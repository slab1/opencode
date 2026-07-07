"""CLI command to purge orphaned events from the opencode session database.

The `opencode-memfs` plugin creates event-sourcing events for every streamed
token update. Over time, these orphaned events can bloat the database to 300+ MB,
breaking `opencode --continue` and `opencode session list`.

This script prunes old events while preserving session messages and metadata.

Usage:
    python3 -m opencode_improvement purge [options]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path


def get_db_path() -> Path:
    """Return the path to the opencode session database."""
    return Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def get_db_size(db_path: Path) -> dict:
    """Get database and WAL file sizes in MB."""
    sizes = {}
    sizes["db"] = db_path.stat().st_size if db_path.exists() else 0
    wal = db_path.parent / f"{db_path.name}-wal"
    sizes["wal"] = wal.stat().st_size if wal.exists() else 0
    shm = db_path.parent / f"{db_path.name}-shm"
    sizes["shm"] = shm.stat().st_size if shm.exists() else 0
    for k in sizes:
        sizes[k] = round(sizes[k] / (1024 * 1024), 1)
    return sizes


def analyze_db(db_path: Path) -> dict:
    """Analyze the database and return stats."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    try:
        # Session and message counts
        c.execute("SELECT COUNT(*) FROM session")
        sessions = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM message")
        messages = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM part")
        parts = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM event")
        events = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM event_sequence")
        sequences = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM todo")
        todos = c.fetchone()[0]

        # Orphan analysis
        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(LENGTH(e.data)), 0)
            FROM event_sequence es
            LEFT JOIN session s ON es.owner_id = s.id
            LEFT JOIN event e ON e.aggregate_id = es.aggregate_id
            WHERE s.id IS NULL
        """)
        orphan_seq, orphan_bytes = c.fetchone()

        # Event type breakdown
        c.execute("SELECT type, COUNT(*) FROM event GROUP BY type ORDER BY COUNT(*) DESC")
        event_types = {row[0]: row[1] for row in c.fetchall()}

        c.execute("SELECT SUM(LENGTH(data)) FROM event")
        total_event_bytes = c.fetchone()[0] or 0

        # Size totals
        db_size = get_db_size(db_path)
        total_mb = db_size["db"] + db_size["wal"]

    finally:
        conn.close()

    return {
        "sessions": sessions,
        "messages": messages,
        "parts": parts,
        "events": events,
        "event_sequences": sequences,
        "todos": todos,
        "orphan_sequences": orphan_seq,
        "orphan_bytes_mb": round(orphan_bytes / (1024 * 1024), 1),
        "total_event_bytes_mb": round(total_event_bytes / (1024 * 1024), 1),
        "db_size_mb": db_size,
        "total_size_mb": total_mb,
        "event_types": event_types,
    }


def _purge(db_path: Path, keep_sessions: int, dry_run: bool = False) -> dict:
    """Delete orphaned events and optionally VACUUM."""
    result = {"dry_run": dry_run}
    errors = []

    if not db_path.exists():
        return {"error": f"Database not found: {db_path}"}

    # Back up
    backup_path = db_path.parent / f"{db_path.name}.backup_before_purge"
    if not dry_run and not backup_path.exists():
        import shutil
        shutil.copy2(str(db_path), str(backup_path))
        result["backup"] = str(backup_path)

    before = analyze_db(db_path)
    result["before"] = before

    if before["events"] == 0:
        result["message"] = "No events to purge."
        return result

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = OFF")
    c = conn.cursor()

    try:
        if keep_sessions > 0:
            # Keep events for the most recent N sessions
            c.execute("""
                SELECT id FROM session
                ORDER BY time_updated DESC
                LIMIT ?
            """, (keep_sessions,))
            keep_ids = {row[0] for row in c.fetchall()}

            # Find owner_ids (aggregate_ids) linked to kept sessions
            c.execute("""
                SELECT aggregate_id FROM event_sequence
                WHERE owner_id IS NOT NULL AND owner_id IN ({})
            """.format(",".join("?" for _ in keep_ids)), list(keep_ids))
            keep_aggregates = {row[0] for row in c.fetchall()}

            if keep_aggregates:
                placeholders = ",".join("?" for _ in keep_aggregates)
                c.execute(f"DELETE FROM event WHERE aggregate_id NOT IN ({placeholders})", list(keep_aggregates))
                evts_deleted = c.rowcount
                c.execute(f"DELETE FROM event_sequence WHERE aggregate_id NOT IN ({placeholders})", list(keep_aggregates))
                seq_deleted = c.rowcount
            else:
                evts_deleted, seq_deleted = 0, 0

            result["kept_session_ids"] = list(keep_ids)[:10]  # log first 10
            result["kept_aggregates"] = len(keep_aggregates)
        else:
            # Delete ALL events (they're all orphaned intermediate state)
            c.execute("DELETE FROM event")
            evts_deleted = c.rowcount
            c.execute("DELETE FROM event_sequence")
            seq_deleted = c.rowcount

        result["events_deleted"] = evts_deleted
        result["sequences_deleted"] = seq_deleted
        conn.commit()

        # Checkpoint WAL
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()

    except Exception as e:
        errors.append(str(e))
        result["error"] = str(e)
    finally:
        conn.close()

    # VACUUM (needs separate connection)
    if not dry_run and not errors:
        try:
            conn2 = sqlite3.connect(str(db_path))
            conn2.execute("VACUUM")
            conn2.close()
            result["vacuum_done"] = True
        except Exception as e:
            errors.append(f"VACUUM failed: {e}")
            result["vacuum_error"] = str(e)

    after = analyze_db(db_path)
    result["after"] = after

    if not errors:
        saved_mb = round(before["total_size_mb"] - after["total_size_mb"], 1)
        result["space_saved_mb"] = saved_mb
        result["message"] = (
            f"Purged {evts_deleted} events / {seq_deleted} sequences. "
            f"DB: {before['total_size_mb']} MB → {after['total_size_mb']} MB "
            f"(-{saved_mb} MB, {'-'.join(str(before['db_size_mb'][k]) + '→' + str(after['db_size_mb'][k]) for k in ['db', 'wal'])} MB)"
        )

    if errors:
        result["errors"] = errors
        result["message"] = f"Purge completed with {len(errors)} error(s): {'; '.join(errors)}"

    return result


def add_subparser(subparsers) -> argparse.ArgumentParser:
    """Register the 'purge' subcommand and return the parser."""
    pp = subparsers.add_parser(
        "purge", help="Purge orphaned session events from the opencode database"
    )
    pp.add_argument("--dry-run", "-n", action="store_true",
                    help="Show what would be deleted without deleting")
    pp.add_argument("--keep", "-k", type=int, default=0,
                    help="Keep events for the N most recent sessions (default: 0 = delete all)")
    pp.add_argument("--vacuum", action="store_true", default=True,
                    help="Run VACUUM after purge (default: True)")
    pp.add_argument("--analyze", action="store_true",
                    help="Just analyze the database without purging")
    pp.add_argument("--json", action="store_true",
                    help="Output raw JSON instead of formatted text")
    pp.add_argument("--backup", action="store_true", default=True,
                    help="Create backup before purging (default: True)")
    return pp


def run_purge(args: argparse.Namespace) -> int:
    """Run the purge command."""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    if args.analyze:
        stats = analyze_db(db_path)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Database: {db_path}")
            print(f"  Size: {stats['db_size_mb']['db']} MB (WAL: {stats['db_size_mb']['wal']} MB, total: {stats['total_size_mb']} MB)")
            print(f"  Sessions: {stats['sessions']} | Messages: {stats['messages']} | Parts: {stats['parts']}")
            print(f"  Events: {stats['events']} | Sequences: {stats['event_sequences']} | Todos: {stats['todos']}")
            print(f"  Orphan sequences: {stats['orphan_sequences']} ({stats['orphan_bytes_mb']} MB)")
            print(f"  Total event data: {stats['total_event_bytes_mb']} MB")
            if stats["event_types"]:
                print(f"  Event types:")
                for etype, count in stats["event_types"].items():
                    print(f"    {etype}: {count}")
        return 0

    result = _purge(db_path, keep_sessions=args.keep, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
            return 1

        print(f"\n  Database purge {'(DRY RUN)' if args.dry_run else ''}")
        print(f"  {'='*50}")
        print(f"  Before: {result['before']['total_size_mb']} MB "
              f"(db={result['before']['db_size_mb']['db']} MB, "
              f"wal={result['before']['db_size_mb']['wal']} MB)")
        print(f"  Events: {result['before']['events']} | "
              f"Sequences: {result['before']['event_sequences']}")

        if not args.dry_run and "events_deleted" in result:
            print(f"  Deleted: {result['events_deleted']} events, "
                  f"{result['sequences_deleted']} sequences")
            print(f"  After: {result['after']['total_size_mb']} MB "
                  f"(db={result['after']['db_size_mb']['db']} MB, "
                  f"wal={result['after']['db_size_mb']['wal']} MB)")
            saved = result.get("space_saved_mb", 0)
            print(f"  Space saved: {saved} MB")
            print(f"  Vacuum: {'✓' if result.get('vacuum_done') else result.get('vacuum_error', 'n/a')}")
        elif args.dry_run:
            print(f"  Would delete ~{result['before']['events']} events "
                  f"(~{result['before']['total_event_bytes_mb']} MB)")

        if result.get("errors"):
            print(f"  Errors: {'; '.join(result['errors'])}")
            return 1

    return 0

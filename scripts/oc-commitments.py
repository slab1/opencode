#!/usr/bin/env python3
"""
OpenCode Commitments — track inferred follow-up tasks.

Commitments are lightweight, short-lived follow-up memories that
the agent creates to remember to check back on something.

Usage:
    oc-commitments add --desc "Check CI status" --due "4h"
    oc-commitments list [--status open|done|all]
    oc-commitments done <id>
    oc-commitments drop <id>
    oc-commitments overdue
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

COMMITMENTS_FILE = Path.home() / ".config" / "opencode" / "shared" / "commitments.json"
MAX_ACTIVE = 10  # Don't accumulate too many open commitments


def load():
    if not COMMITMENTS_FILE.exists():
        return []
    try:
        with open(COMMITMENTS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save(commitments):
    COMMITMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Keep only MAX_ACTIVE most recent of each status
    open_items = [c for c in commitments if c.get("status") == "open"]
    done_items = [c for c in commitments if c.get("status") == "done"]
    # Sort by created_at descending
    open_items.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    done_items.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    # Trim
    commitments = open_items[:MAX_ACTIVE] + done_items[:MAX_ACTIVE]
    with open(COMMITMENTS_FILE, "w") as f:
        json.dump(commitments, f, indent=2)


def parse_due(due_str):
    """Parse a due string like '4h', '2d', '30m' into a timestamp."""
    now = datetime.now(timezone.utc)
    if due_str.lower() == "now":
        return now.isoformat()
    if due_str.lower() == "eod":
        # End of day (today 23:59 UTC)
        return now.replace(hour=23, minute=59, second=0).isoformat()

    import re
    match = re.match(r"(\d+)\s*(m|min|h|hr|d|day|w|week)s?", due_str)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    delta = None

    if unit in ("m", "min"):
        delta = timedelta(minutes=amount)
    elif unit in ("h", "hr"):
        delta = timedelta(hours=amount)
    elif unit in ("d", "day"):
        delta = timedelta(days=amount)
    elif unit in ("w", "week"):
        delta = timedelta(weeks=amount)

    return (now + delta).isoformat() if delta else None


def pretty_time(iso_str):
    """Format ISO timestamp as relative time."""
    if not iso_str:
        return "never"
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    now = datetime.now(timezone.utc)
    diff = dt - now
    total_secs = diff.total_seconds()

    if total_secs < 0:
        return f"{int(-total_secs // 60)}m overdue"
    if total_secs < 3600:
        return f"in {int(total_secs // 60)}m"
    if total_secs < 86400:
        return f"in {int(total_secs // 3600)}h"
    return f"in {int(total_secs // 86400)}d"


def cmd_add(description, due_str=None, scope=None):
    """Add a new commitment."""
    commitments = load()

    commitment = {
        "id": str(uuid4())[:8],
        "description": description,
        "status": "open",
        "scope": scope or "general",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "due_at": parse_due(due_str) if due_str else None,
        "from_session": None,  # Could be populated by agent
    }

    commitments.append(commitment)
    save(commitments)
    print(f"Added commitment [{commitment['id']}]: {description}")
    if commitment["due_at"]:
        print(f"  Due: {pretty_time(commitment['due_at'])}")
    return 0


def cmd_list(status_filter="open"):
    """List commitments, optionally filtered by status."""
    commitments = load()
    if status_filter == "all":
        filtered = commitments
    elif status_filter:
        filtered = [c for c in commitments if c.get("status") == status_filter]
    else:
        filtered = [c for c in commitments if c.get("status") == "open"]

    if not filtered:
        print(f"No {'open' if status_filter == 'open' else status_filter} commitments.")
        return

    # Sort: overdue first, then by due date
    def sort_key(c):
        due = c.get("due_at", "")
        status_order = 0 if c.get("status") == "open" else 1
        return (status_order, due or "")

    filtered.sort(key=sort_key)

    print(f"{'ID':<10} {'Status':<8} {'Due':<18} {'Description'}")
    print("-" * 70)
    for c in filtered:
        due_str = pretty_time(c.get("due_at")) if c.get("due_at") else "—"
        status = c.get("status", "?")
        desc = c.get("description", "")[:50]
        print(f"{c.get('id', '?'):<10} {status:<8} {due_str:<18} {desc}")
    print(f"\n{len(filtered)} commitment(s)")


def cmd_done(commitment_id):
    """Mark a commitment as done."""
    commitments = load()
    found = False
    for c in commitments:
        if c.get("id") == commitment_id or c.get("id", "").startswith(commitment_id):
            c["status"] = "done"
            c["updated_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            print(f"Completed: {c.get('description', '')}")
            break
    if not found:
        print(f"No commitment with id starting with '{commitment_id}'", file=sys.stderr)
        return 1
    save(commitments)
    return 0


def cmd_drop(commitment_id):
    """Remove a commitment entirely."""
    commitments = load()
    new_commitments = [c for c in commitments
                       if c.get("id") != commitment_id
                       and not c.get("id", "").startswith(commitment_id)]
    if len(new_commitments) == len(commitments):
        print(f"No commitment with id '{commitment_id}'", file=sys.stderr)
        return 1
    save(new_commitments)
    print(f"Removed commitment {commitment_id}")
    return 0


def cmd_overdue():
    """List overdue commitments."""
    commitments = load()
    now = datetime.now(timezone.utc)
    overdue = []
    for c in commitments:
        due = c.get("due_at")
        if due and c.get("status") == "open":
            try:
                due_dt = datetime.fromisoformat(due)
                if due_dt < now:
                    overdue.append(c)
            except ValueError:
                pass

    if not overdue:
        print("No overdue commitments. 🎉")
        return

    print(f"{'ID':<10} {'Overdue':<14} {'Description'}")
    print("-" * 60)
    for c in overdue:
        due_str = pretty_time(c.get("due_at", ""))
        print(f"{c.get('id', '?'):<10} {due_str:<14} {c.get('description', '')[:40]}")
    print(f"\n{len(overdue)} overdue commitment(s)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenCode Commitments Manager")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a commitment")
    add_p.add_argument("--desc", "-d", required=True, help="Description")
    add_p.add_argument("--due", help="Due in: 4h, 2d, 30m, eod, now")
    add_p.add_argument("--scope", "-s", help="Scope (e.g. build, review)")

    list_p = sub.add_parser("list", help="List commitments")
    list_p.add_argument("--status", choices=["open", "done", "all"], default="open")

    done_p = sub.add_parser("done", help="Mark commitment as done")
    done_p.add_argument("id", help="Commitment ID")

    drop_p = sub.add_parser("drop", help="Remove a commitment")
    drop_p.add_argument("id", help="Commitment ID")

    sub.add_parser("overdue", help="List overdue commitments")

    args = parser.parse_args()

    commands = {
        "add": lambda: cmd_add(args.desc, args.due, args.scope),
        "list": lambda: cmd_list(args.status),
        "done": lambda: cmd_done(args.id),
        "drop": lambda: cmd_drop(args.id),
        "overdue": cmd_overdue,
    }

    fn = commands.get(args.command)
    if fn:
        return fn()
    return 1


if __name__ == "__main__":
    sys.exit(main())

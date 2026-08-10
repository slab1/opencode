#!/usr/bin/env python3
"""One-time backfill: seed episodic memory (L2) from shared/performance.json.

Reads existing task history and appends deduped entries to
memory/aether/episodic_memory.jsonl. Entries already present (same task +
timestamp) are skipped. Existing entries are never deleted. Idempotent —
re-running adds nothing.
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path.home() / ".config" / "opencode"
PERFORMANCE_FILE = BASE_DIR / "shared" / "performance.json"
EPISODIC_DB = BASE_DIR / "memory" / "aether" / "episodic_memory.jsonl"


def load_existing() -> list:
    entries = []
    if EPISODIC_DB.exists():
        for line in EPISODIC_DB.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def dedup_key(entry: dict) -> tuple:
    task = str(entry.get("task", "")).strip().lower()
    ts = entry.get("timestamp", 0)
    try:
        ts = round(float(ts), 3)
    except (TypeError, ValueError):
        ts = 0.0
    return (task, ts)


def main() -> int:
    if not PERFORMANCE_FILE.exists():
        print(f"performance.json not found at {PERFORMANCE_FILE}")
        return 1

    try:
        perf = json.loads(PERFORMANCE_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to read performance.json: {e}")
        return 1

    if not isinstance(perf, list):
        print("performance.json is not a list; nothing to seed")
        return 1

    existing = load_existing()
    seen = {dedup_key(e) for e in existing}

    added = 0
    skipped = 0
    with open(EPISODIC_DB, "a") as f:
        for entry in perf:
            task = entry.get("task")
            ts = entry.get("timestamp")
            if not task or ts is None:
                skipped += 1
                continue
            key = dedup_key(entry)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            episodic = {
                "timestamp": float(ts),
                "task": str(task),
                "action": f"tracked by agent '{entry.get('agent', 'unknown')}'",
                "outcome": str(entry.get("outcome", "unknown")),
                "metadata": {
                    "agent": entry.get("agent"),
                    "duration_s": entry.get("duration_s", 0),
                    "error": entry.get("error"),
                    "source": "seed_backfill",
                },
            }
            f.write(json.dumps(episodic) + "\n")
            added += 1

    total = len(existing) + added
    print(f"Seeded {added} new episodic entries ({skipped} skipped as duplicates/invalid).")
    print(f"Episodic store now has {total} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""Control-plane audit trail (Bet 7).

Append-only, fsync'd record of agent actions — the "control plane lite"
governance surface: anyone can run `audit-log --tail` to see exactly what
agents did, when, and with what outcome. Records are never rewritten or
deleted in place; the file only ever grows. Replaces the vaporware promise
of the deprecated cost_tracker with something real and file-verifiable.

Storage: memory/aether/audit_log.jsonl (one JSON object per line).
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path.home() / ".config" / "opencode"
MEMORY_DIR = BASE_DIR / "memory" / "aether"
AUDIT_LOG = MEMORY_DIR / "audit_log.jsonl"


class AuditLog:
    """Append-only action log for the control-plane surface."""

    def log(
        self,
        agent: str,
        action: str,
        outcome: str,
        detail: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append one audited action. Never fails tracking callers (raise=False
        semantics are left to the caller's try/except)."""
        entry = {
            "timestamp": time.time(),
            "agent": agent,
            "action": action,
            "outcome": outcome,
            "detail": detail,
            "metadata": metadata or {},
        }
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry

    def _load(self) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(AUDIT_LOG, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        return records

    def tail(
        self,
        limit: int = 20,
        agent: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Most recent records first. Optional agent-name and since-epoch filters."""
        records = self._load()
        if agent:
            records = [r for r in records if r.get("agent") == agent]
        if since is not None:
            records = [r for r in records if (r.get("timestamp") or 0) >= since]
        records.sort(key=lambda r: r.get("timestamp", 0.0), reverse=True)
        return records[:limit]

    def stats(self) -> Dict[str, Any]:
        records = self._load()
        by_agent: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        by_action: Dict[str, int] = {}
        for r in records:
            by_agent[r.get("agent", "?")] = by_agent.get(r.get("agent", "?"), 0) + 1
            by_outcome[r.get("outcome", "?")] = by_outcome.get(r.get("outcome", "?"), 0) + 1
            by_action[r.get("action", "?")] = by_action.get(r.get("action", "?"), 0) + 1
        return {
            "total": len(records),
            "by_agent": by_agent,
            "by_outcome": by_outcome,
            "by_action": by_action,
            "first_logged_at": records[0]["timestamp"] if records else None,
            "last_logged_at": records[-1]["timestamp"] if records else None,
        }

    def export(self, path: Path) -> Dict[str, Any]:
        """Export the full audit log as a portable JSON array (records as-is)."""
        records = self._load()
        bundle = {
            "format": "aether-audit",
            "version": 1,
            "exported_at": time.time(),
            "total": len(records),
            "records": records,
        }
        out = Path(path)
        out.write_text(json.dumps(bundle, indent=2))
        return bundle


if __name__ == "__main__":
    import sys

    a = AuditLog()
    print(json.dumps(a.tail(int(sys.argv[1]) if len(sys.argv) > 1 else 20), indent=2))
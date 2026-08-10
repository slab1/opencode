#!/usr/bin/env python3
"""Bet 7 verification — control-plane audit trail.

Tests (isolated temp store; live log touched only by the CLI smoke check):
  1. log() appends one fsync'd record per call
  2. tail() returns newest-first with correct count
  3. agent filter and since-epoch filter work
  4. stats() counts are correct (by agent / outcome / action)
  5. reads never write: queries leave the file byte-identical
  6. export() produces a parseable portable bundle with all records
  7. CLI smoke: `audit-log --tail` runs against the live log

Run: python3 scripts/test-audit-log.py   (exit 0 = pass)
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import shared.audit_log as al_mod
from shared.audit_log import AuditLog


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    orig = al_mod.AUDIT_LOG
    tmp = Path(tempfile.mkdtemp(prefix="aether-audit-test-"))
    try:
        al_mod.AUDIT_LOG = tmp / "audit_log.jsonl"
        al = AuditLog()

        # Test 1: append semantics
        e1 = al.log("human", "track", "success", "round-trip marker", {"k": "v"})
        e2 = al.log("fixer", "track", "success", "audit smoke")
        e3 = al.log("fixer", "track", "failure", "bad build")
        assert e1["agent"] == "human" and e1["outcome"] == "success"
        lines = [l for l in al_mod.AUDIT_LOG.read_text().splitlines() if l.strip()]
        assert len(lines) == 3, f"expected 3 lines, got {len(lines)}"

        # Test 2: tail newest-first
        t = al.tail(limit=10)
        assert len(t) == 3 and t[0]["detail"] == "bad build", t[0]
        t2 = al.tail(limit=1)
        assert len(t2) == 1 and t2[0]["detail"] == "bad build"

        # Test 3: filters
        f = al.tail(limit=10, agent="fixer")
        assert len(f) == 2 and all(r["agent"] == "fixer" for r in f)
        s = al.tail(limit=10, since=e2["timestamp"])
        assert len(s) == 2 and s[0]["detail"] == "bad build"

        # Test 4: stats
        st = al.stats()
        assert st["total"] == 3, st
        assert st["by_agent"] == {"human": 1, "fixer": 2}, st["by_agent"]
        assert st["by_outcome"] == {"success": 2, "failure": 1}, st["by_outcome"]
        assert st["by_action"] == {"track": 3}, st["by_action"]

        # Test 5: reads never write (append-only invariant)
        before = al_mod.AUDIT_LOG.read_bytes()
        al.tail(10)
        al.stats()
        assert al_mod.AUDIT_LOG.read_bytes() == before, "query mutated the log!"

        # Test 6: export bundle
        bundle = al.export(tmp / "audit_export.json")
        assert bundle["format"] == "aether-audit" and bundle["total"] == 3
        reloaded = json.loads((tmp / "audit_export.json").read_text())
        assert len(reloaded["records"]) == 3

        # Test 7: CLI smoke against the live log (restore real path first)
        al_mod.AUDIT_LOG = orig
        r = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "audit-log", "--tail", "5"],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, r.stderr
        live = json.loads(r.stdout)
        print(f"PASS: audit trail tests green "
              f"(live log has {len(live)} visible records, stats says "
              f"{AuditLog().stats()['total']} total)")
        return 0
    finally:
        al_mod.AUDIT_LOG = orig
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
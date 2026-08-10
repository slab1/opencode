#!/usr/bin/env python3
"""Bet 10 verification — self-improvement paper trail (trends CLI).

Tests (isolated temp trends dir; real reports/trends/ untouched):
  1. two pass receipts + one FAIL-gate receipt -> table shows gates
  2. gate classification: rate >= 0.8 PASS else FAIL
  3. --json output parseable, matches table rows
  4. empty dir -> rc=1 (no receipts = broken paper trail)
  5. empty dir + --no-fail -> rc=0
  6. --limit trims to N most recent
  7. live sanity: trends CLI on real reports/trends/ returns rc 0 (>=1 receipt)

Run: python3 scripts/test-trends-cli.py   (exit 0 = pass)
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.trends import load_trends, render_table, MIN_PASS_RATE

RECEIPT = (
    '{"timestamp": "%s", "provider": "mock", '
    '"summary": {"passed": %d, "total_tests": 63, "pass_rate": %.3f}, '
    '"regression": {"delta": %s}}'
)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="aether-trends-test-"))
    try:
        (tmp / "trend_2026-08-10_00-00-01.json").write_text(
            RECEIPT % ("2026-08-10T00:00:01Z", 63, 1.0, 0.0))
        (tmp / "trend_2026-08-10_00-00-02.json").write_text(
            RECEIPT % ("2026-08-10T00:00:02Z", 55, 0.873, -0.127))
        (tmp / "trend_2026-08-10_00-00-03.json").write_text(
            RECEIPT % ("2026-08-10T00:00:03Z", 44, 0.698, -0.302))

        rows = load_trends(tmp)
        assert len(rows) == 3, len(rows)
        gates = [r["gate"] for r in rows]
        assert gates == ["PASS", "PASS", "FAIL"], gates
        assert (rows[0]["pass_rate"] or 0) >= MIN_PASS_RATE
        assert (rows[2]["pass_rate"] or 0) < MIN_PASS_RATE

        table = render_table(rows)
        assert "| FAIL |" in table and table.count("| PASS |") == 2
        assert "44/63" in table and "70%" in table

        # --json output matches table rows
        r1 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "trends",
             "--path", str(tmp), "--json"],
            capture_output=True, text=True, timeout=60)
        assert r1.returncode == 0, r1.stderr
        parsed = json.loads(r1.stdout)
        assert len(parsed) == 3 and parsed[-1]["gate"] == "FAIL"

        # --limit trims to the most recent
        r2 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "trends",
             "--path", str(tmp), "--limit", "2"],
            capture_output=True, text=True, timeout=60)
        assert r2.returncode == 0
        assert "00:00:01" not in r2.stdout and "00:00:03" in r2.stdout

        # empty dir: rc=1 (vacuous-pass guard), --no-fail rc=0
        empty = tmp / "empty"
        empty.mkdir()
        r3 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "trends",
             "--path", str(empty)],
            capture_output=True, text=True, timeout=60)
        assert r3.returncode == 1, "expected rc=1 on empty paper trail"
        assert "paper trail is empty" in r3.stderr
        r4 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "trends",
             "--path", str(empty), "--no-fail"],
            capture_output=True, text=True, timeout=60)
        assert r4.returncode == 0, "expected rc=0 with --no-fail"

        # live sanity: real repo reports/trends has >= 1 receipt
        real = load_trends(Path.home() / ".config" / "opencode" / "reports" / "trends")
        assert len(real) >= 1, "expected >= 1 committed CI receipt"
        print(f"PASS: trends CLI green (live receipts: {len(real)} from "
              f"{real[0]['timestamp']} gate={real[0]['gate']} rate={real[0]['pass_rate']})")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
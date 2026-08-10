"""CI eval trend ledger (Bet 10 — self-improvement paper trail).

Reads the reports/trends/trend_*.json receipts produced by Agent Eval CI
runs and renders a human-readable pass-rate history. "The agent audits
its own prompts, with receipts": every CI run writes a receipt file; this
command shows them.

Usage (CLI): python3 -m opencode_improvement trends ...
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

MIN_PASS_RATE = 0.8  # must match the agent-eval.yml gate


def load_trends(trends_dir: Path) -> List[Dict[str, Any]]:
    """Parse every trend_*.json in the dir into a receipt row (newest last)."""
    rows: List[Dict[str, Any]] = []
    for f in sorted(trends_dir.glob("trend_*.json")):
        try:
            j = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        s = j.get("summary") or {}
        rate = s.get("pass_rate")
        rows.append(
            {
                "file": f.name,
                "timestamp": j.get("timestamp")
                or f.stem.removeprefix("trend_").replace("_", " "),
                "provider": j.get("provider", "?"),
                "passed": s.get("passed"),
                "total": s.get("total_tests"),
                "pass_rate": rate,
                "gate": "PASS" if (rate or 0) >= MIN_PASS_RATE else "FAIL",
                "regression_delta": (j.get("regression") or {}).get("delta"),
            }
        )
    return rows


def render_table(rows: List[Dict[str, Any]]) -> str:
    lines = [
        "| run (UTC) | provider | passed/total | pass rate | gate | vs baseline |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        pct = f"{r['pass_rate'] * 100:.0f}%" if r["pass_rate"] is not None else "?"
        delta = (
            f"{r['regression_delta'] * 100:+.1f}%"
            if r["regression_delta"] is not None
            else "—"
        )
        passed = f"{r['passed']}/{r['total']}" if r["passed"] is not None else "?"
        lines.append(
            f"| {r['timestamp']} | {r['provider']} | {passed} | {pct} | "
            f"{r['gate']} | {delta} |"
        )
    return "\n".join(lines)


def main(argv: List[str] = None) -> int:
    p = argparse.ArgumentParser(
        prog="trends", description="Show the CI eval paper trail (receipts)."
    )
    p.add_argument("--path", default=None, help="Trends dir (default: repo 'reports/trends/')")
    p.add_argument("--limit", type=int, default=20, help="Show only the N most recent receipts")
    p.add_argument("--json", action="store_true", help="Print parsed receipts as JSON")
    p.add_argument("--no-fail", action="store_true", help="Exit 0 even with no receipts")
    args = p.parse_args(argv)

    if args.path:
        trends_dir = Path(args.path)
    else:
        cwd_trends = Path.cwd() / "reports" / "trends"
        trends_dir = cwd_trends if cwd_trends.exists() else Path.home() / ".config" / "opencode" / "reports" / "trends"

    rows = load_trends(trends_dir)
    rows = rows[-args.limit:] if args.limit else rows

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        if rows:
            print(render_table(rows))
        else:
            print(f"no receipts found in {trends_dir}")

    if not rows:
        print(f"ERROR: no trend receipts found at {trends_dir} — paper trail is empty", file=sys.stderr)
        return 1 if not args.no_fail else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
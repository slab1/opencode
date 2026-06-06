"""CLI entry point for python3 -m opencode_improvement."""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="OpenCode Self-Improvement Engine")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- audit ---
    ap = subparsers.add_parser("audit", help="Audit all agent configs for structural completeness")
    ap.add_argument("--agent", "-a", help="Audit a specific agent only")

    # --- report ---
    rp = subparsers.add_parser("report", help="Generate performance report")
    rp.add_argument("--agent", help="Filter report to one agent")

    # --- suggest ---
    sp = subparsers.add_parser("suggest", help="Suggest improvements for an agent")
    sp.add_argument("--agent", "-a", required=True, help="Agent to analyze")

    # --- track ---
    tp = subparsers.add_parser("track", help="Log a task outcome")
    tp.add_argument("agent", help="Agent name")
    tp.add_argument("outcome", choices=["success", "failure", "partial"], help="Task outcome")
    tp.add_argument("task", help="Task description")
    tp.add_argument("--duration", type=int, default=0, help="Duration in seconds")
    tp.add_argument("--error", help="Error message if the task failed")

    args = parser.parse_args()

    if args.command == "audit":
        from opencode_improvement import audit_agents
        result = audit_agents(args.agent)
        print(json.dumps(result, indent=2))

    elif args.command == "report":
        from opencode_improvement import generate_report
        result = generate_report(args.agent)
        print(json.dumps(result, indent=2))

    elif args.command == "suggest":
        from opencode_improvement import suggest_improvements
        result = suggest_improvements(args.agent)
        print(json.dumps(result, indent=2))

    elif args.command == "track":
        from opencode_improvement.track import PerformanceTracker
        tracker = PerformanceTracker()
        entry = tracker.log(
            agent=args.agent,
            task=args.task,
            outcome=args.outcome,
            duration_s=args.duration,
            error=args.error,
        )
        print(json.dumps(entry, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

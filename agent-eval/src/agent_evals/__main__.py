"""CLI entry point for python3 -m agent_evals.

Supports: audit, eval, inspect, kappa, list-strategies, strategies, ab, version, suggest, report, track
"""

import argparse
import json
import sys
import os
from pathlib import Path


def _resolve_paths(args):
    """Resolve overridable paths from CLI args and env vars."""
    base = Path(os.environ.get("AGENT_EVAL_HOME", Path.home() / ".config" / "opencode"))
    agents_dir = Path(getattr(args, "agents_dir", None)) if hasattr(args, "agents_dir") and getattr(args, "agents_dir") else base / "agents"
    golden_file = Path(getattr(args, "golden_file", None)) if hasattr(args, "golden_file") and getattr(args, "golden_file") else base / "shared" / "golden" / "agent_tasks.json"
    eval_dir = Path(getattr(args, "eval_dir", None)) if hasattr(args, "eval_dir") and getattr(args, "eval_dir") else base / "shared" / "eval"
    return agents_dir, golden_file, eval_dir


def main():
    parser = argparse.ArgumentParser(description="Agent Evaluation Toolkit")
    parser.add_argument("--agents-dir", default=None, help="Override agents directory")
    parser.add_argument("--golden-file", default=None, help="Override golden dataset path")
    parser.add_argument("--eval-dir", default=None, help="Override eval directory")

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

    # --- strategy (log) ---
    sp_strat = subparsers.add_parser("strategy", help="Log an improvement strategy decision")
    sp_strat.add_argument("--target", required=True, help="Target agent")
    sp_strat.add_argument("--diagnosis", required=True, help="What's wrong")
    sp_strat.add_argument("--strategy", required=True, help="Strategy chosen")
    sp_strat.add_argument("--alternatives", nargs="*", default=[], help="Other strategies considered")
    sp_strat.add_argument("--why", default="", help="Why this strategy was chosen")
    sp_strat.add_argument("--confidence-before", type=float, default=0.5, help="Confidence before (0-1)")
    sp_strat.add_argument("--outcome", choices=["success", "failure", "partial"], help="Outcome")
    sp_strat.add_argument("--evidence", help="Evidence of outcome")
    sp_strat.add_argument("--confidence-after", type=float, help="Confidence after (0-1)")

    # --- strategies (effectiveness report) ---
    subparsers.add_parser("strategies", help="Show strategy effectiveness scores")

    # --- eval ---
    ep = subparsers.add_parser("eval", help="Evaluate agent(s) against golden test cases")
    ep.add_argument("--agent", "-a", help="Evaluate a specific agent only")
    ep.add_argument("--config", "-c", default=None, help="Path to YAML eval config")
    ep.add_argument("--golden", action="store_true", default=True, help="Run golden test cases (default: True)")
    ep.add_argument("--fail-under", type=float, default=None,
                    help="Minimum pass rate (0.0-1.0). Exit non-zero if below threshold.")
    ep.add_argument("--severity", choices=["info", "warn", "critical"], default="warn",
                    help="Minimum severity to fail on (default: warn)")
    ep.add_argument("--compare", action="store_true", default=False,
                    help="Compare results against baseline and generate markdown report")
    ep.add_argument("--baseline", default=None, help="Path to baseline JSON file")
    ep.add_argument("--output", "-o", default=None, help="Save results to file")
    ep.add_argument("--provider", choices=["real", "mock"], default="real",
                    help="Evaluation provider: real (default) or mock (offline deterministic)")
    ep.add_argument("--judge-model", default=None,
                    help="LLM model name for LLM-as-judge scoring (e.g., 'gpt-4')")
    ep.add_argument("--executor", choices=["sync", "async"], default="sync",
                    help="Execution strategy: sync (sequential, default) or async (concurrent)")
    ep.add_argument("--scorecard", action="store_true", default=False,
                    help="Render ASCII bar chart scorecard in output")
    ep.add_argument("--ab", nargs=2, metavar=("CONFIG_A", "CONFIG_B"), default=None,
                    help="A/B compare two agent configs (requires --agent)")
    ep.add_argument("--version", action="store_true", default=False,
                    help="Show golden test case versions")

    # --- list-strategies ---
    subparsers.add_parser("list-strategies", help="List all available improvement strategies")

    # --- inspect ---
    ip = subparsers.add_parser("inspect", help="Inspect golden test case details")
    ip.add_argument("--agent", "-a", required=True, help="Agent to inspect")
    ip.add_argument("--case", "-c", default=None, help="Specific test case ID")
    ip.add_argument("--failed", action="store_true", default=False,
                    help="List all failing test cases for this agent")

    # --- kappa ---
    kp = subparsers.add_parser("kappa", help="Compute Cohen's Kappa inter-rater agreement")
    kp.add_argument("--dataset", default=None, help="Path to golden dataset JSON")

    # --- version (standalone) ---
    subparsers.add_parser("version", help="Show package version and task version info")

    args = parser.parse_args()
    agents_dir, golden_file, eval_dir = _resolve_paths(args)

    from agent_evals import (
        audit_agents, generate_report, suggest_improvements,
        eval_agents, list_task_versions, inspect_case,
        compute_cohens_kappa, STRATEGY_LIBRARY,
        log_strategy, strategy_effectiveness, ab_compare_agents,
    )
    from agent_evals.track import PerformanceTracker

    if args.command == "audit":
        result = audit_agents(args.agent, agents_dir=agents_dir)
        print(json.dumps(result, indent=2))

    elif args.command == "report":
        result = generate_report(args.agent, agents_dir=agents_dir)
        print(json.dumps(result, indent=2))

    elif args.command == "suggest":
        result = suggest_improvements(args.agent, agents_dir=agents_dir)
        print(json.dumps(result, indent=2))

    elif args.command == "track":
        tracker = PerformanceTracker()
        entry = tracker.log(
            agent=args.agent,
            task=args.task,
            outcome=args.outcome,
            duration_s=args.duration,
            error=args.error,
        )
        print(json.dumps(entry, indent=2))

    elif args.command == "strategy":
        result = log_strategy(
            agent_target=args.target,
            diagnosis=args.diagnosis,
            strategy_chosen=args.strategy,
            strategy_alternatives=args.alternatives,
            why_this_strategy=args.why,
            confidence_before=args.confidence_before,
            outcome=args.outcome,
            outcome_evidence=args.evidence,
            confidence_after=args.confidence_after,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "strategies":
        result = strategy_effectiveness()
        print(json.dumps(result, indent=2))

    elif args.command == "eval":
        if args.version:
            result = list_task_versions(golden_file=golden_file)
            print(json.dumps(result, indent=2))
            sys.exit(0)

        if args.ab:
            if not args.agent:
                print("Error: --ab requires --agent to specify the agent being compared")
                sys.exit(1)
            result = ab_compare_agents(
                agent_name=args.agent,
                config_a=args.ab[0],
                config_b=args.ab[1],
                golden_file=golden_file,
            )
            print(json.dumps(result, indent=2))
            sys.exit(0)

        result = eval_agents(
            agent_name=args.agent,
            config_path=args.config,
            use_golden=args.golden,
            fail_under=args.fail_under,
            severity=args.severity,
            compare=args.compare,
            baseline_path=args.baseline,
            provider=args.provider,
            judge_model=args.judge_model,
            executor_type=args.executor,
            scorecard=args.scorecard,
            agents_dir=agents_dir,
            golden_file=golden_file,
            eval_dir=eval_dir,
        )

        output = result
        if args.scorecard:
            print(result.get("scorecard", ""))
            print("")
            print("--- Full JSON output below ---")
            print("")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {args.output}")

        print(json.dumps(output, indent=2))

        if args.fail_under is not None and result.get("pass_rate", 1.0) < args.fail_under:
            sys.exit(1)

    elif args.command == "inspect":
        result = inspect_case(
            agent_name=args.agent,
            case_id=args.case,
            failed_only=args.failed,
            agents_dir=agents_dir,
            golden_file=golden_file,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "kappa":
        result = compute_cohens_kappa(
            dataset_path=args.dataset,
            golden_file=golden_file,
        )
        print(json.dumps(result, indent=2))

        if result.get("kappa_acceptable") is False:
            print(f"\n⚠️  Kappa {result.get('overall_kappa')} < 0.7 — flagged categories:")
            for cat in result.get("flagged_categories", []):
                print(f"   - {cat['category']}: {cat['kappa']}")
            sys.exit(1)

    elif args.command == "list-strategies":
        print(json.dumps(STRATEGY_LIBRARY, indent=2))

    elif args.command == "version":
        from agent_evals import __version__
        vinfo = list_task_versions(golden_file=golden_file)
        print(f"agent-eval version: {__version__}")
        print(json.dumps(vinfo, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

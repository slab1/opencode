"""CLI entry point for python3 -m opencode_improvement.

Extended with 10 improvements:
1. LLM-as-Judge evaluator (--judge-model)
2. Mock provider (--provider mock)
3. Comparison report (--compare generates markdown)
4. Auto-commit trends (CI integration)
5. A/B config comparison (--ab)
6. Cohen's Kappa (kappa subcommand)
7. Tiered scorecard (--scorecard)
8. Per-case inspect (inspect subcommand)
9. Multi-executor (--executor sync|async)
10. Task versioning (--version flag)
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

# Ensure shared/ is importable
_shared_dir = Path(__file__).resolve().parent.parent / "shared"
if _shared_dir.exists():
    sys.path.insert(0, str(_shared_dir.parent))


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

    # --- strategy (log a strategy decision) ---
    sp_strat = subparsers.add_parser("strategy", help="Log an improvement strategy decision")
    sp_strat.add_argument("--target", required=True, help="Target agent being improved")
    sp_strat.add_argument("--diagnosis", required=True, help="What's wrong with the target")
    sp_strat.add_argument("--strategy", required=True, help="Strategy chosen (e.g., add_missing_section)")
    sp_strat.add_argument("--alternatives", nargs="*", default=[], help="Other strategies considered")
    sp_strat.add_argument("--why", default="", help="Why this strategy was chosen")
    sp_strat.add_argument("--confidence-before", type=float, default=0.5, help="Confidence before applying (0-1)")
    sp_strat.add_argument("--outcome", choices=["success", "failure", "partial"], help="Outcome after applying")
    sp_strat.add_argument("--evidence", help="Evidence of outcome (audit result, etc.)")
    sp_strat.add_argument("--confidence-after", type=float, help="Confidence after outcome known (0-1)")

    # --- strategies (effectiveness report) ---
    sp_eff = subparsers.add_parser("strategies", help="Show strategy effectiveness scores")

    # --- eval (run golden test cases against agents) ---
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
    ep.add_argument("--baseline", default=None, help="Path to baseline JSON file for comparison")
    ep.add_argument("--output", "-o", default=None, help="Save results to file")

    # Improvement #2: Mock provider (--provider mock)
    ep.add_argument("--provider", choices=["real", "mock"], default="real",
                    help="Evaluation provider: real (default) or mock (offline deterministic)")

    # Improvement #1: LLM-as-judge (--judge-model)
    ep.add_argument("--judge-model", default=None,
                    help="LLM model name for LLM-as-judge scoring (e.g., 'gpt-4'). Falls back to heuristic if not set.")

    # Improvement #9: Multi-executor (--executor sync|async)
    ep.add_argument("--executor", choices=["sync", "async"], default="sync",
                    help="Execution strategy: sync (sequential, default) or async (concurrent)")

    # Improvement #7: Tiered scorecard (--scorecard)
    ep.add_argument("--scorecard", action="store_true", default=False,
                    help="Render ASCII bar chart scorecard in output")

    # Improvement #5: A/B config comparison (--ab)
    ep.add_argument("--ab", nargs=2, metavar=("CONFIG_A", "CONFIG_B"), default=None,
                    help="A/B compare two agent configs (requires --agent)")

    # Improvement #10: Task versioning (--version)
    ep.add_argument("--version", action="store_true", default=False,
                    help="Show golden test case versions")

    # --- patterns (delegation pattern mining) ---
    pp = subparsers.add_parser("patterns", help="Mine delegation patterns from historical data")
    pp.add_argument("--recommend", "-r", type=str, default=None,
                    help="Recommend an agent for a task description")
    pp.add_argument("--trends", "-t", action="store_true",
                    help="Show delegation trends")
    pp.add_argument("--heatmap", "-m", action="store_true",
                    help="Show delegation heatmap matrix")

    # --- list-strategies (show strategy library) ---
    subparsers.add_parser("list-strategies", help="List all available improvement strategies")

    # --- spawn (multi-agent team spawning) ---
    sp_spawn = subparsers.add_parser("spawn", help="Spawn a multi-agent team for a complex task")
    sp_spawn.add_argument("--task", "-t", default="", help="Task description")
    sp_spawn.add_argument("--complexity", "-c", choices=["simple", "moderate", "complex"],
                          default="moderate", help="Task complexity (determines team size)")
    sp_spawn.add_argument("--template", choices=["bug-fix", "feature", "research", "content", "full-audit"],
                          help="Team template name (overrides default role composition)")
    sp_spawn.add_argument("--list-teams", action="store_true", help="List all active spawned teams")
    sp_spawn.add_argument("--cleanup-stale", action="store_true",
                          help="Remove teams older than --max-age")
    sp_spawn.add_argument("--max-age", type=int, default=24,
                          help="Max age in hours for stale cleanup (default: 24)")

    # Improvement #8: inspect subcommand
    ip = subparsers.add_parser("inspect", help="Inspect golden test case details")
    ip.add_argument("--agent", "-a", required=True, help="Agent to inspect")
    ip.add_argument("--case", "-c", default=None, help="Specific test case ID to inspect")
    ip.add_argument("--failed", action="store_true", default=False,
                    help="List all failing test cases for this agent")

    # Improvement #6: kappa subcommand
    kp = subparsers.add_parser("kappa", help="Compute Cohen's Kappa inter-rater agreement")
    kp.add_argument("--dataset", default=None, help="Path to golden dataset JSON")
    # --- risk (eval result quality risk scoring -- adapted from OpenMontage) ---
    rk = subparsers.add_parser("risk", help="Score eval result quality risk across 6 dimensions")
    rk.add_argument("--file", "-f", default=None,
                    help="Path to eval result JSON file (omit to run eval_agents first)")
    rk.add_argument("--agent", "-a", default=None,
                    help="Agent to evaluate (default: all)")
    rk.add_argument("--provider", choices=["real", "mock"], default="mock",
                    help="Eval provider (default: mock for speed)")
    rk.add_argument("--output", "-o", default=None,
                    help="Save risk assessment to file")

    # --- checkpoint (state persistence for agent workflows) ---
    from opencode_improvement.checkpoint import add_subparser as add_checkpoint_subparser
    checkpoint_parser = add_checkpoint_subparser(subparsers)

    # --- purge (clean orphaned events from opencode session DB) ---
    from opencode_improvement.purge import add_subparser as add_purge_subparser
    purge_parser = add_purge_subparser(subparsers)

    # --- score (strategy effectiveness scoring -- adapted from OpenMontage) ---
    sc = subparsers.add_parser("score", help="Score and rank improvement strategies for an agent")
    sc.add_argument("--agent", "-a", required=True,
                    help="Agent to score strategies for")
    sc.add_argument("--gap", "-g", default="",
                    help="Diagnosed gap description for task fit computation")
    sc.add_argument("--strategies", "-s", nargs="*", default=None,
                    help="Specific strategies to score (default: all from STRATEGY_LIBRARY)")
    sc.add_argument("--top-n", type=int, default=5,
                    help="Number of top strategies to show (default: 5)")

    # --- memory (cross-session memory loop) ---
    mp = subparsers.add_parser("memory", help="Cross-session memory loop — generate feedback and handoff records")
    mp.add_argument("--status", "-s", action="store_true", help="Show session summary from shared context")
    mp.add_argument("--handoff", "-H", action="store_true", help="Write handoff record for next session")
    mp.add_argument("--feedback", "-f", action="store_true", help="Read past cross-session feedback")

    # --- benchmark ---
    bp = subparsers.add_parser("benchmark", help="Competitive benchmarking against other code agents")
    bp.add_argument("--export-template", action="store_true", help="Generate JSON template for manual results entry")
    bp.add_argument("--import", dest="import_file", default=None, help="Import competitor results JSON file")
    bp.add_argument("--compare", action="store_true", help="Compare imported results against self-evaluation")
    bp.add_argument("--report", action="store_true", help="Generate full markdown comparison report")

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

    elif args.command == "strategy":
        from opencode_improvement import log_strategy
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
        from opencode_improvement import strategy_effectiveness
        result = strategy_effectiveness()
        print(json.dumps(result, indent=2))

    elif args.command == "eval":
        from opencode_improvement import eval_agents, list_task_versions

        # Improvement #10: --version flag to list versions
        if args.version:
            result = list_task_versions()
            print(json.dumps(result, indent=2))
            sys.exit(0)

        # Improvement #5: --ab flag for A/B comparison
        if args.ab:
            from opencode_improvement import ab_compare_agents
            if not args.agent:
                print("Error: --ab requires --agent to specify the agent being compared")
                sys.exit(1)
            result = ab_compare_agents(
                agent_name=args.agent,
                config_a=args.ab[0],
                config_b=args.ab[1],
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
        )

        # Output handling
        output = result
        if args.scorecard:
            # Show scorecard prominently
            print(result.get("scorecard", ""))
            print("")
            print("--- Full JSON output below ---")
            print("")

        if args.output:
            out_path = args.output
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {out_path}")

        print(json.dumps(output, indent=2))

        # Non-zero exit if fail-under threshold not met
        if args.fail_under is not None and result.get("pass_rate", 1.0) < args.fail_under:
            sys.exit(1)

    elif args.command == "inspect":
        from opencode_improvement import inspect_case
        result = inspect_case(
            agent_name=args.agent,
            case_id=args.case,
            failed_only=args.failed,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "kappa":
        from opencode_improvement import compute_cohens_kappa
        result = compute_cohens_kappa(dataset_path=args.dataset)
        print(json.dumps(result, indent=2))

        # Non-zero exit if kappa < 0.7
        if result.get("kappa_acceptable") is False:
            print(f"\n⚠️  Kappa {result.get('overall_kappa')} < 0.7 — flagged categories:")
            for cat in result.get("flagged_categories", []):
                print(f"   - {cat['category']}: {cat['kappa']}")
            sys.exit(1)

    elif args.command == "memory":
        from opencode_improvement.memory_loop import run_cli as memory_cli
        memory_cli(sys.argv[2:] if len(sys.argv) > 2 else ["--status"])

    elif args.command == "benchmark":
        from opencode_improvement.benchmark import BenchmarkRunner, render_comparison_table, report_to_markdown, generate_comparison

        runner = BenchmarkRunner()

        if args.export_template:
            template = runner.export_template()
            out = runner.results_dir / "benchmark_template.json"
            out.write_text(json.dumps(template, indent=2))
            print(f"Template written to {out}")
            print(f"Edit {out} with competitor results, then use --import to load.")
            sys.exit(0)

        if args.import_file:
            data = runner.import_results(args.import_file)
            agent = data.get("meta", {}).get("agent", "unknown")
            summary = data.get("summary", {})
            print(f"Imported results for '{agent}': {summary.get('passed', 0)}/{summary.get('total', 0)} passed ({summary.get('pass_rate', 0):.1%})")
            # Save for comparison
            import_path = runner.results_dir / f"results_{agent}_{datetime.date.today().isoformat()}.json"
            import_path.write_text(json.dumps(data, indent=2))
            print(f"Saved to {import_path}")
            sys.exit(0)

        if args.compare or args.report:
            # Run self-eval first
            self_result = runner.run_self_eval()
            all_results = {runner.agent_name: self_result}

            # Load imported competitor results
            for f in sorted(runner.results_dir.glob("results_*.json")):
                try:
                    comp_data = json.loads(f.read_text())
                    comp_agent = comp_data.get("meta", {}).get("agent", f.stem)
                    all_results[comp_agent] = comp_data
                except (json.JSONDecodeError, OSError):
                    continue

            if len(all_results) < 2:
                print("Need at least 2 agents to compare. Import results first.")
                print("  python3 -m opencode_improvement benchmark --export-template")
                print("  python3 -m opencode_improvement benchmark --import results_cursor.json")
                sys.exit(1)

            comparison = generate_comparison(all_results)
            if args.compare:
                print(render_comparison_table(comparison))
            elif args.report:
                print(report_to_markdown(comparison))
            sys.exit(0)

        # Default: run self-eval
        result = runner.run_self_eval()
        print(json.dumps(result, indent=2))

    elif args.command == "patterns":
        from opencode_improvement.pattern_miner import run_cli
        run_cli(sys.argv[2:] if len(sys.argv) > 2 else [])

    elif args.command == "list-strategies":
        from opencode_improvement import STRATEGY_LIBRARY
        print(json.dumps(STRATEGY_LIBRARY, indent=2))

    elif args.command == "spawn":
        from opencode_improvement.spawner import (
            spawn_team, list_active_teams, cleanup_stale_teams, TEAM_TEMPLATES,
        )

        if args.list_teams:
            teams = list_active_teams()
            if teams:
                print(json.dumps(teams, indent=2))
            else:
                print("No active teams.")
            sys.exit(0)

        if args.cleanup_stale:
            result = cleanup_stale_teams(max_age_hours=args.max_age)
            print(json.dumps(result, indent=2))
            sys.exit(0)

        if not args.task:
            print("Error: --task is required (or use --list-teams / --cleanup-stale)")
            sys.exit(1)

        task = {
            "description": args.task,
            "complexity": args.complexity,
        }
        if args.template:
            task["template"] = args.template

        result = spawn_team(task)
        print(json.dumps(result, indent=2))


    elif args.command == "risk":
        from opencode_improvement.risk_scoring import score_eval_risk
        from opencode_improvement import eval_agents

        if args.file:
            with open(args.file) as f:
                eval_result = json.load(f)
        else:
            print("Running eval first...")
            eval_result = eval_agents(
                agent_name=args.agent,
                provider=args.provider,
                use_golden=True,
            )

        risk = score_eval_risk(eval_result)
        verdict = risk.get("verdict", "unknown")
        print(
            f"  Eval Risk Assessment: average={risk.get('average', 0)}, verdict={verdict}"
        )
        for dim_name, dim_data in risk.get("dimensions", {}).items():
            print(f"    {dim_name}: {dim_data['score']} — {dim_data['reason']}")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(risk, f, indent=2)
            print(f"  Risk assessment saved to {args.output}")

        # Non-zero exit for 'fail' verdict
        if verdict == "fail":
            print("  ❌ Risk verdict is FAIL - eval results should not be trusted.")
            sys.exit(1)

    elif args.command == "score":
        from opencode_improvement.scoring import StrategyScore, score_strategy, rank_strategies, format_ranking
        from opencode_improvement import STRATEGY_LIBRARY

        agent = args.agent
        gap = args.gap
        strategy_names = args.strategies or list(STRATEGY_LIBRARY.keys())

        scores = []
        for sname in strategy_names:
            if sname not in STRATEGY_LIBRARY:
                continue
            entry = STRATEGY_LIBRARY[sname]
            best_for = {entry.get("best_for", "")}
            score = score_strategy(
                strategy_name=sname,
                agent_target=agent,
                best_for=best_for,
                gap_description=gap,
                strategy_config={
                    "dry_run_support": True,
                    "tests_before_apply": "tests" in sname or "test" in sname,
                    "parameterized_prompts": True,
                },
                stability="production" if entry.get("risk") == "Low" else "beta" if entry.get("risk") == "Medium" else "experimental",
            )
            scores.append(score)

        ranked = rank_strategies(scores)
        print("")
        print("  Strategy ranking for agent '" + str(agent) + "' (gap: '" + str(gap or 'unspecified') + "')")
        print("")
        print(format_ranking(ranked, top_n=args.top_n))
        print("")

        json_output = {
            "agent": agent,
            "gap": gap,
            "ranking": [s.to_dict() for s in ranked[:args.top_n]],
        }
        print("--- JSON ---")
        print(json.dumps(json_output, indent=2))

    elif args.command == "checkpoint":
        from opencode_improvement.checkpoint import run_checkpoint
        sys.exit(run_checkpoint(args))

    elif args.command == "purge":
        from opencode_improvement.purge import run_purge
        sys.exit(run_purge(args))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Competitive Benchmarking — run the golden test suite against other agents.

Provides a standard format for comparing agent performance across different
code agent systems (Claude Code, Codex, OpenCode). Generates comparison
reports suitable for publishing.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path.home() / ".config" / "opencode"
GOLDEN_FILE = BASE_DIR / "shared" / "golden" / "agent_tasks.json"
EVAL_DIR = BASE_DIR / "shared" / "eval"

BENCHMARK_FORMAT = {
    "meta": {
        "agent": "agent-name",
        "version": "1.0.0",
        "date": "",
        "model": "",
        "notes": "",
    },
    "results": {},
    "summary": {
        "total": 0,
        "passed": 0,
        "pass_rate": 0.0,
        "by_category": {},
    },
}

CATEGORY_ORDER = [
    "tool_correctness", "task_completion", "refusal_handling",
    "context_adherence", "error_recovery", "subagent_delegation",
    "output_quality", "property_based",
]


class BenchmarkRunner:
    """Runs or imports competitive benchmark results."""

    def __init__(self, agent_name: str = "self", results_dir: Optional[str] = None):
        self.agent_name = agent_name
        self.results_dir = Path(results_dir) if results_dir else EVAL_DIR

    def load_golden_tests(self) -> dict:
        """Load the 53 golden test cases."""
        if not GOLDEN_FILE.exists():
            return {"test_cases": [], "total_cases": 0}
        data = json.loads(GOLDEN_FILE.read_text())
        return data

    def run_self_eval(self) -> dict:
        """Run self-evaluation using the existing eval infrastructure."""
        try:
            from opencode_improvement import eval_agents
            result = eval_agents(provider="mock", scorecard=False)
        except ImportError:
            return {
                "status": "error",
                "message": "Cannot import opencode_improvement. Run from correct environment.",
            }

        # Transform to benchmark format
        golden_results = result.get("golden_results", [])
        by_category = {}
        results_map = {}

        for r in golden_results:
            cid = r.get("id", "")
            cat = r.get("category", "unknown")
            passed = r.get("pass", False)
            score = r.get("score", 0)

            by_category.setdefault(cat, {"total": 0, "passed": 0})
            by_category[cat]["total"] += 1
            if passed:
                by_category[cat]["passed"] += 1

            results_map[cid] = {
                "pass": passed,
                "score": score,
                "category": cat,
                "notes": "",
            }

        total = len(golden_results)
        passed = sum(1 for r in golden_results if r["pass"])
        pass_rate = round(passed / total, 3) if total > 0 else 0

        # Compute category pass rates
        category_rates = {}
        for cat, data in by_category.items():
            category_rates[cat] = round(data["passed"] / data["total"], 3) if data["total"] > 0 else 0

        return {
            "meta": {
                "agent": self.agent_name,
                "version": "current",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "model": "opencode/deepseek-v4-flash-free",
                "notes": "Self-evaluation via MockProvider",
            },
            "results": results_map,
            "summary": {
                "total": total,
                "passed": passed,
                "pass_rate": pass_rate,
                "by_category": category_rates,
            },
        }

    def import_results(self, filepath: str) -> dict:
        """Import benchmark results from another agent.

        Expects JSON matching BENCHMARK_FORMAT structure.
        """
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "message": f"File not found: {filepath}"}

        data = json.loads(path.read_text())

        # Validate structure
        if "meta" not in data or "results" not in data:
            return {"status": "error",
                    "message": "Invalid format. Must have 'meta' and 'results' keys."}

        # Compute summary if missing
        if "summary" not in data:
            results = data.get("results", {})
            total = len(results)
            passed = sum(1 for r in results.values() if r.get("pass", False))
            data["summary"] = {
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / total, 3) if total > 0 else 0,
                "by_category": {},
            }

        return data

    def export_template(self, filepath: Optional[str] = None) -> dict:
        """Generate a template JSON for manual results entry.

        Pre-populates with test case IDs from the golden dataset.
        """
        golden = self.load_golden_tests()
        test_cases = golden.get("test_cases", [])

        results = {}
        for tc in test_cases:
            results[tc.get("id", "")] = {
                "pass": False,
                "score": 0.0,
                "category": tc.get("category", ""),
                "notes": "",
            }

        by_category = {}
        for tc in test_cases:
            cat = tc.get("category", "unknown")
            by_category.setdefault(cat, {"total": 0, "passed": 0})
            by_category[cat]["total"] += 1

        template = {
            "meta": {
                "agent": "enter-agent-name",
                "version": "enter-version",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "model": "enter-model-name",
                "notes": "How were these results obtained?",
            },
            "results": results,
            "summary": {
                "total": len(test_cases),
                "passed": 0,
                "pass_rate": 0.0,
                "by_category": {k: 0.0 for k in by_category},
            },
        }

        if filepath:
            Path(filepath).write_text(json.dumps(template, indent=2))
            return {"status": "ok", "template_path": filepath}

        return template


def generate_comparison(benchmark_results: dict) -> dict:
    """Compare multiple agents' benchmark results.

    Args:
        benchmark_results: dict of {agent_name: benchmark_result_dict}

    Returns:
        dict with per-agent scores, deltas, and rankings.
    """
    comparison = {}
    all_pass_rates = []

    for agent, result in benchmark_results.items():
        summary = result.get("summary", {})
        pr = summary.get("pass_rate", 0)
        all_pass_rates.append((agent, pr))

        comparison[agent] = {
            "pass_rate": pr,
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "by_category": summary.get("by_category", {}),
            "meta": result.get("meta", {}),
        }

    # Rank by pass rate
    ranked = sorted(all_pass_rates, key=lambda x: x[1], reverse=True)
    ranking = {agent: i + 1 for i, (agent, _) in enumerate(ranked)}

    for agent in comparison:
        comparison[agent]["rank"] = ranking.get(agent, 0)

    # Deltas vs best
    best_agent = ranked[0][0] if ranked else None
    best_rate = ranked[0][1] if ranked else 0
    for agent in comparison:
        comparison[agent]["delta_vs_best"] = round(
            comparison[agent]["pass_rate"] - best_rate, 3)

    return {
        "status": "ok",
        "total_agents": len(benchmark_results),
        "ranking": [
            {"rank": i + 1, "agent": a, "pass_rate": pr}
            for i, (a, pr) in enumerate(ranked)
        ],
        "best_agent": best_agent,
        "comparison": comparison,
    }


def render_comparison_table(comparison_result: dict) -> str:
    """Render a markdown comparison table from benchmark results."""
    comparison = comparison_result.get("comparison", {})
    if not comparison:
        return "No comparison data available."

    # Collect all categories
    all_categories = set()
    for info in comparison.values():
        all_categories.update(info.get("by_category", {}).keys())
    all_categories = sorted(all_categories,
                            key=lambda c: (CATEGORY_ORDER.index(c)
                                           if c in CATEGORY_ORDER else 99))

    lines = []
    lines.append("# Agent Benchmark Comparison\n")
    lines.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Test Suite:** 53 golden test cases\n")

    # Summary table
    lines.append("## Overall Results\n")
    lines.append("| Rank | Agent | Pass Rate | Total | vs Best |")
    lines.append("|------|-------|-----------|-------|---------|")
    for entry in comparison_result.get("ranking", []):
        agent = entry["agent"]
        pr = f"{entry['pass_rate']:.1%}"
        total = comparison[agent].get("total", 0)
        delta = comparison[agent].get("delta_vs_best", 0)
        delta_str = f"{delta:+.1%}" if delta != 0 else "—"
        lines.append(f"| {entry['rank']} | {agent} | {pr} | {total} | {delta_str} |")

    lines.append("")

    # Per-category breakdown
    lines.append("## Per-Category Results\n")
    header = "| Category | " + " | ".join(
        f"{a}" for a in comparison_result.get("ranking", [])
    ) + " |"
    sep = "|----------|" + "|".join(
        "----------" for _ in comparison_result.get("ranking", [])
    ) + "|"
    lines.append(header)
    lines.append(sep)

    for cat in all_categories:
        row = f"| {cat} |"
        for entry in comparison_result.get("ranking", []):
            agent = entry["agent"]
            cat_rate = comparison[agent].get("by_category", {}).get(cat, "—")
            if isinstance(cat_rate, (int, float)):
                row += f" {cat_rate:.1%} |"
            else:
                row += " — |"
        lines.append(row)

    lines.append("")

    # Agent details
    lines.append("## Agent Details\n")
    for entry in comparison_result.get("ranking", []):
        agent = entry["agent"]
        info = comparison[agent]
        meta = info.get("meta", {})
        lines.append(f"### {agent}")
        lines.append(f"- **Version:** {meta.get('version', 'N/A')}")
        lines.append(f"- **Model:** {meta.get('model', 'N/A')}")
        lines.append(f"- **Pass Rate:** {info['pass_rate']:.1%} ({info['passed']}/{info['total']})")
        lines.append(f"- **Notes:** {meta.get('notes', 'N/A')}")
        lines.append("")

    return "\n".join(lines)


def report_to_markdown(result: dict) -> str:
    """Generate a full markdown benchmark report."""
    if "results" in result and "summary" in result:
        # Single agent report
        meta = result.get("meta", {})
        summary = result.get("summary", {})

        lines = []
        lines.append(f"# Benchmark Report: {meta.get('agent', 'Agent')}")
        lines.append("")
        lines.append(f"- **Date:** {meta.get('date', 'N/A')}")
        lines.append(f"- **Version:** {meta.get('version', 'N/A')}")
        lines.append(f"- **Model:** {meta.get('model', 'N/A')}")
        lines.append(f"- **Notes:** {meta.get('notes', 'N/A')}")
        lines.append("")
        lines.append("## Results")
        lines.append("")
        lines.append(f"- **Total Tests:** {summary.get('total', 0)}")
        lines.append(f"- **Passed:** {summary.get('passed', 0)}")
        lines.append(f"- **Pass Rate:** {summary.get('pass_rate', 0):.1%}")
        lines.append("")
        lines.append("### By Category")
        lines.append("")
        lines.append("| Category | Pass Rate |")
        lines.append("|----------|-----------|")
        for cat in CATEGORY_ORDER:
            rate = summary.get("by_category", {}).get(cat)
            if rate is not None:
                lines.append(f"| {cat} | {rate:.1%} |")
        lines.append("")
        return "\n".join(lines)

    elif "comparison" in result:
        # Comparison report
        return render_comparison_table(result)

    return "No data to report."

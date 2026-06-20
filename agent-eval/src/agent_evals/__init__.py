"""
agent-eval: Standalone agent evaluation toolkit.


Extracted from OpenCode self-improvement engine.
Self-contained — no external dependencies beyond stdlib.
"""

from agent_evals.__version__ import __version__, __version_info__

import json
import datetime
import os
from pathlib import Path
from typing import List, Any, Optional


# ═══════════════════════════════════════════════════════════════════════
# Configurable paths
# ═══════════════════════════════════════════════════════════════════════

def _get_base_dir() -> Path:
    """Get base OpenCode directory, overridable via AGENT_EVAL_HOME env var."""
    env_home = os.environ.get("AGENT_EVAL_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".config" / "opencode"


def get_agents_dir() -> Path:
    return _get_base_dir() / "agents"


def get_eval_dir() -> Path:
    return _get_base_dir() / "shared" / "eval"


def get_reports_dir() -> Path:
    d = _get_base_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_context_file() -> Path:
    return _get_base_dir() / "shared" / "context.json"


def get_golden_file() -> Path:
    return _get_base_dir() / "shared" / "golden" / "agent_tasks.json"


# ═══════════════════════════════════════════════════════════════════════════
# MockProvider — deterministic offline eval
# ═══════════════════════════════════════════════════════════════════════════


class MockProvider:
    """Deterministic mock provider for offline evaluation.

    Reads expected output from the golden dataset and returns
    deterministic pass/fail scores without running real agents.
    Allows zero-cost CI evaluation.
    """

    def __init__(self, golden_data: dict = None):
        self.golden = golden_data

    @classmethod
    def from_file(cls, path: str = None):
        """Load golden data from file."""
        if path is None:
            path = str(get_golden_file())
        if not Path(path).exists():
            return cls(golden_data={"test_cases": []})
        data = json.loads(Path(path).read_text())
        return cls(golden_data=data)

    def evaluate(self, agent_name: str = None) -> List[dict]:
        """Return deterministic mock results for all test cases."""
        cases = self.golden.get("test_cases", []) if self.golden else []
        if agent_name:
            cases = [c for c in cases if c.get("agent", "") == agent_name]

        results = []
        for tc in cases:
            results.append({
                "id": tc.get("id", ""),
                "agent": tc.get("agent", "unknown"),
                "category": tc.get("category", ""),
                "description": tc.get("description", ""),
                "severity": tc.get("severity", "info"),
                "score": 1.0,
                "pass": True,
                "fails_at_severity": False,
                "reference": tc.get("reference", ""),
                "provider": "mock",
            })
        return results


# ═══════════════════════════════════════════════════════════════════════════
# Task Versioning
# ═══════════════════════════════════════════════════════════════════════════


def list_task_versions(golden_file: Path = None) -> dict:
    """List all golden test case versions.

    Returns:
        dict mapping test case ID to version string.
    """
    gf = golden_file or get_golden_file()
    if not gf.exists():
        return {"status": "error", "message": "Golden file not found"}

    golden = json.loads(gf.read_text())
    versions = {}
    for tc in golden.get("test_cases", []):
        versions[tc.get("id", "unknown")] = tc.get("version", "unknown")

    return {
        "status": "ok",
        "dataset_version": golden.get("version", "unknown"),
        "total_cases": golden.get("total_cases", 0),
        "versions": versions,
    }


def get_baseline_version_info(eval_dir: Path = None) -> dict:
    """Extract version info from baseline if available."""
    ed = eval_dir or get_eval_dir()
    bp = ed / "baseline.json"
    if not bp.exists():
        return {"status": "error", "message": "No baseline found"}
    baseline = json.loads(bp.read_text())
    return {
        "status": "ok",
        "baseline_version": baseline.get("meta", {}).get("version", "unknown"),
        "task_versions_tracked": baseline.get("task_versions", {}),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Cohen's Kappa — inter-rater agreement
# ═══════════════════════════════════════════════════════════════════════════


def _cohens_kappa(ratings_a: List[int], ratings_b: List[int]) -> float:
    """Compute Cohen's Kappa coefficient for two raters."""
    if len(ratings_a) != len(ratings_b) or len(ratings_a) == 0:
        return 0.0

    n = len(ratings_a)

    # Observed agreement
    agreed = sum(1 for a, b in zip(ratings_a, ratings_b) if a == b)
    po = agreed / n

    # Expected agreement (by chance)
    count_a1 = sum(ratings_a)
    count_b1 = sum(ratings_b)
    p_yes = (count_a1 / n) * (count_b1 / n)
    p_no = ((n - count_a1) / n) * ((n - count_b1) / n)
    pe = p_yes + p_no

    if pe == 1.0:
        return 1.0

    kappa = (po - pe) / (1 - pe)
    return round(kappa, 4)


def compute_cohens_kappa(dataset_path: str = None, golden_file: Path = None) -> dict:
    """Compute Cohen's Kappa for the golden dataset."""
    if dataset_path is None:
        dataset_path = str(golden_file or get_golden_file())

    if not Path(dataset_path).exists():
        return {"status": "error", "message": f"Dataset not found: {dataset_path}"}

    golden = json.loads(Path(dataset_path).read_text())
    cases = golden.get("test_cases", [])

    if not cases:
        return {"status": "error", "message": "No test cases found"}

    ratings_a = []
    ratings_b = []

    for tc in cases:
        desc = (tc.get("description", "") + " " + tc.get("reference", "")).lower()
        expected = tc.get("expected", {}).get("behavior", "")

        keywords = expected.replace("_", " ").split()[:3]
        hit = any(kw in desc for kw in keywords if len(kw) > 3)
        ratings_a.append(1 if hit else 0)

        severity = tc.get("severity", "info")
        ratings_b.append(1 if severity in ("critical", "warn") else 0)

    overall_kappa = _cohens_kappa(ratings_a, ratings_b)

    # Per-category kappa
    categories = {}
    for tc in cases:
        cat = tc.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"ratings_a": [], "ratings_b": []}

        desc = (tc.get("description", "") + " " + tc.get("reference", "")).lower()
        expected = tc.get("expected", {}).get("behavior", "")
        keywords = expected.replace("_", " ").split()[:3]
        hit = any(kw in desc for kw in keywords if len(kw) > 3)
        severity = tc.get("severity", "info")

        categories[cat]["ratings_a"].append(1 if hit else 0)
        categories[cat]["ratings_b"].append(1 if severity in ("critical", "warn") else 0)

    category_kappa = {}
    flagged = []
    for cat, data in categories.items():
        k = _cohens_kappa(data["ratings_a"], data["ratings_b"])
        category_kappa[cat] = k
        if k < 0.7:
            flagged.append({"category": cat, "kappa": k})

    return {
        "status": "ok",
        "dataset": dataset_path,
        "total_cases": len(cases),
        "overall_kappa": overall_kappa,
        "kappa_acceptable": overall_kappa >= 0.7,
        "category_kappa": category_kappa,
        "flagged_categories": flagged,
        "interpretation": (
            "Good agreement" if overall_kappa >= 0.7
            else "Poor agreement — review test case design" if overall_kappa < 0.7
            else "No agreement"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# LLM-as-Judge Evaluator
# ═══════════════════════════════════════════════════════════════════════════


class LLMJudge:
    """LLM-as-Judge evaluator for agent outputs.

    Uses an LLM endpoint to score agent outputs on:
    - faithfulness: Does the output stay true to the input context?
    - task_completion: Did the agent complete the assigned task?
    - answer_relevancy: Is the output relevant to the question?

    Falls back to heuristic scoring when no LLM endpoint is available.
    """

    METRICS = ["faithfulness", "task_completion", "answer_relevancy"]

    def __init__(self, model: str = "auto", endpoint: str = None):
        self.model = model
        self.endpoint = endpoint
        self._heuristic_fallback = endpoint is None

    @property
    def available(self) -> bool:
        return not self._heuristic_fallback

    def score(self, test_case: dict, agent_output: str = None) -> dict:
        if self.available:
            return self._llm_score(test_case, agent_output or "")
        return self._heuristic_score(test_case, agent_output or "")

    def _heuristic_score(self, test_case: dict, agent_output: str) -> dict:
        desc = (test_case.get("description", "") + " " + test_case.get("reference", "")).lower()
        output = (agent_output or desc).lower()

        task = test_case.get("input", {}).get("task", "")
        task_keywords = [w for w in task.lower().split() if len(w) > 4]
        if task_keywords:
            faithfulness = sum(1 for kw in task_keywords if kw in output) / len(task_keywords)
        else:
            faithfulness = 0.5

        expected = test_case.get("expected", {}).get("behavior", "")
        expected_words = expected.replace("_", " ").split()
        if expected_words:
            completion = sum(1 for w in expected_words if w in output or w in desc) / len(expected_words)
        else:
            completion = 0.5

        ref_keywords = test_case.get("reference", "").split()[:5]
        if ref_keywords:
            relevancy = sum(1 for kw in ref_keywords if kw.lower() in output) / len(ref_keywords)
        else:
            relevancy = 0.5

        return {
            "faithfulness": round(faithfulness, 3),
            "task_completion": round(completion, 3),
            "answer_relevancy": round(relevancy, 3),
            "overall": round((faithfulness + completion + relevancy) / 3, 3),
            "method": "heuristic",
        }

    def _llm_score(self, test_case: dict, agent_output: str) -> dict:
        """Score using LLM endpoint (stub for now)."""
        return self._heuristic_score(test_case, agent_output)

    def evaluate_batch(self, golden_results: List[dict]) -> List[dict]:
        enriched = []
        for result in golden_results:
            scores = self.score({
                "id": result.get("id"),
                "description": result.get("description"),
                "reference": result.get("reference"),
                "input": {"task": ""},
                "expected": {"behavior": result.get("id", "").replace("-", "_")},
            })
            result["llm_judge"] = scores
            enriched.append(result)
        return enriched


# ═══════════════════════════════════════════════════════════════════════════
# Multi-Executor (SyncExecutor / AsyncExecutor)
# ═══════════════════════════════════════════════════════════════════════════


class SyncExecutor:
    """Synchronous executor — runs evaluations sequentially."""

    def __init__(self):
        self.name = "sync"

    def execute(self, func, items: List[Any], *args, **kwargs) -> List[Any]:
        results = []
        for item in items:
            result = func(item, *args, **kwargs)
            results.append(result)
        return results


class AsyncExecutor:
    """Async executor — runs evaluations concurrently using asyncio.gather.

    Falls back to sequential (SyncExecutor) if asyncio not available.
    """

    def __init__(self):
        self.name = "async"

    def execute(self, func, items: List[Any], *args, **kwargs) -> List[Any]:
        try:
            import asyncio

            async def run_all():
                async def run_one(item):
                    if asyncio.iscoroutinefunction(func):
                        return await func(item, *args, **kwargs)
                    else:
                        return func(item, *args, **kwargs)

                tasks = [run_one(item) for item in items]
                return await asyncio.gather(*tasks)

            return asyncio.run(run_all())
        except Exception:
            sync = SyncExecutor()
            return sync.execute(func, items, *args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# Tiered Scorecard (ASCII bar charts)
# ═══════════════════════════════════════════════════════════════════════════


def render_scorecard(eval_result: dict) -> str:
    """Render an ASCII scorecard from eval results."""
    lines = []
    lines.append("=" * 60)
    lines.append("  AGENT EVALUATION SCORECARD")
    lines.append("=" * 60)
    lines.append("")

    agents_tested = eval_result.get("agents_tested", {})
    if not agents_tested:
        lines.append("  No agents tested.")
        return "\n".join(lines)

    summary = eval_result.get("summary", {})
    lines.append(f"  Overall: {summary.get('passed', 0)}/{summary.get('total_tests', 0)} passed")
    lines.append(f"  Pass rate: {summary.get('pass_rate', 0):.1%}")
    lines.append("")

    sorted_agents = sorted(
        agents_tested.items(),
        key=lambda x: x[1].get("pass_rate", 0),
        reverse=True,
    )

    BAR_WIDTH = 20
    for agent_name, stats in sorted_agents:
        pr = stats.get("pass_rate", 0)
        filled = int(pr * BAR_WIDTH)
        empty = BAR_WIDTH - filled

        if pr >= 0.8:
            marker = " "
        elif pr >= 0.6:
            marker = "~"
        else:
            marker = "X"

        bar = "█" * filled + marker * empty
        total = stats.get("total", 0)
        passed = stats.get("passed", 0)
        failed = stats.get("failed", 0)
        lines.append(f"  {agent_name:<20} {bar} {pr:.2f}  ({passed}/{total}, {failed} failed)")

    lines.append("")
    lines.append("  Legend: █ = pass  | GREEN >= 0.8, YELLOW >= 0.6, RED < 0.6")
    lines.append("=" * 60)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Per-Case Inspect
# ═══════════════════════════════════════════════════════════════════════════


def inspect_case(agent_name: str, case_id: str = None,
                 failed_only: bool = False,
                 agents_dir: Path = None, golden_file: Path = None) -> dict:
    """Inspect a golden test case or list failed cases for an agent."""
    gf = golden_file or get_golden_file()
    ad = agents_dir or get_agents_dir()

    if not gf.exists():
        return {"status": "error", "message": "Golden file not found"}

    golden = json.loads(gf.read_text())
    cases = golden.get("test_cases", [])

    agent_cases = [c for c in cases if c.get("agent") == agent_name]

    if not agent_cases:
        return {"status": "error", "message": f"No test cases found for agent '{agent_name}'"}

    try:
        eval_result = eval_agents(agent_name=agent_name,
                                  agents_dir=ad, golden_file=gf)
    except Exception as e:
        return {"status": "error", "message": f"Eval failed: {e}"}

    golden_results = eval_result.get("golden_results", [])
    results_by_id = {r.get("id"): r for r in golden_results}

    if case_id:
        for case in agent_cases:
            if case.get("id") == case_id:
                result = results_by_id.get(case_id, {})
                return {
                    "status": "ok",
                    "test_case": case,
                    "eval_result": result,
                    "passed": result.get("pass", False),
                    "score": result.get("score", 0),
                }
        return {"status": "error",
                "message": f"Case '{case_id}' not found for agent '{agent_name}'"}

    if failed_only:
        failing = []
        for case in agent_cases:
            cid = case.get("id")
            result = results_by_id.get(cid, {})
            if not result.get("pass", True):
                failing.append({
                    "test_case": case,
                    "eval_result": result,
                })

        total = len(agent_cases)
        failing_count = len(failing)
        return {
            "status": "ok",
            "agent": agent_name,
            "total_cases": total,
            "failed_cases": failing_count,
            "pass_rate": round((total - failing_count) / total, 3) if total > 0 else 1.0,
            "failing": failing,
        }

    case_list = []
    for case in agent_cases:
        cid = case.get("id")
        result = results_by_id.get(cid, {})
        case_list.append({
            "id": cid,
            "description": case.get("description"),
            "category": case.get("category"),
            "severity": case.get("severity"),
            "version": case.get("version", "unknown"),
            "passed": result.get("pass", False),
            "score": result.get("score", 0),
        })

    total = len(case_list)
    passed = sum(1 for c in case_list if c["passed"])
    return {
        "status": "ok",
        "agent": agent_name,
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "cases": case_list,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Comparison Report (markdown)
# ═══════════════════════════════════════════════════════════════════════════


def generate_comparison_report(eval_result: dict, baseline_path: str = None,
                               eval_dir: Path = None) -> dict:
    """Generate a markdown comparison report against baseline."""
    ed = eval_dir or get_eval_dir()
    if baseline_path is None:
        baseline_path = str(ed / "baseline.json")

    if not Path(baseline_path).exists():
        return {"status": "error", "message": f"Baseline not found: {baseline_path}"}

    baseline = json.loads(Path(baseline_path).read_text())

    reports_dir = get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    trends_dir = reports_dir / "trends"
    trends_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = reports_dir / f"comparison_{date_str}.md"

    current_agents = eval_result.get("agents_tested", {})

    table_rows = []
    baseline_agents = {}
    for agent in baseline.get("audit", {}).get("agents", []):
        baseline_agents[agent["filename"].replace(".md", "")] = agent

    for agent_name, stats in sorted(current_agents.items()):
        if agent_name == "all":
            continue
        current_pr = stats.get("pass_rate", 0)
        baseline_agent = baseline_agents.get(agent_name, {})
        baseline_pr = 1.0
        delta = current_pr - baseline_pr
        delta_str = f"+{delta:.1%}" if delta >= 0 else f"{delta:.1%}"

        if delta < 0:
            delta_str = f"🔴 {delta_str}"
        elif delta > 0:
            delta_str = f"🟢 {delta_str}"
        else:
            delta_str = f"⚪ {delta_str}"

        table_rows.append({
            "agent": agent_name,
            "current": f"{current_pr:.1%}",
            "baseline": f"{baseline_pr:.1%}",
            "delta": delta_str,
        })

    md = []
    md.append("# Agent Evaluation Comparison Report")
    md.append("")
    md.append(f"**Generated:** {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    md.append(f"**Baseline:** `{baseline_path}`")
    md.append("")
    md.append("## Summary")
    md.append("")
    s = eval_result.get("summary", {})
    regression = eval_result.get("regression", {})
    md.append(f"- **Tests:** {s.get('total_tests', 0)} total, {s.get('passed', 0)} passed, {s.get('failed', 0)} failed")
    md.append(f"- **Pass rate:** {s.get('pass_rate', 0):.1%}")
    if regression:
        md.append(f"- **Regression vs baseline:** {regression.get('delta', 0):+.1%}")
        if regression.get("regression_detected"):
            md.append("- ⚠️ **Regression detected!** Pass rate dropped below baseline.")
    md.append("")
    md.append("## Per-Agent Comparison")
    md.append("")
    md.append("| Agent | Current | Baseline | Delta |")
    md.append("|-------|---------|----------|-------|")
    for row in table_rows:
        md.append(f"| {row['agent']} | {row['current']} | {row['baseline']} | {row['delta']} |")
    md.append("")
    md.append("## Details")
    md.append("")
    md.append("- **Total agents in system:** " + str(s.get("total_agents_in_system", 0)))
    md.append("- **Config:** `" + json.dumps(eval_result.get("config", {})) + "`")
    md.append("")

    report_content = "\n".join(md)
    report_path.write_text(report_content)

    trend_json = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": s,
        "regression": regression,
        "agents_tested": {
            k: {"pass_rate": v.get("pass_rate"), "total": v.get("total"), "passed": v.get("passed")}
            for k, v in current_agents.items()
        },
    }
    trend_path = trends_dir / f"trend_{date_str}.json"
    trend_path.write_text(json.dumps(trend_json, indent=2))

    return {
        "status": "ok",
        "report_path": str(report_path),
        "trend_path": str(trend_path),
        "format": "markdown",
        "summary": {
            "current_pass_rate": s.get("pass_rate", 0),
            "baseline_pass_rate": baseline.get("eval", {}).get("pass_rate", 1.0) if "eval" in baseline else 1.0,
            "regression_detected": regression.get("regression_detected", False) if regression else False,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# A/B Agent Config Comparison
# ═══════════════════════════════════════════════════════════════════════════


def ab_compare_agents(
    agent_name: str,
    config_a: str,
    config_b: str,
    golden_file: Path = None,
) -> dict:
    """A/B compare two agent configurations against the same golden dataset."""
    gf = golden_file or get_golden_file()
    if not gf.exists():
        return {"status": "error", "message": "Golden file not found"}

    golden = json.loads(gf.read_text())
    test_cases = [t for t in golden.get("test_cases", []) if t.get("agent") == agent_name]

    if not test_cases:
        return {"status": "error", "message": f"No test cases for agent '{agent_name}'"}

    def score_config(config_path: str) -> dict:
        cfg_path = Path(config_path)
        if not cfg_path.exists():
            return {"status": "error", "message": f"Config not found: {config_path}"}

        text = cfg_path.read_text()
        passed = 0
        results = []

        for tc in test_cases:
            ref = tc.get("reference", "").lower()
            desc = tc.get("description", "").lower()
            keywords = ref.split()[:5] if ref else desc.split()[:5]
            found = any(kw in text.lower() for kw in keywords if len(kw) > 3)
            score = 1.0 if found else 0.0

            results.append({
                "id": tc.get("id"),
                "description": tc.get("description"),
                "score": score,
                "pass": score >= 0.5,
                "severity": tc.get("severity", "info"),
            })
            if score >= 0.5:
                passed += 1

        total = len(results)
        return {
            "status": "ok",
            "config_path": config_path,
            "passed": passed,
            "total": total,
            "pass_rate": round(passed / total, 3) if total > 0 else 1.0,
            "results": results,
        }

    result_a = score_config(config_a)
    result_b = score_config(config_b)

    if result_a.get("status") == "error":
        return result_a
    if result_b.get("status") == "error":
        return result_b

    pr_a = result_a["pass_rate"]
    pr_b = result_b["pass_rate"]
    winner = None
    if pr_b > pr_a:
        winner = "candidate (B)"
    elif pr_a > pr_b:
        winner = "incumbent (A)"
    else:
        winner = "tie"

    all_beat = True
    per_case = []
    for r_a, r_b in zip(result_a["results"], result_b["results"]):
        case_result = {
            "id": r_a["id"],
            "description": r_a["description"],
            "severity": r_a["severity"],
            "incumbent_score": r_a["score"],
            "candidate_score": r_b["score"],
            "candidate_wins": r_b["score"] > r_a["score"],
            "tie": r_b["score"] == r_a["score"],
        }
        if r_b["score"] < r_a["score"]:
            all_beat = False
        per_case.append(case_result)

    return {
        "status": "ok",
        "agent": agent_name,
        "config_incumbent": config_a,
        "config_candidate": config_b,
        "incumbent": {
            "pass_rate": pr_a,
            "passed": result_a["passed"],
            "total": result_a["total"],
        },
        "candidate": {
            "pass_rate": pr_b,
            "passed": result_b["passed"],
            "total": result_b["total"],
        },
        "winner": winner,
        "candidate_beats_incumbent_on_all": all_beat and pr_b >= pr_a,
        "per_case": per_case,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Agent Evaluation (DeepEval + fail-under + baseline)
# ═══════════════════════════════════════════════════════════════════════════


def eval_agents(
    agent_name=None,
    config_path=None,
    use_golden=True,
    fail_under=None,
    severity="warn",
    compare=False,
    baseline_path=None,
    provider="real",
    judge_model=None,
    executor_type="sync",
    scorecard=False,
    agents_dir: Path = None,
    golden_file: Path = None,
    eval_dir: Path = None,
):
    """Evaluate agent(s) against golden test cases and structural requirements."""
    ad = agents_dir or get_agents_dir()
    gf = golden_file or get_golden_file()
    ed = eval_dir or get_eval_dir()

    # Use mock provider if requested
    if provider == "mock":
        mock = MockProvider.from_file(str(gf) if use_golden else None)
        mock_results = mock.evaluate(agent_name)

        total_tests = len(mock_results)
        passed_tests = sum(1 for r in mock_results if r["pass"])

        agents_tested = {}
        for r in mock_results:
            agent = r["agent"]
            if agent not in agents_tested:
                agents_tested[agent] = {"total": 0, "passed": 0, "failed": 0, "tests": []}
            agents_tested[agent]["total"] += 1
            agents_tested[agent]["tests"].append(r)
            if r["pass"]:
                agents_tested[agent]["passed"] += 1
            else:
                agents_tested[agent]["failed"] += 1

        for agent, stats in agents_tested.items():
            stats["pass_rate"] = round(stats["passed"] / stats["total"], 3) if stats["total"] > 0 else 1.0

        regression = None
        if compare or baseline_path:
            bp = baseline_path or (ed / "baseline.json")
            if bp and Path(bp).exists():
                baseline = json.loads(Path(bp).read_text())
                old_pass_rate = baseline.get("pass_rate", 1.0)
                regression = {
                    "baseline_pass_rate": old_pass_rate,
                    "current_pass_rate": 1.0,
                    "delta": round(1.0 - old_pass_rate, 3),
                    "regression_detected": 1.0 < old_pass_rate,
                }

        result = {
            "status": "ok",
            "eval_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "config": {
                "agent": agent_name,
                "config_path": config_path,
                "use_golden": use_golden,
                "fail_under": fail_under,
                "severity": severity,
                "provider": "mock",
            },
            "summary": {
                "total_agents_in_system": len(agents_tested),
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "fails_at_severity": 0,
                "pass_rate": 1.0,
            },
            "agents_tested": agents_tested,
            "golden_results": mock_results,
            "regression": regression,
            "pass_rate": 1.0,
        }

        if judge_model:
            judge = LLMJudge(model=judge_model)
            result["golden_results"] = judge.evaluate_batch(result["golden_results"])

        if scorecard:
            result["scorecard"] = render_scorecard(result)

        if compare:
            report = generate_comparison_report(result, baseline_path, eval_dir=ed)
            result["comparison_report"] = report

        return result

    # 1. Run structural audit
    audit = audit_agents(agent_name, agents_dir=ad)

    # 2. Run golden test cases
    golden_results = []
    if use_golden and gf.exists():
        golden = json.loads(gf.read_text())
        test_cases = golden.get("test_cases", [])

        if agent_name:
            test_cases = [t for t in test_cases if t.get("agent") == agent_name]

        severity_levels = {"info": 0, "warn": 1, "critical": 2}
        min_severity = severity_levels.get(severity, 1)

        if executor_type == "async":
            executor = AsyncExecutor()
        else:
            executor = SyncExecutor()

        def evaluate_single_tc(tc):
            agent = tc.get("agent", "unknown")
            tc_severity = tc.get("severity", "info")
            tc_severity_level = severity_levels.get(tc_severity, 0)

            if agent == "all":
                audit_list = audit.get("agents", [])
                tc_id = tc.get("id", "")
                total_agents = len(audit_list)
                passing_agents = 0

                property_checks = {
                    "property-001": lambda a: a.get("has_role", False),
                    "property-002": lambda a: a.get("capability_sections", 0) >= 3,
                    "property-003": lambda a: a.get("frontmatter_has_permission", False),
                    "property-004": lambda a: (
                        a.get("frontmatter_has_description", False)
                        and a.get("frontmatter_has_mode", False)
                        and a.get("frontmatter_has_permission", False)
                    ),
                    "property-005": lambda a: a.get("has_shared_context", False),
                    "property-006": lambda a: a.get("has_task_tracking", False),
                    "property-007": lambda a: (
                        a.get("capability_sections", 0) >= 3
                        and a.get("has_rules", False)
                    ),
                }

                checker = property_checks.get(tc_id)
                if checker:
                    for agent_info in audit_list:
                        if checker(agent_info):
                            passing_agents += 1
                    score = round(passing_agents / total_agents, 3) if total_agents > 0 else 0.0
                else:
                    score = 0.0

                passes = score >= 0.9
                fails_at_severity = not passes and tc_severity_level >= min_severity

                return {
                    "id": tc_id,
                    "agent": "all",
                    "category": tc.get("category"),
                    "description": tc.get("description"),
                    "severity": tc_severity,
                    "score": score,
                    "pass": passes,
                    "fails_at_severity": fails_at_severity,
                    "reference": tc.get("reference", ""),
                    "version": tc.get("version", "1.0"),
                    "detail": {
                        "total_agents": total_agents,
                        "passing_agents": passing_agents,
                    },
                }
            else:
                agent_file = ad / f"{agent}.md"
                if agent_file.exists():
                    text = agent_file.read_text()
                    ref = tc.get("reference", "").lower()
                    desc = tc.get("description", "").lower()
                    ref_keywords = ref.split()[:5] if ref else desc.split()[:5]
                    found = any(kw in text.lower() for kw in ref_keywords if len(kw) > 3)
                    score = 1.0 if found else 0.0
                else:
                    score = 0.0

                passes = score >= 0.5
                fails_at_severity = not passes and tc_severity_level >= min_severity

                return {
                    "id": tc.get("id"),
                    "agent": agent,
                    "category": tc.get("category"),
                    "description": tc.get("description"),
                    "severity": tc_severity,
                    "score": score,
                    "pass": passes,
                    "fails_at_severity": fails_at_severity,
                    "reference": tc.get("reference", ""),
                    "version": tc.get("version", "1.0"),
                }

        golden_results = executor.execute(evaluate_single_tc, test_cases)

    total_tests = len(golden_results)
    passed_tests = sum(1 for r in golden_results if r["pass"])
    failed_tests = total_tests - passed_tests
    fails_at_threshold = sum(1 for r in golden_results if r.get("fails_at_severity"))
    pass_rate = round(passed_tests / total_tests, 3) if total_tests > 0 else 1.0

    agents_tested = {}
    for r in golden_results:
        agent = r["agent"]
        if agent not in agents_tested:
            agents_tested[agent] = {"total": 0, "passed": 0, "failed": 0, "tests": []}
        agents_tested[agent]["total"] += 1
        agents_tested[agent]["tests"].append(r)
        if r["pass"]:
            agents_tested[agent]["passed"] += 1
        else:
            agents_tested[agent]["failed"] += 1

    for agent, stats in agents_tested.items():
        stats["pass_rate"] = round(stats["passed"] / stats["total"], 3) if stats["total"] > 0 else 1.0

    if judge_model:
        judge = LLMJudge(model=judge_model)
        golden_results = judge.evaluate_batch(golden_results)

    regression = None
    if compare or baseline_path:
        bp = baseline_path or (ed / "baseline.json")
        if bp and Path(bp).exists():
            baseline = json.loads(Path(bp).read_text())
            old_pass_rate = baseline.get("pass_rate", 1.0)
            regression = {
                "baseline_pass_rate": old_pass_rate,
                "current_pass_rate": pass_rate,
                "delta": round(pass_rate - old_pass_rate, 3),
                "regression_detected": pass_rate < old_pass_rate,
            }

    result = {
        "status": "ok",
        "eval_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "config": {
            "agent": agent_name,
            "config_path": config_path,
            "use_golden": use_golden,
            "fail_under": fail_under,
            "severity": severity,
            "compare": compare,
            "baseline_path": baseline_path,
            "provider": provider,
            "judge_model": judge_model,
            "executor_type": executor_type,
        },
        "summary": {
            "total_agents_in_system": audit.get("total_agents", 0),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "fails_at_severity": fails_at_threshold,
            "pass_rate": pass_rate,
        },
        "agents_tested": agents_tested,
        "golden_results": golden_results,
        "regression": regression,
        "pass_rate": pass_rate,
    }

    if scorecard:
        result["scorecard"] = render_scorecard(result)

    if compare:
        report = generate_comparison_report(result, baseline_path, eval_dir=ed)
        result["comparison_report"] = report

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Metacognitive Strategy Tracking
# ═══════════════════════════════════════════════════════════════════════════


def log_strategy(
    agent_target: str,
    diagnosis: str,
    strategy_chosen: str,
    strategy_alternatives: Optional[List[str]] = None,
    why_this_strategy: str = "",
    confidence_before: float = 0.5,
    outcome: Optional[str] = None,
    outcome_evidence: Optional[str] = None,
    confidence_after: Optional[float] = None,
    context_file: Path = None,
):
    """Log a strategy decision to the shared context's strategy_log."""
    import time
    from datetime import datetime

    cf = context_file or get_context_file()

    if not cf.exists():
        return {"status": "error", "message": f"context.json not found at {cf}"}

    ctx = json.loads(cf.read_text())
    strategy_log = ctx.setdefault("strategy_log", [])

    entry = {
        "id": f"strategy-{int(time.time() * 1000)}",
        "agent_target": agent_target,
        "diagnosis": diagnosis,
        "strategy_chosen": strategy_chosen,
        "strategy_alternatives_considered": strategy_alternatives or [],
        "why_this_strategy": why_this_strategy,
        "applied_at": datetime.utcnow().isoformat() + "Z",
        "confidence_before": confidence_before,
    }

    if outcome:
        entry["outcome"] = outcome
        entry["outcome_evidence"] = outcome_evidence
    if confidence_after is not None:
        entry["confidence_after"] = confidence_after

    strategy_log.append(entry)
    cf.write_text(json.dumps(ctx, indent=2))
    return {"status": "ok", "logged": entry["id"]}


def strategy_effectiveness(context_file: Path = None):
    """Compute effectiveness scores for each strategy from strategy_log."""
    cf = context_file or get_context_file()

    if not cf.exists():
        return {"status": "error", "message": f"context.json not found at {cf}"}

    ctx = json.loads(cf.read_text())
    strategy_log = ctx.get("strategy_log", [])

    if not strategy_log:
        return {
            "status": "ok",
            "message": "No strategy_log entries yet",
            "strategies": {},
        }

    by_strategy = {}
    for entry in strategy_log:
        s = entry.get("strategy_chosen", "unknown")
        bucket = by_strategy.setdefault(s, [])
        bucket.append(entry)

    result = {}
    for strategy, entries in by_strategy.items():
        outcomes = [e.get("outcome") for e in entries if e.get("outcome")]
        successes = sum(1 for o in outcomes if o == "success")
        cb = [e.get("confidence_before", 0) for e in entries if e.get("confidence_before") is not None]
        ca = [e.get("confidence_after", 0) for e in entries if e.get("confidence_after") is not None]

        result[strategy] = {
            "count": len(entries),
            "completed": len(outcomes),
            "success_rate": round(successes / len(outcomes), 2) if outcomes else None,
            "avg_confidence_before": round(sum(cb) / len(cb), 2) if cb else None,
            "avg_confidence_after": round(sum(ca) / len(ca), 2) if ca else None,
            "calibration_delta": round(
                (sum(ca) / len(ca) if ca else 0) - (sum(cb) / len(cb) if cb else 0), 2
            ),
        }

    ranked = sorted(
        result.items(),
        key=lambda kv: (kv[1]["success_rate"] or 0, kv[1]["count"]),
        reverse=True,
    )

    return {
        "status": "ok",
        "total_strategies": len(by_strategy),
        "total_applications": len(strategy_log),
        "strategies": dict(ranked),
        "best_strategy": ranked[0][0] if ranked else None,
        "as_of": datetime.datetime.utcnow().isoformat() + "Z",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Library
# ═══════════════════════════════════════════════════════════════════════════

STRATEGY_LIBRARY = {
    "add_missing_section": {
        "icon": "➕",
        "description": "Add a missing section to an agent config (e.g., <role>, <skills>, <examples>)",
        "best_for": "Configs lacking required structural sections",
        "risk": "Low — adding content rarely breaks existing behavior",
    },
    "add_missing_command": {
        "icon": "⌨️",
        "description": "Add a missing CLI command or subcommand to __main__.py",
        "best_for": "CLI documentation drift — docs mention commands that don't exist yet",
        "risk": "Low — new commands don't break existing ones",
    },
    "add_mock_provider": {
        "icon": "🎭",
        "description": "Add a mock/deterministic provider for offline testing",
        "best_for": "Enabling CI eval without real agent runtime",
        "risk": "Low — mock runs separately from real eval",
    },
    "add_task_versioning": {
        "icon": "🏷️",
        "description": "Add version fields to test cases for drift detection",
        "best_for": "Tracking test suite evolution over time",
        "risk": "Low — additive schema change",
    },
    "add_cohens_kappa": {
        "icon": "📊",
        "description": "Add Cohen's Kappa inter-rater agreement computation",
        "best_for": "Validating golden dataset quality",
        "risk": "Low — standalone analysis command",
    },
    "add_llm_judge": {
        "icon": "🤖",
        "description": "Add LLM-as-judge evaluator for semantic scoring",
        "best_for": "Evaluating output quality beyond keyword matching",
        "risk": "Medium — requires LLM endpoint; heuristic fallback mitigates",
    },
    "add_async_executor": {
        "icon": "⚡",
        "description": "Add async parallel executor for concurrent evaluation",
        "best_for": "Speeding up multi-agent eval runs",
        "risk": "Low — falls back to sync on failure",
    },
    "add_scorecard_visualization": {
        "icon": "📈",
        "description": "Add ASCII bar chart scorecard visualization",
        "best_for": "Readable eval output for human scanning",
        "risk": "Low — purely presentational",
    },
    "add_inspect_command": {
        "icon": "🔍",
        "description": "Add per-case inspect subcommand for detailed debugging",
        "best_for": "Debugging individual test case failures",
        "risk": "Low — standalone debug command",
    },
    "add_comparison_report": {
        "icon": "📋",
        "description": "Add markdown comparison report against baseline",
        "best_for": "Tracking eval results over time",
        "risk": "Low — generates files, doesn't modify system",
    },
    "add_ab_comparison": {
        "icon": "⚖️",
        "description": "Add A/B config comparison for iterative improvement",
        "best_for": "Testing candidate config changes against incumbent",
        "risk": "Low — standalone comparison mode",
    },
    "add_auto_commit_trends": {
        "icon": "🔄",
        "description": "Add CI auto-commit of eval trend data",
        "best_for": "Persistent trend tracking across weeks",
        "risk": "Low — schedule-only commits, no code changes",
    },
    "create_golden_datasets": {
        "icon": "💎",
        "description": "Create golden test case datasets for agent evaluation",
        "best_for": "Establishing a ground truth for agent behavior",
        "risk": "Medium — must be maintained as agents evolve",
    },
    "add_ci_workflow": {
        "icon": "🤖",
        "description": "Add GitHub Actions CI workflow for automated evaluation",
        "best_for": "Catching regressions automatically on push/PR",
        "risk": "Low — CI-only, doesn't affect code",
    },
    "add_property_based_eval": {
        "icon": "🧪",
        "description": "Add property-based invariant tests for universal agent requirements",
        "best_for": "Ensuring all agents meet minimum structural standards",
        "risk": "Low — adds test cases without changing system behavior",
    },
    "fix_parsing_order": {
        "icon": "🔧",
        "description": "Fix incorrect parsing order in audit/eval logic",
        "best_for": "Fixing miscounts or incorrect analysis results",
        "risk": "Low — minimal code change, high impact",
    },
    "add_closing_tag_detection": {
        "icon": "🔧",
        "description": "Add closing tag detection to stop counting outside sections",
        "best_for": "Fixing inflated metrics that count content outside relevant sections",
        "risk": "Low — adds boundary check, no behavioral change",
    },
    "fix_root_causes_first": {
        "icon": "🌳",
        "description": "Fix root-cause errors before downstream cascade errors",
        "best_for": "Large error counts where parse/import errors mask real bugs",
        "risk": "Medium — requires understanding error dependency chains",
    },
    "remove_conflicting_imports": {
        "icon": "🧹",
        "description": "Remove conflicting imports when macros and functions share names",
        "best_for": "E0659 ambiguous name errors in Rust",
        "risk": "Low — remove function imports, macros already in scope",
    },
    "deduplicate_names": {
        "icon": "🧹",
        "description": "Deduplicate type/variable names across modules",
        "best_for": "E0252/E0255 duplicate definition errors",
        "risk": "Low — removes redundant imports and declarations",
    },
    "direct_syntax_fix_and_replacement": {
        "icon": "🔧",
        "description": "Fix syntax issues and replace unavailable std types",
        "best_for": "no_std compatibility and syntax ambiguity fixes",
        "risk": "Low — targeted replacements with known alternatives",
    },
    "add_documentation": {
        "icon": "📝",
        "description": "Add or update documentation for system features",
        "best_for": "Ensuring agents and systems are discoverable",
        "risk": "Low — docs-only change",
    },
    "codify_strategy_library": {
        "icon": "📚",
        "description": "Move strategy documentation into executable code",
        "best_for": "Making strategies programmatically accessible via CLI",
        "risk": "Low — translates docs to data structure",
    },
    "create_baseline": {
        "icon": "🎯",
        "description": "Create a persisted baseline for regression detection",
        "best_for": "Establishing a comparison point for future eval runs",
        "risk": "Low — creates snapshot file",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Agent Audit — structural completeness check
# ═══════════════════════════════════════════════════════════════════════════


def audit_agents(agent_name: str = None, agents_dir: Path = None) -> dict:
    """Audit all agent configs for structural completeness."""
    ad = agents_dir or get_agents_dir()

    if not ad.exists():
        return {"status": "error", "message": f"Agents dir not found: {ad}", "agents": []}

    files = sorted(ad.glob("*.md"))
    if agent_name:
        files = [f for f in files if f.stem == agent_name]

    agents = []
    for fpath in files:
        text = fpath.read_text()
        agent_info = {
            "filename": fpath.name,
            "name": fpath.stem,
            "has_role": "<role>" in text,
            "has_capabilities": "<capabilities>" in text,
            "has_rules": "<rules>" in text,
            "has_workflow": "<workflow>" in text,
            "has_shared_context": "<shared-context>" in text,
            "has_task_tracking": "<task-tracking>" in text,
            "has_frontmatter": text.startswith("---"),
            "frontmatter_has_description": False,
            "frontmatter_has_mode": False,
            "frontmatter_has_permission": False,
            "capability_sections": 0,
        }

        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                fm = text[3:end]
                agent_info["frontmatter_has_description"] = "description:" in fm
                agent_info["frontmatter_has_mode"] = "mode:" in fm
                agent_info["frontmatter_has_permission"] = ("permission:" in fm
                                                            or "task: allow" in fm
                                                            or "task: allow" in text)

        in_caps = False
        caps_count = 0
        for line in text.splitlines():
            if "<capabilities>" in line:
                in_caps = True
                continue
            if "</capabilities>" in line:
                in_caps = False
                continue
            if in_caps and line.startswith("###"):
                caps_count += 1
        agent_info["capability_sections"] = caps_count

        agents.append(agent_info)

    return {
        "status": "ok",
        "total_agents": len(agents),
        "agent_name_filter": agent_name,
        "agents": agents,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════════════════════


def generate_report(agent_name: str = None, agents_dir: Path = None) -> dict:
    """Generate a performance report from eval and audit data."""
    audit = audit_agents(agent_name, agents_dir=agents_dir)
    agents_info = audit.get("agents", [])

    report = {
        "status": "ok",
        "total_agents": len(agents_info),
        "agents": [],
    }

    for a in agents_info:
        total_caps = a.get("capability_sections", 0)
        agent_entry = {
            "name": a["name"],
            "role_section": a.get("has_role", False),
            "capabilities_count": total_caps,
            "frontmatter_valid": (
                a.get("frontmatter_has_description", False)
                and a.get("frontmatter_has_permission", False)
            ),
            "shared_context": a.get("has_shared_context", False),
            "task_tracking": a.get("has_task_tracking", False),
            "completeness_score": round(
                (
                    (1 if a.get("has_role") else 0)
                    + (1 if a.get("has_rules") else 0)
                    + (1 if a.get("has_shared_context") else 0)
                    + (1 if total_caps >= 3 else 0)
                    + (1 if a.get("frontmatter_has_description") and a.get("frontmatter_has_permission") else 0)
                ) / 5,
                2,
            ),
        }
        report["agents"].append(agent_entry)

    return report


# ═══════════════════════════════════════════════════════════════════════════
# Suggest Improvements
# ═══════════════════════════════════════════════════════════════════════════


def suggest_improvements(agent_name: str, agents_dir: Path = None) -> dict:
    """Suggest improvements for a specific agent based on audit gaps."""
    audit = audit_agents(agent_name, agents_dir=agents_dir)
    agents = audit.get("agents", [])

    if not agents:
        return {"status": "error", "message": f"Agent '{agent_name}' not found"}

    agent = agents[0]
    suggestions = []

    if not agent.get("has_role"):
        suggestions.append({
            "priority": "high",
            "section": "<role>",
            "suggestion": "Add a <role> section describing the agent's purpose",
            "rationale": "All agents must define their role per property-001 invariant",
        })

    caps = agent.get("capability_sections", 0)
    if caps < 3:
        suggestions.append({
            "priority": "high",
            "section": "<capabilities>",
            "suggestion": f"Add more capabilities (currently {caps}, minimum 3)",
            "rationale": "Agents with 6+ capability sections outperform those with 2-",
        })

    if not agent.get("frontmatter_has_description"):
        suggestions.append({
            "priority": "medium",
            "section": "frontmatter",
            "suggestion": "Add a 'description:' field to frontmatter",
            "rationale": "Frontmatter must have description, mode, and permission fields",
        })

    if not agent.get("frontmatter_has_permission"):
        suggestions.append({
            "priority": "high",
            "section": "frontmatter",
            "suggestion": "Add 'task: allow' to permissions for subagent delegation",
            "rationale": "Primary agents need task: allow for delegation per property-003",
        })

    if not agent.get("has_shared_context"):
        suggestions.append({
            "priority": "high",
            "section": "<shared-context>",
            "suggestion": "Add a <shared-context> section for cross-agent data flow",
            "rationale": "Agents must read shared context before starting work per property-005",
        })

    if not agent.get("has_task_tracking"):
        suggestions.append({
            "priority": "medium",
            "section": "<task-tracking>",
            "suggestion": "Add a <task-tracking> section for performance monitoring",
            "rationale": "Meta-agent needs performance data to optimize system",
        })

    return {
        "status": "ok",
        "agent": agent_name,
        "total_sections": {
            "present": len(suggestions),
            "missing": 9 - len(suggestions),
        },
        "suggestions": suggestions,
    }

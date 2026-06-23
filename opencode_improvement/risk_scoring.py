"""Eval result quality risk scorer.

Adapted from OpenMontage's slideshow_risk.py — scores eval result quality
across 6 dimensions that reliably predict whether the evaluation will
mislead improvement decisions.

Each dimension is scored 0-5 (lower is better):
  - hallucination_risk: Does the eval credit non-existent capabilities?
  - coverage_gap: Does the eval miss important test cases?
  - inconsistent_scoring: Do scores vary wildly across categories?
  - regression_blindness: Does the eval miss regressions?
  - benchmark_overfit: Does the eval only test what it's good at?
  - data_leakage_risk: Did the agent see the test data before?

Verdict:
  < 2.0: strong
  < 3.0: acceptable
  < 4.0: revise
  >= 4.0: fail — results should not be trusted for improvement decisions
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Risk Score Result
# ---------------------------------------------------------------------------

class RiskScoreResult:
    """Container for a scored eval risk assessment."""

    def __init__(
        self,
        average: float,
        verdict: str,
        dimensions: dict[str, dict[str, Any]],
        eval_config: dict[str, Any] | None = None,
    ):
        self.average = average
        self.verdict = verdict
        self.dimensions = dimensions
        self.eval_config = eval_config or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "average": self.average,
            "verdict": self.verdict,
            "dimensions": self.dimensions,
            "eval_config": self.eval_config,
        }


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_eval_risk(
    eval_result: dict[str, Any] | None = None,
    *,
    golden_results: list[dict[str, Any]] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score eval result quality across 6 risk dimensions.

    Args:
        eval_result: Full result dict from eval_agents().
        golden_results: List of per-test-case result dicts (alternative to
            passing full eval_result).
        config: Eval config dict for context (provider, judge_model, etc.).

    Returns:
        dict with 'average', 'verdict', 'dimensions', and 'eval_config'.
    """
    # Extract golden_results from eval_result if not provided directly
    results = golden_results or []
    if eval_result and not results:
        results = eval_result.get("golden_results", [])

    cfg = config or {}
    if eval_result and not cfg:
        cfg = eval_result.get("config", {})

    if not results:
        return RiskScoreResult(
            average=5.0,
            verdict="fail",
            dimensions={},
            eval_config=cfg,
        ).to_dict()

    dimensions = {
        "hallucination_risk": _score_hallucination_risk(results),
        "coverage_gap": _score_coverage_gap(results),
        "inconsistent_scoring": _score_inconsistent_scoring(results),
        "regression_blindness": _score_regression_blindness(results, cfg),
        "benchmark_overfit": _score_benchmark_overfit(results, cfg),
        "data_leakage_risk": _score_data_leakage_risk(results, cfg),
    }

    scores = [d["score"] for d in dimensions.values()]
    average = sum(scores) / len(scores)

    if average < 2.0:
        verdict = "strong"
    elif average < 3.0:
        verdict = "acceptable"
    elif average < 4.0:
        verdict = "revise"
    else:
        verdict = "fail"

    return RiskScoreResult(
        average=round(average, 2),
        verdict=verdict,
        dimensions=dimensions,
        eval_config=cfg,
    ).to_dict()


# ---------------------------------------------------------------------------
# Individual dimension scorers (each 0-5, lower is better)
# ---------------------------------------------------------------------------

def _score_hallucination_risk(results: list[dict]) -> dict[str, Any]:
    """Score risk that the eval credits non-existent capabilities.

    Signals:
    - Too many 1.0 scores across diverse categories suggests the eval is too
      lenient and may be hallucinating capability.
    - Mock provider results always passing is a risk factor.
    - If all cases pass, especially with suspiciously high scores.
    """
    if not results:
        return {"score": 5.0, "reason": "No results to evaluate"}

    passed = sum(1 for r in results if r.get("pass", False))
    pass_rate = passed / len(results) if results else 0.0

    providers = {r.get("provider", "real") for r in results}

    reasons = []
    score = 0.0

    # All-pass with mock provider is suspicious — the mock never fails
    if "mock" in providers and pass_rate == 1.0:
        score += 2.5
        reasons.append(
            "Mock provider returned 100% pass rate — does not validate "
            "actual agent capability"
        )

    # Very high pass rate without mock provider could still be too lenient
    if pass_rate >= 0.95 and "mock" not in providers:
        score += 1.0
        reasons.append(f"Pass rate of {pass_rate:.0%} may indicate overly lenient eval")

    # Check for suspicious score patterns (all scores are 0.0 or 1.0)
    scores_set = {r.get("score", 0.0) for r in results}
    if scores_set == {1.0}:
        score += 1.5
        reasons.append("Every test case scored exactly 1.0 — eval may be non-discriminating")

    # Average score unusually high across categories
    avg_score = sum(r.get("score", 0.0) for r in results) / len(results) if results else 0.0
    if avg_score >= 0.98 and "mock" not in providers:
        score += 1.0
        reasons.append(f"Average score {avg_score:.2f} is suspiciously high")

    return {
        "score": min(5.0, score),
        "reason": "; ".join(reasons) or "Hallucination risk appears low",
    }


def _score_coverage_gap(results: list[dict]) -> dict[str, Any]:
    """Score risk that the eval misses important test cases.

    Signals:
    - Few categories tested indicates coverage gaps.
    - No critical/warn severity cases suggests missing important tests.
    - Small total case count for the number of agents.
    """
    if not results:
        return {"score": 5.0, "reason": "No results to evaluate"}

    categories = {r.get("category", "unknown") for r in results}
    agents = {r.get("agent", "unknown") for r in results}
    severities = {r.get("severity", "info") for r in results}

    score = 0.0
    reasons = []

    # Category coverage
    if len(categories) < 2:
        score += 2.0
        reasons.append(f"Only {len(categories)} category tested (expect 5+)")
    elif len(categories) < 4:
        score += 1.0
        reasons.append(f"Only {len(categories)} categories tested (expect 5+)")

    # Severity coverage
    if "critical" not in severities:
        score += 1.5
        reasons.append("No critical-severity test cases — high-risk regressions may be missed")
    if "warn" not in severities:
        score += 0.5
        reasons.append("No warn-severity test cases")

    # Cases per agent
    cases_per_agent = len(results) / max(len(agents), 1)
    if cases_per_agent < 3 and len(agents) > 0:
        score += 1.5
        reasons.append(
            f"Only {cases_per_agent:.1f} test cases per agent — "
            f"insufficient coverage"
        )

    return {
        "score": min(5.0, score),
        "reason": "; ".join(reasons) or "Coverage appears adequate",
    }


def _score_inconsistent_scoring(results: list[dict]) -> dict[str, Any]:
    """Score risk of inconsistent scoring across categories.

    Signals:
    - Large variance in scores across categories.
    - Some categories at 100% and others at 0%.
    - High variance in pass rates between categories.
    """
    if not results:
        return {"score": 5.0, "reason": "No results to evaluate"}

    # Group by category
    from collections import defaultdict

    category_scores: dict[str, list[float]] = defaultdict(list)
    for r in results:
        cat = r.get("category", "unknown")
        category_scores[cat].append(r.get("score", 0.0))

    if len(category_scores) < 2:
        return {"score": 0.0, "reason": "Only one category — cannot assess inconsistency"}

    # Compute per-category average
    cat_avgs = {
        cat: sum(scores) / len(scores)
        for cat, scores in category_scores.items()
    }

    # Variance of category averages
    avg_values = list(cat_avgs.values())
    mean_avg = sum(avg_values) / len(avg_values)
    variance = sum((v - mean_avg) ** 2 for v in avg_values) / len(avg_values)
    std_dev = variance ** 0.5

    score = 0.0
    reasons = []

    if std_dev > 0.4:
        score += 2.5
        reasons.append(f"High score variance across categories (std={std_dev:.2f})")
        # Show which categories are outliers
        for cat, avg in sorted(cat_avgs.items()):
            if abs(avg - mean_avg) > std_dev * 1.5:
                reasons.append(f"  Category '{cat}' average {avg:.2f} deviates significantly")
    elif std_dev > 0.2:
        score += 1.0
        reasons.append(f"Moderate score variance across categories (std={std_dev:.2f})")

    return {
        "score": min(5.0, score),
        "reason": "; ".join(reasons) or f"Scores consistent across categories (std={std_dev:.2f})",
    }


def _score_regression_blindness(
    results: list[dict],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Score risk that the eval misses regressions.

    Signals:
    - No baseline comparison requested.
    - No regression detection mechanism.
    - --compare not used despite being available.
    """
    if not results:
        return {"score": 5.0, "reason": "No results to evaluate"}

    score = 0.0
    reasons = []

    compare = config.get("compare", False)
    fail_under = config.get("fail_under")

    if not compare and fail_under is None:
        score += 3.0
        reasons.append(
            "No baseline comparison (--compare) and no fail-under threshold "
            "(--fail-under) — regressions will go undetected"
        )
    elif not compare:
        score += 1.5
        reasons.append(
            "No baseline comparison (--compare) — cannot detect pass rate "
            "degradation over time"
        )

    # Check if regression data is present in results
    # (This function receives raw results, not the full eval_result dict,
    # so we check what we can from config)

    # Mock provider with no regression detection is risky
    if config.get("provider") == "mock" and not compare:
        score += 1.0
        reasons.append("Mock provider used without baseline — cannot detect regressions")

    return {
        "score": min(5.0, score),
        "reason": "; ".join(reasons) or "Regression detection appears adequate",
    }


def _score_benchmark_overfit(
    results: list[dict],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Score risk that the eval only tests what it's good at.

    Signals:
    - Tests skewed toward one category.
    - Only using keyword-match eval (no LLM judge).
    - Agent evaluated on too few test case types.
    """
    if not results:
        return {"score": 5.0, "reason": "No results to evaluate"}

    from collections import Counter

    score = 0.0
    reasons = []

    # Category skew
    categories = Counter(r.get("category", "unknown") for r in results)
    if categories:
        most_common_cat, most_common_count = categories.most_common(1)[0]
        cat_ratio = most_common_count / len(results)
        if cat_ratio > 0.7:
            score += 2.0
            reasons.append(
                f"Category '{most_common_cat}' dominates at {cat_ratio:.0%} of test cases — "
                f"eval may overfit to one area"
            )
        elif cat_ratio > 0.5:
            score += 1.0
            reasons.append(f"Category '{most_common_cat}' is {cat_ratio:.0%} of test cases")

    # LLM judge absence
    judge_model = config.get("judge_model")
    if not judge_model and config.get("provider") != "mock":
        score += 1.5
        reasons.append(
            "No LLM-as-judge (--judge-model) — eval uses only keyword matching, "
            "which may overfit to surface patterns"
        )

    # Provider = mock means no real eval at all
    if config.get("provider") == "mock":
        score += 1.0
        reasons.append("Mock provider does not exercise real agent capabilities")

    return {
        "score": min(5.0, score),
        "reason": "; ".join(reasons) or "No significant overfit signals detected",
    }


def _score_data_leakage_risk(
    results: list[dict],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Score risk that the agent saw the test data before.

    Signals:
    - Agent evaluated using only keyword matching against its own config file.
      If the config contains keywords from golden test cases, the eval is
      measuring memorization, not capability.
    - High pass rate combined with keyword-only eval is suspicious.
    """
    if not results:
        return {"score": 5.0, "reason": "No results to evaluate"}

    score = 0.0
    reasons = []

    # If provider is "real" and only keyword matching is used,
    # check for possible data leakage through config files
    provider = config.get("provider", "real")
    use_judge = bool(config.get("judge_model"))

    if provider == "mock":
        score += 2.0
        reasons.append(
            "Mock provider loads golden data directly — results show "
            "perfect pass rate regardless of actual agent capability"
        )

    if not use_judge and provider != "mock":
        # Keyword matching against agent configs can measure config quality,
        # not actual agent behavior
        passed = sum(1 for r in results if r.get("pass", False))
        pass_rate = passed / len(results) if results else 0.0
        if pass_rate > 0.9:
            score += 2.5
            reasons.append(
                f"Keyword-match eval with {pass_rate:.0%} pass rate — "
                f"may measure config memorization rather than agent capability"
            )
        elif pass_rate > 0.7:
            score += 1.0
            reasons.append(
                f"Keyword-match eval with {pass_rate:.0%} pass rate — "
                f"consider LLM judge for semantic evaluation"
            )

    return {
        "score": min(5.0, score),
        "reason": "; ".join(reasons) or "Data leakage risk appears low",
    }

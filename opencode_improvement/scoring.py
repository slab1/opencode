"""Strategy effectiveness scoring engine.

Adapted from OpenMontage's scoring.py — replaces naive "first available strategy"
selection with weighted multi-dimensional scoring. Every strategy choice should
be explainable, not just "it was available."

Scores are normalized 0-1. Higher is better.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
import re
from typing import Any


# ---------------------------------------------------------------------------
# Strategy Score — adapted from OpenMontage's ProviderScore
# ---------------------------------------------------------------------------

@dataclass
class StrategyScore:
    """Scored evaluation of an improvement strategy for a specific agent.

    Adapted from OpenMontage's 7-dimension provider scoring model.
    These dimensions measure strategy effectiveness in the agent eval context:

    - task_fit: How well the strategy matches the agent's diagnosed gaps.
    - output_quality: Expected improvement in eval scores from applying this.
    - control: Determinism — how predictable the outcome is.
    - reliability: Historical pass rate of this strategy across agents.
    - cost_efficiency: Token/time investment vs expected return.
    - speed: How quickly the strategy produces measurable improvement.
    - continuity: Compatibility with already-applied strategies.
    """

    strategy_name: str
    agent_target: str
    task_fit: float = 0.0       # 0-1: best fit for this agent's gaps
    output_quality: float = 0.0  # 0-1: expected score improvement
    control: float = 0.0        # 0-1: determinism / predictability
    reliability: float = 0.0    # 0-1: historical pass rate
    cost_efficiency: float = 0.0  # 0-1: improvement per token
    speed: float = 0.0          # 0-1: time to measurable result
    continuity: float = 0.0     # 0-1: compatibility with prior strategies

    @property
    def weighted_score(self) -> float:
        """Compute weighted composite score.

        Weights are tuned for the agent improvement domain:
        - task_fit and output_quality get the most weight because alignment
          and result quality are paramount.
        - reliability and control get medium weight — we need confidence.
        - cost_efficiency, speed, continuity are secondary factors.
        """
        return (
            self.task_fit * 0.30
            + self.output_quality * 0.20
            + self.control * 0.15
            + self.reliability * 0.15
            + self.cost_efficiency * 0.10
            + self.speed * 0.05
            + self.continuity * 0.05
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["weighted_score"] = self.weighted_score
        return d

    def explain(self) -> str:
        """Human-readable explanation of this score."""
        parts = [
            f"Strategy '{self.strategy_name}' for {self.agent_target}: "
            f"{self.weighted_score:.2f}"
        ]
        top = sorted(
            [
                ("task_fit", self.task_fit, 0.30),
                ("output_quality", self.output_quality, 0.20),
                ("control", self.control, 0.15),
                ("reliability", self.reliability, 0.15),
                ("cost_efficiency", self.cost_efficiency, 0.10),
                ("speed", self.speed, 0.05),
                ("continuity", self.continuity, 0.05),
            ],
            key=lambda x: x[1] * x[2],
            reverse=True,
        )
        for name, val, weight in top[:3]:
            parts.append(f"  {name}={val:.2f} (w={weight})")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Strategy Effectiveness Score — adapted from OpenMontage's ProductionPathScore
# ---------------------------------------------------------------------------

@dataclass
class StrategyEffectiveness:
    """Aggregated effectiveness of a strategy across multiple applications."""

    strategy_name: str
    applicability: float = 0.0     # 0-1: how broadly this strategy applies
    improvement_magnitude: float = 0.0  # 0-1: avg score delta when applied
    success_rate: float = 0.0      # 0-1: fraction of successful applications
    synergy_with_others: float = 0.0  # 0-1: works well with other strategies
    token_efficiency: float = 0.0  # 0-1: improvement per token consumed
    iteration_speed: float = 0.0   # 0-1: eval cycles to see improvement
    risk_profile: float = 0.0      # 0-1: inverse of risk (low risk = high score)

    @property
    def weighted_score(self) -> float:
        return (
            self.applicability * 0.25
            + self.improvement_magnitude * 0.20
            + self.success_rate * 0.15
            + self.synergy_with_others * 0.10
            + self.token_efficiency * 0.10
            + self.iteration_speed * 0.10
            + self.risk_profile * 0.10
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["weighted_score"] = self.weighted_score
        return d


# ---------------------------------------------------------------------------
# Scoring Functions — adapted from OpenMontage
# ---------------------------------------------------------------------------

def _keyword_overlap(set_a: set[str], set_b: set[str]) -> float:
    """Overlap coefficient between two keyword sets.

    Uses |A ∩ B| / min(|A|, |B|) rather than Jaccard. Jaccard over-penalizes
    strategies whose 'best_for' describes many strengths. Overlap coefficient
    answers the question: 'is the intent a subset of what this strategy
    advertises?' which is what we actually care about for strategy matching.
    """
    if not set_a or not set_b:
        return 0.0
    a = {s.lower().strip() for s in set_a}
    b = {s.lower().strip() for s in set_b}
    intersection = len(a & b)
    smaller = min(len(a), len(b))
    return intersection / smaller if smaller > 0 else 0.0


# Semantic synonym clusters for agent improvement domain:
# When a gap description says "hallucination" and a strategy says "factuality"
# or "grounding", that's a match even without literal keyword overlap.
_STRATEGY_SYNONYM_CLUSTERS: list[set[str]] = [
    {"hallucination", "factuality", "grounding", "faithfulness", "truthfulness"},
    {"coverage", "completeness", "scope", "comprehensiveness", "exhaustiveness"},
    {"determinism", "predictability", "consistency", "reproducibility", "stability"},
    {"token", "cost", "efficiency", "waste", "spend", "budget", "optimization"},
    {"latency", "speed", "performance", "throughput", "responsiveness", "wait"},
    {"regression", "breakage", "backslide", "degradation", "invariant"},
    {"overfit", "dataset-bias", "benchmark-bias", "data-leakage", "cheating"},
    {"structure", "schema", "frontmatter", "capabilities", "rules", "template"},
    {"testing", "validation", "verification", "assertion", "check", "eval"},
    {"prompt", "instruction", "system-prompt", "guidance", "directive"},
]

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+._-]*")


def _tokenize_text(value: str) -> list[str]:
    return _TOKEN_RE.findall((value or "").lower())


def _expand_synonyms(words: set[str]) -> set[str]:
    """Expand a word set with synonyms from known clusters."""
    expanded = set(words)
    for cluster in _STRATEGY_SYNONYM_CLUSTERS:
        if expanded & cluster:
            expanded |= cluster
    return expanded


def _compute_task_fit(
    best_for: set[str],
    gap_description: str,
    agent_keywords: set[str],
) -> float:
    """Score how well a strategy's 'best_for' matches the agent's gap.

    Uses synonym expansion so semantic near-misses (e.g. "hallucination"
    vs "factuality") still score well.
    """
    if not best_for:
        return 0.3  # Unknown capability — modest default

    intent_words = _expand_synonyms(set(_tokenize_text(gap_description)))
    best_for_words: set[str] = set()
    for desc in best_for:
        best_for_words.update(_tokenize_text(desc))
    best_for_words = _expand_synonyms(best_for_words)

    intent_score = _keyword_overlap(intent_words, best_for_words)

    agent_expanded = _expand_synonyms({kw.lower() for kw in agent_keywords})
    agent_score = _keyword_overlap(agent_expanded, best_for_words)

    return min(1.0, intent_score * 0.7 + agent_score * 0.3 + 0.1)


def _compute_control(strategy_config: dict[str, Any]) -> float:
    """Score controllability from the strategy config.

    Features are weighted by impact: strategies with explicit confidence
    thresholds and rollback plans score higher for control.
    """
    control_features = [
        ("confidence_threshold", 2.0),
        ("rollback_plan", 1.8),
        ("tests_before_apply", 1.5),
        ("dry_run_support", 1.3),
        ("output_validation", 1.2),
        ("parameterized_prompts", 1.0),
        ("configurable_target", 0.8),
    ]
    if not strategy_config:
        return 0.3
    total_weight = sum(w for _, w in control_features)
    earned = sum(w for f, w in control_features if strategy_config.get(f))
    return min(1.0, earned / (total_weight * 0.5))


def _compute_cost_efficiency(
    estimated_tokens: float,
    token_budget_remaining: float | None,
) -> float:
    """Score cost efficiency. Low-token is 1.0, over-budget is 0.0."""
    if estimated_tokens <= 0:
        return 1.0
    if token_budget_remaining is not None and token_budget_remaining <= 0:
        return 0.0
    if token_budget_remaining is not None:
        ratio = estimated_tokens / token_budget_remaining
        if ratio > 0.5:
            return 0.1
        if ratio > 0.2:
            return 0.5
        return 0.8
    # No budget info — use absolute token heuristic
    if estimated_tokens < 1000:
        return 0.9
    if estimated_tokens < 5000:
        return 0.7
    if estimated_tokens < 25000:
        return 0.5
    return 0.3


def _compute_continuity(
    strategy_name: str,
    applied_strategies: set[str],
) -> float:
    """Score how well this strategy fits already-applied strategies."""
    if not applied_strategies:
        return 0.5  # No prior context
    if strategy_name in applied_strategies:
        return 0.9  # Same strategy = likely compatible
    return 0.4  # Different strategy = possible conflict


def score_strategy(
    strategy_name: str,
    agent_target: str,
    *,
    best_for: set[str] | None = None,
    gap_description: str = "",
    agent_keywords: set[str] | None = None,
    strategy_config: dict[str, Any] | None = None,
    applied_strategies: set[str] | None = None,
    historical_success_rate: float | None = None,
    estimated_tokens: float | None = None,
    token_budget_remaining: float | None = None,
    stability: str = "experimental",
) -> StrategyScore:
    """Score a strategy against an agent's diagnosed gaps.

    Args:
        strategy_name: Name of the improvement strategy.
        agent_target: Target agent being improved.
        best_for: Set of descriptions of what this strategy is good for.
        gap_description: Description of the agent's diagnosed gap.
        agent_keywords: Keywords describing the agent's capabilities.
        strategy_config: Dict with keys like 'confidence_threshold',
            'rollback_plan', 'dry_run_support', etc.
        applied_strategies: Set of strategy names already applied to this agent.
        historical_success_rate: Measured 0.0-1.0 success rate from strategy_log.
        estimated_tokens: Expected token cost for this strategy.
        token_budget_remaining: Remaining token budget.
        stability: 'production', 'beta', or 'experimental'.

    Returns:
        A StrategyScore with all dimensions populated.
    """
    best_for = best_for or set()
    agent_keywords = agent_keywords or set()
    strategy_config = strategy_config or {}
    applied_strategies = applied_strategies or set()

    # Task fit
    task_fit = _compute_task_fit(best_for, gap_description, agent_keywords)

    # Reliability: use historical success rate if available
    if historical_success_rate is not None:
        reliability = float(historical_success_rate)
    elif stability == "production":
        reliability = 0.85
    elif stability == "beta":
        reliability = 0.65
    else:
        reliability = 0.40

    # Control: from strategy config
    control = _compute_control(strategy_config)

    # Cost efficiency
    if estimated_tokens is not None:
        cost_efficiency = _compute_cost_efficiency(estimated_tokens, token_budget_remaining)
    else:
        cost_efficiency = 0.5

    # Output quality: based on stability + tier
    quality_map = {"production": 0.85, "beta": 0.65, "experimental": 0.40}
    output_quality = quality_map.get(stability, 0.5)

    # Speed: based on how many eval cycles a strategy typically needs
    speed_map = {
        "production": 0.8,   # Well-understood, fast to apply
        "beta": 0.6,
        "experimental": 0.4,  # May need iterations
    }
    speed = speed_map.get(stability, 0.5)

    # Continuity
    continuity = _compute_continuity(strategy_name, applied_strategies)

    return StrategyScore(
        strategy_name=strategy_name,
        agent_target=agent_target,
        task_fit=min(1.0, task_fit),
        output_quality=output_quality,
        control=control,
        reliability=reliability,
        cost_efficiency=cost_efficiency,
        speed=speed,
        continuity=continuity,
    )


def rank_strategies(
    strategy_scores: list[StrategyScore],
) -> list[StrategyScore]:
    """Rank strategy scores by weighted score descending."""
    return sorted(strategy_scores, key=lambda s: s.weighted_score, reverse=True)


def format_ranking(rankings: list[StrategyScore], top_n: int = 5) -> str:
    """Format a ranking list for user presentation."""
    lines = []
    for i, r in enumerate(rankings[:top_n], 1):
        lines.append(
            f"  {i}. {r.strategy_name} (for {r.agent_target}) — "
            f"score: {r.weighted_score:.2f} "
            f"[fit={r.task_fit:.1f} quality={r.output_quality:.1f} "
            f"control={r.control:.1f} reliable={r.reliability:.1f} "
            f"cost={r.cost_efficiency:.1f}]"
        )
    return "\n".join(lines)

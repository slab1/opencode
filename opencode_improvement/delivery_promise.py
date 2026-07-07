"""Eval result quality promise classifier.

Adapted from OpenMontage's delivery_promise.py — before running an eval,
the system classifies what quality tier it's promising to deliver. This
prevents the most damaging failure mode: silently certifying a regression
as acceptable because the eval wasn't thorough enough.

The delivery promise is set before eval execution and locked. If the
actual results don't satisfy the promise, the system must flag it —
not silently accept lower quality.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class PromiseType(Enum):
    """Eval promise tiers, ordered by rigor.

    Each tier makes a different quality commitment:
    - FULL_COVERAGE: Every test case must pass — no exceptions.
    - CRITICAL_ONLY: Only critical/warn severity cases must pass.
    - SMOKE_TEST: Quick health check — a few representative cases.
    - REGRESSION_CHECK: Must at least match the last known baseline.
    """
    FULL_COVERAGE = "full_coverage"
    CRITICAL_ONLY = "critical_only"
    SMOKE_TEST = "smoke_test"
    REGRESSION_CHECK = "regression_check"


# Rules per promise type — what is and isn't acceptable for eval results
PROMISE_RULES: dict[str, dict[str, Any]] = {
    "full_coverage": {
        "min_pass_rate": 1.0,
        "all_severities_required": True,
        "all_agents_required": True,
        "all_categories_required": True,
        "fails_on_any_failure": True,
        "description": (
            "Every golden test case across every agent must pass. "
            "Zero tolerance for regressions."
        ),
    },
    "critical_only": {
        "min_pass_rate": 1.0,
        "all_severities_required": False,
        "all_agents_required": True,
        "all_categories_required": False,
        "fails_on_any_failure": False,
        "description": (
            "Only critical and warn severity test cases must pass. "
            "Info-level failures are acceptable."
        ),
    },
    "smoke_test": {
        "min_pass_rate": 0.8,
        "all_severities_required": False,
        "all_agents_required": False,
        "all_categories_required": False,
        "fails_on_any_failure": False,
        "description": (
            "Quick health check — at least 80% of tested cases pass. "
            "Not all agents or categories are covered."
        ),
    },
    "regression_check": {
        "min_pass_rate": None,  # Dynamic: must match or beat baseline
        "all_severities_required": False,
        "all_agents_required": True,
        "all_categories_required": True,
        "fails_on_any_failure": False,
        "description": (
            "Must at least match the stored baseline pass rate. "
            "Designed for CI regression detection."
        ),
    },
}

# Severity ranking: critical is the highest priority
_SEVERITY_ORDER: dict[str, int] = {
    "critical": 3,
    "warn": 2,
    "info": 1,
}


@dataclass
class DeliveryPromise:
    """Classifies what quality tier the eval promises to deliver.

    The promise is set before eval execution. If the results don't satisfy
    it, the system must stop and ask — not silently accept lower quality.
    """

    promise_type: PromiseType
    min_pass_rate: float | None   # None = dynamic (from baseline)
    all_severities_required: bool
    all_agents_required: bool
    all_categories_required: bool
    fails_on_any_failure: bool
    baseline_pass_rate: float | None = None  # For REGRESSION_CHECK

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["promise_type"] = self.promise_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliveryPromise":
        return cls(
            promise_type=PromiseType(data["promise_type"]),
            min_pass_rate=data.get("min_pass_rate"),
            all_severities_required=data.get("all_severities_required", False),
            all_agents_required=data.get("all_agents_required", False),
            all_categories_required=data.get("all_categories_required", False),
            fails_on_any_failure=data.get("fails_on_any_failure", False),
            baseline_pass_rate=data.get("baseline_pass_rate"),
        )

    def get_rules(self) -> dict[str, Any]:
        """Get the enforcement rules for this promise type."""
        return PROMISE_RULES.get(self.promise_type.value, {})

    def validate_eval_cases(
        self,
        eval_results: list[dict[str, Any]],
        *,
        baseline_pass_rate: float | None = None,
        tested_agents: set[str] | None = None,
        expected_agents: set[str] | None = None,
    ) -> dict[str, Any]:
        """Validate eval results against this delivery promise.

        Args:
            eval_results: List of per-test-case result dicts from eval_agents().
            baseline_pass_rate: Baseline pass rate for REGRESSION_CHECK.
            tested_agents: Actual agents tested in this eval run.
            expected_agents: Agents that were supposed to be tested.

        Returns:
            dict with 'valid' (bool), 'violations' (list[str]),
            and 'metrics' (dict).
        """
        rules = self.get_rules()
        violations = []

        if not eval_results:
            return {
                "valid": False,
                "violations": ["No eval results provided"],
                "metrics": {"pass_rate": 0.0, "total": 0, "passed": 0},
            }

        total = len(eval_results)
        passed = sum(1 for r in eval_results if r.get("pass", False))
        pass_rate = passed / total if total > 0 else 0.0

        metrics = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(pass_rate, 3),
        }

        # Check agent coverage
        if self.all_agents_required and expected_agents and tested_agents:
            missing_agents = expected_agents - tested_agents
            if missing_agents:
                violations.append(
                    f"Missing agents not tested: {', '.join(sorted(missing_agents))}. "
                    f"Promise type {self.promise_type.value} requires all agents."
                )

        # Check category coverage
        if self.all_categories_required:
            categories_tested = {r.get("category", "unknown") for r in eval_results}
            # Deduce expected categories from the results themselves
            if len(categories_tested) < 3:
                violations.append(
                    f"Only {len(categories_tested)} categories tested. "
                    f"Promise type {self.promise_type.value} expects broad coverage."
                )

        # Check minimum pass rate
        effective_min = self.min_pass_rate
        if effective_min is None:
            # REGRESSION_CHECK: use baseline
            bp = baseline_pass_rate or self.baseline_pass_rate
            if bp is not None:
                effective_min = bp
            else:
                effective_min = 0.0  # No baseline — can't check regression

        if pass_rate < effective_min:
            if self.promise_type == PromiseType.REGRESSION_CHECK:
                violations.append(
                    f"Pass rate {pass_rate:.1%} is below baseline "
                    f"{effective_min:.1%}. Regression detected."
                )
            else:
                violations.append(
                    f"Pass rate {pass_rate:.1%} is below minimum "
                    f"{effective_min:.1%} required for "
                    f"{self.promise_type.value}."
                )

        # Check severity coverage for CRITICAL_ONLY
        if self.promise_type == PromiseType.CRITICAL_ONLY:
            critical_failures = [
                r for r in eval_results
                if not r.get("pass", False)
                and r.get("severity", "info") in ("critical", "warn")
            ]
            if critical_failures:
                violations.append(
                    f"{len(critical_failures)} critical/warn test cases failed "
                    f"but {self.promise_type.value} requires all critical cases to pass."
                )

        # Check all-severities-required for FULL_COVERAGE
        if self.all_severities_required:
            any_failure = [r for r in eval_results if not r.get("pass", False)]
            if any_failure:
                violations.append(
                    f"{len(any_failure)} test cases failed but "
                    f"{self.promise_type.value} requires all severities to pass."
                )

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "metrics": metrics,
        }


def classify_from_config(
    *,
    fail_under: float | None = None,
    compare: bool = False,
    severity: str = "warn",
    all_agents: bool = True,
) -> DeliveryPromise:
    """Classify delivery promise from eval CLI config.

    This provides a sensible default based on the eval flags the user chose.
    Matches the CLI flags from __main__.py.

    Args:
        fail_under: Minimum pass rate threshold (--fail-under).
        compare: Whether baseline comparison was requested (--compare).
        severity: Minimum severity level.
        all_agents: Whether all agents are being tested.

    Returns:
        A DeliveryPromise appropriate for the config.
    """
    rules = PROMISE_RULES

    if fail_under is not None and fail_under >= 0.99:
        # User set a very high bar
        return DeliveryPromise(
            promise_type=PromiseType.FULL_COVERAGE,
            min_pass_rate=fail_under,
            all_severities_required=True,
            all_agents_required=True,
            all_categories_required=True,
            fails_on_any_failure=True,
        )

    if compare:
        # Regression check against baseline
        return DeliveryPromise(
            promise_type=PromiseType.REGRESSION_CHECK,
            min_pass_rate=None,  # Dynamic from baseline
            all_severities_required=False,
            all_agents_required=True,
            all_categories_required=True,
            fails_on_any_failure=False,
        )

    if severity == "critical":
        # Only critical failures matter
        return DeliveryPromise(
            promise_type=PromiseType.CRITICAL_ONLY,
            min_pass_rate=1.0,
            all_severities_required=False,
            all_agents_required=True,
            all_categories_required=False,
            fails_on_any_failure=False,
        )

    # Default: moderate bar
    return DeliveryPromise(
        promise_type=PromiseType.SMOKE_TEST,
        min_pass_rate=rules["smoke_test"]["min_pass_rate"],
        all_severities_required=False,
        all_agents_required=all_agents,
        all_categories_required=False,
        fails_on_any_failure=False,
    )

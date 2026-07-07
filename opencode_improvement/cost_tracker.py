"""Eval cost tracker: estimate, reserve, reconcile, and persist.

Adapted from OpenMontage's cost_tracker.py — implements budget governance
for eval execution costs measured in tokens and time, not USD.

Lifecycle:
  estimate() → reserve() → reconcile() / refund()
  estimate() → reserve() → reconcile() / refund()

Each eval run produces a preflight estimate, the system reserves budget
before execution, and actual spend is reconciled when the run finishes
or fails.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class EntryStatus(str, Enum):
    ESTIMATED = "estimated"
    RESERVED = "reserved"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class BudgetMode(str, Enum):
    WARN = "warn"        # Log warnings on overruns, don't block
    CAP = "cap"          # Hard block when budget exceeded
    OBSERVE = "observe"  # Track only, no warnings or blocks


class BudgetExceededError(Exception):
    """Raised when an eval run would exceed the budget in cap mode."""
    pass


class ApprovalRequiredError(Exception):
    """Raised when an eval run needs explicit approval before proceeding."""
    pass


class CostTracker:
    """Tracks estimated, reserved, and actual token/time costs for eval runs.

    Budget governance for agent evaluation:
    - Tokens: API consumption for LLM-based eval judges.
    - Time: Execution duration for eval runs.
    - Both use the same estimate → reserve → reconcile lifecycle.
    """

    def __init__(
        self,
        token_budget: int = 100_000,
        time_budget_seconds: int = 3600,
        reserve_pct: float = 0.10,
        single_run_approval_tokens: int = 25_000,
        require_approval_for_new_agent: bool = True,
        mode: BudgetMode = BudgetMode.WARN,
        cost_log_path: Optional[Path] = None,
    ) -> None:
        self.token_budget = token_budget
        self.time_budget_seconds = time_budget_seconds
        self.reserve_pct = reserve_pct
        self.single_run_approval_tokens = single_run_approval_tokens
        self.require_approval_for_new_agent = require_approval_for_new_agent
        self.mode = mode
        self.cost_log_path = cost_log_path
        self.entries: list[dict[str, Any]] = []
        self._approved_agents: set[str] = set()

        if cost_log_path and cost_log_path.exists():
            self._load()

    # ---- Budget calculations ----

    @property
    def budget_reserved_tokens(self) -> int:
        return sum(
            e.get("reserved_tokens", 0)
            for e in self.entries
            if e["status"] == EntryStatus.RESERVED.value
        )

    @property
    def budget_spent_tokens(self) -> int:
        return sum(
            e.get("actual_tokens", 0)
            for e in self.entries
            if e["status"] in (EntryStatus.COMPLETED.value, EntryStatus.FAILED.value)
        )

    @property
    def budget_remaining_tokens(self) -> int:
        return self.token_budget - self.budget_spent_tokens - self.budget_reserved_tokens

    @property
    def budget_remaining_seconds(self) -> int:
        """Remaining time budget, accounting for spent and reserved time."""
        spent = sum(
            e.get("actual_seconds", 0)
            for e in self.entries
            if e["status"] in (EntryStatus.COMPLETED.value, EntryStatus.FAILED.value)
        )
        reserved = sum(
            e.get("reserved_seconds", 0)
            for e in self.entries
            if e["status"] == EntryStatus.RESERVED.value
        )
        return max(0, self.time_budget_seconds - spent - reserved)

    @property
    def usable_budget_tokens(self) -> int:
        """Token budget minus the reserve holdback."""
        holdback = int(self.token_budget * self.reserve_pct)
        return max(0, self.budget_remaining_tokens - holdback)

    def cost_snapshot(self) -> dict[str, float | int]:
        return {
            "total_spent_tokens": self.budget_spent_tokens,
            "total_reserved_tokens": self.budget_reserved_tokens,
            "budget_remaining_tokens": self.budget_remaining_tokens,
            "budget_remaining_seconds": self.budget_remaining_seconds,
        }

    # ---- Core operations ----

    def estimate(
        self,
        agent: str,
        operation: str,
        estimated_tokens: int,
        estimated_seconds: int = 0,
    ) -> str:
        """Record an estimate for an eval run. Returns entry ID."""
        entry_id = self._new_id()
        self.entries.append({
            "id": entry_id,
            "agent": agent,
            "operation": operation,
            "status": EntryStatus.ESTIMATED.value,
            "estimated_tokens": estimated_tokens,
            "estimated_seconds": estimated_seconds,
            "reserved_tokens": 0,
            "reserved_seconds": 0,
            "actual_tokens": 0,
            "actual_seconds": 0,
            "timestamp": self._now(),
        })
        self._save()
        return entry_id

    def reserve(self, entry_id: str) -> None:
        """Reserve budget for an estimated eval run.

        Raises BudgetExceededError in CAP mode, or ApprovalRequiredError
        when the run exceeds the single-run approval threshold.
        """
        entry = self._find(entry_id)
        estimated_tokens = entry["estimated_tokens"]

        # Check single-run approval threshold
        if estimated_tokens > self.single_run_approval_tokens:
            if self.mode != BudgetMode.OBSERVE:
                raise ApprovalRequiredError(
                    f"Eval run for {entry['agent']} costs {estimated_tokens} tokens, "
                    f"exceeds single-run threshold "
                    f"{self.single_run_approval_tokens}"
                )

        # Check new agent approval
        if self.require_approval_for_new_agent and estimated_tokens > 0:
            if entry["agent"] not in self._approved_agents:
                if self.mode != BudgetMode.OBSERVE:
                    raise ApprovalRequiredError(
                        f"First eval of agent {entry['agent']!r} requires approval"
                    )

        # Check token budget
        if estimated_tokens > self.usable_budget_tokens:
            if self.mode == BudgetMode.CAP:
                raise BudgetExceededError(
                    f"Reservation of {estimated_tokens} tokens exceeds usable "
                    f"budget of {self.usable_budget_tokens} tokens"
                )

        # Check time budget
        estimated_seconds = entry.get("estimated_seconds", 0)
        if estimated_seconds > self.budget_remaining_seconds:
            if self.mode == BudgetMode.CAP:
                raise BudgetExceededError(
                    f"Reservation of {estimated_seconds}s exceeds remaining "
                    f"time budget of {self.budget_remaining_seconds}s"
                )

        entry["status"] = EntryStatus.RESERVED.value
        entry["reserved_tokens"] = estimated_tokens
        entry["reserved_seconds"] = estimated_seconds
        entry["timestamp"] = self._now()
        self._save()

    def approve_agent(self, agent: str) -> None:
        """Mark an agent as approved for eval runs."""
        self._approved_agents.add(agent)
        self._save_approvals()

    def reconcile(
        self,
        entry_id: str,
        actual_tokens: int,
        actual_seconds: int = 0,
        success: bool = True,
    ) -> None:
        """Reconcile actual resource usage after eval completes."""
        entry = self._find(entry_id)
        entry["status"] = EntryStatus.COMPLETED.value if success else EntryStatus.FAILED.value
        entry["actual_tokens"] = actual_tokens
        entry["actual_seconds"] = actual_seconds
        entry["reserved_tokens"] = 0
        entry["reserved_seconds"] = 0
        entry["timestamp"] = self._now()
        self._save()

    def refund(self, entry_id: str) -> None:
        """Cancel a reservation without executing."""
        entry = self._find(entry_id)
        entry["status"] = EntryStatus.REFUNDED.value
        entry["reserved_tokens"] = 0
        entry["reserved_seconds"] = 0
        entry["timestamp"] = self._now()
        self._save()

    # ---- Reference-based estimation for eval runs ----

    def estimate_eval_run(
        self,
        agent: str,
        num_test_cases: int,
        *,
        use_llm_judge: bool = False,
        average_case_tokens: int = 500,
        average_judge_tokens: int = 2000,
        average_seconds_per_case: int = 2,
        overhead_seconds: int = 10,
    ) -> dict[str, Any]:
        """Estimate token and time cost for an eval run.

        Args:
            agent: Agent being evaluated.
            num_test_cases: Number of golden test cases to run.
            use_llm_judge: Whether LLM-as-judge scoring is enabled.
            average_case_tokens: Avg tokens per keyword-match test case.
            average_judge_tokens: Avg tokens per LLM judge evaluation.
            average_seconds_per_case: Avg seconds per test case.
            overhead_seconds: Fixed overhead for startup/teardown.

        Returns:
            dict with estimated_tokens, estimated_seconds, line_items.
        """
        # Base eval: keyword matching for each test case
        base_tokens = num_test_cases * average_case_tokens
        line_items = [{
            "category": "keyword_eval",
            "cases": num_test_cases,
            "tokens_per_case": average_case_tokens,
            "total_tokens": base_tokens,
        }]

        # LLM judge addon
        judge_tokens = 0
        if use_llm_judge:
            judge_tokens = num_test_cases * average_judge_tokens
            line_items.append({
                "category": "llm_judge",
                "cases": num_test_cases,
                "tokens_per_case": average_judge_tokens,
                "total_tokens": judge_tokens,
            })

        total_tokens = base_tokens + judge_tokens
        total_seconds = (num_test_cases * average_seconds_per_case) + overhead_seconds

        # Confidence: depends on how much data we have
        if num_test_cases >= 50:
            confidence = "high"
        elif num_test_cases >= 20:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "agent": agent,
            "num_test_cases": num_test_cases,
            "use_llm_judge": use_llm_judge,
            "total_tokens": total_tokens,
            "total_seconds": total_seconds,
            "line_items": line_items,
            "confidence": confidence,
        }

    # ---- Persistence ----

    def _save(self) -> None:
        if self.cost_log_path is None:
            return
        data = {
            "version": "1.0",
            "token_budget": self.token_budget,
            "time_budget_seconds": self.time_budget_seconds,
            "budget_reserved_tokens": self.budget_reserved_tokens,
            "budget_spent_tokens": self.budget_spent_tokens,
            "entries": self.entries,
        }
        self.cost_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cost_log_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        with open(self.cost_log_path) as f:
            data = json.load(f)
        self.entries = data.get("entries", [])
        self.token_budget = data.get("token_budget", self.token_budget)
        self.time_budget_seconds = data.get("time_budget_seconds", self.time_budget_seconds)

    def _save_approvals(self) -> None:
        """Persist approved agent list alongside the cost log."""
        if self.cost_log_path is None:
            return
        approvals_path = self.cost_log_path.with_suffix(".approvals.json")
        with open(approvals_path, "w") as f:
            json.dump({"approved_agents": sorted(self._approved_agents)}, f, indent=2)

    # ---- Helpers ----

    def _find(self, entry_id: str) -> dict[str, Any]:
        for entry in self.entries:
            if entry["id"] == entry_id:
                return entry
        raise KeyError(f"Cost entry {entry_id!r} not found")

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

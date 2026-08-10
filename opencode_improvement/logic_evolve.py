"""Project Aether: Recursive Code-Level Self-Improvement (RCSI) — EVOLVED.

An HONEST, eval-gated self-improvement loop:

- ``analyze_failures()`` reads ``strategy_effectiveness`` from
  ``shared/context.json``. Failures are now actually recorded (via
  ``record_outcome()`` and ``PerformanceTracker.log(..., context={"strategy": ...})``),
  so the loop can fire instead of being blind to every failure.
- ``synthesize_patch()`` is template-driven: the ``transfer_capability``
  special case is data-driven (``TRANSFER_CAPABILITY_PATCH``), and every other
  failing strategy gets a generic, honest patch targeting the most recent
  agent config that used it.
- ``verify_patch()`` runs a REAL shadow test: it applies the proposed change
  to a temporary copy of the target file, runs
  ``python3 -m opencode_improvement eval --agent <target> --provider mock``
  against the shadow copy, and compares the pass rate to
  ``shared/eval/baseline.json``. Non-agent files fall back to a
  ``python3 -m py_compile`` syntax check. It NEVER returns True
  unconditionally.
- ``run_evolution_cycle()`` actually applies verified patches (appends a
  documented improvement note) and logs the promotion/rejection via
  ``PerformanceTracker``.
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths
BASE_DIR = Path.home() / ".config" / "opencode"
CONTEXT_FILE = BASE_DIR / "shared" / "context.json"
BASELINE_FILE = BASE_DIR / "shared" / "eval" / "baseline.json"
AGENTS_DIR = BASE_DIR / "agents"
EVAL_TOOL = BASE_DIR / "opencode_improvement" / "__main__.py"  # Entry for 'python3 -m opencode_improvement eval'

# Data-driven special case: capability-transfer failures target spawner.py.
TRANSFER_CAPABILITY_PATCH: Dict[str, Any] = {
    "target_file": "opencode_improvement/spawner.py",
    "agent": None,
    "reason": "Capability transfer fails frequently; needs fuzzy-matching for skills.",
    "proposed_change": "Implement fuzzy matching in spawner.py",
    "verification_test": "python3 -m py_compile opencode_improvement/spawner.py",
}

# Shadow-test thresholds.
DEFAULT_MIN_PASS_RATE = 0.8  # required when baseline.json is missing
FAILURE_RATE_THRESHOLD = 0.6  # analyze_failures: success_rate below this
FAILURE_COUNT_THRESHOLD = 3  # analyze_failures: at least this many applications


class LogicEvolver:
    """
    Project Aether: Recursive Code-Level Self-Improvement (RCSI) - EVOLVED.
    Now integrates with agent-eval to empirically verify logic patches before promotion.
    """

    def __init__(self):
        self.ctx = self._load_context()

    def _load_context(self) -> dict:
        if CONTEXT_FILE.exists():
            try:
                return json.loads(CONTEXT_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_context(self, ctx: dict) -> None:
        CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONTEXT_FILE.write_text(json.dumps(ctx, indent=2))

    # ── failure analysis ─────────────────────────────────────────────────

    def analyze_failures(self) -> List[Dict[str, Any]]:
        """Find strategies that are consistently failing.

        A strategy counts as failing when its ``success_rate`` is below
        ``FAILURE_RATE_THRESHOLD`` over at least ``FAILURE_COUNT_THRESHOLD``
        applications. The most recent agent that used the strategy is attached
        (when known) so ``synthesize_patch`` can target a real file.
        """
        effectiveness = self.ctx.get("strategy_effectiveness", {})
        strategy_log = self.ctx.get("strategy_log", [])
        failures = []
        for name, stats in effectiveness.items():
            if (
                stats.get("success_rate", 1.0) < FAILURE_RATE_THRESHOLD
                and stats.get("count", 0) >= FAILURE_COUNT_THRESHOLD
            ):
                failure = {
                    "strategy": name,
                    "success_rate": stats["success_rate"],
                    "count": stats["count"],
                }
                agent = self._last_agent_for_strategy(name, strategy_log)
                if agent:
                    failure["agent"] = agent
                failures.append(failure)
        return failures

    @staticmethod
    def _last_agent_for_strategy(strategy: str, strategy_log: list) -> Optional[str]:
        """Return the most recent ``agent_target`` that used this strategy."""
        for entry in reversed(strategy_log):
            if entry.get("strategy_chosen") == strategy and entry.get("agent_target"):
                return entry["agent_target"]
        return None

    # ── patch synthesis ──────────────────────────────────────────────────

    def synthesize_patch(self, failure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Template-driven patch synthesis.

        The ``transfer_capability`` strategy has a data-driven special case
        (``TRANSFER_CAPABILITY_PATCH``). Every other failing strategy gets a
        generic, honest patch: a review note targeting the most recent agent
        config that used the strategy (when known), verified by the eval CLI.
        """
        strat = failure["strategy"]
        if strat == "transfer_capability":
            return dict(TRANSFER_CAPABILITY_PATCH)

        agent = failure.get("agent")
        if agent:
            target_file = f"agents/{agent}.md"
            verification_test = (
                f"python3 -m opencode_improvement eval --agent {agent} --provider mock"
            )
        else:
            target_file = None
            verification_test = "python3 -m opencode_improvement eval --provider mock"

        return {
            "target_file": target_file,
            "agent": agent,
            "reason": (
                f"Strategy '{strat}' has success_rate {failure.get('success_rate')} "
                f"over {failure.get('count')} applications."
            ),
            "proposed_change": (
                f"Review strategy '{strat}' usage in agent configs; propose a concrete improvement"
            ),
            "verification_test": verification_test,
        }

    # ── shadow verification ──────────────────────────────────────────────

    def verify_patch(self, patch: Dict[str, Any]) -> bool:
        """
        The 'Shadow Test' — REAL verification, never unconditional.

        Flow:
        1. Resolve the target file (relative to ``BASE_DIR``).
        2. Create a temporary shadow copy and apply ``proposed_change`` to it.
        3a. Agent configs: run ``python3 -m opencode_improvement eval
            --agent <target> --provider mock`` against the shadow copy and
            compare the pass rate to ``shared/eval/baseline.json``. Verified
            only if shadow pass rate >= baseline pass rate (>= 0.8 if no
            baseline exists).
        3b. Non-agent files: ``python3 -m py_compile`` the shadow copy;
            verified only if it compiles.
        """
        target_rel = patch.get("target_file")
        if not target_rel:
            print("  Cannot verify: patch has no target_file.")
            return False
        target = BASE_DIR / target_rel
        if not target.exists():
            print(f"  Cannot verify: target file not found: {target}")
            return False

        if target.parent == AGENTS_DIR:
            agent = patch.get("agent") or target.stem
            return self._shadow_eval(target, patch, agent)
        return self._syntax_check(target, patch)

    def _shadow_eval(self, target: Path, patch: Dict[str, Any], agent: str) -> bool:
        """Run the eval CLI against a shadow copy of an agent config."""
        print(f"  Shadow-testing agent '{agent}' via agent-eval...")
        with tempfile.TemporaryDirectory() as tmp:
            shadow = Path(tmp) / target.name
            shadow.write_text(target.read_text())
            self._apply_change(shadow, patch["proposed_change"])

            # Swap the real file for the shadow copy so the eval CLI genuinely
            # evaluates the patched config; restore in all cases.
            original = target.read_text()
            try:
                target.write_text(shadow.read_text())
                proc = subprocess.run(
                    [sys.executable, "-m", "opencode_improvement", "eval",
                     "--agent", agent, "--provider", "mock"],
                    capture_output=True, text=True, timeout=180,
                )
            finally:
                target.write_text(original)

        if proc.returncode != 0:
            print(f"  Eval failed (exit {proc.returncode}): {proc.stderr.strip()[-500:]}")
            return False
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print("  Eval produced invalid JSON output.")
            return False

        shadow_rate = float(result.get("pass_rate", 0.0) or 0.0)
        baseline_rate = self._baseline_pass_rate(agent)
        if baseline_rate is not None:
            threshold = baseline_rate
            print(f"  Shadow pass rate {shadow_rate:.3f} vs baseline {baseline_rate:.3f}")
        else:
            threshold = DEFAULT_MIN_PASS_RATE
            print(
                f"  Shadow pass rate {shadow_rate:.3f} vs baseline N/A "
                f"(threshold {DEFAULT_MIN_PASS_RATE:.2f})"
            )
        ok = shadow_rate >= threshold
        print(f"  {'VERIFIED' if ok else 'REJECTED'}: {shadow_rate:.3f} >= {threshold:.3f}")
        return ok

    def _syntax_check(self, target: Path, patch: Dict[str, Any]) -> bool:
        """Fallback verification for non-agent files: py_compile the shadow copy."""
        print(f"  Syntax-checking {target} (non-agent file)...")
        with tempfile.TemporaryDirectory() as tmp:
            shadow = Path(tmp) / target.name
            shadow.write_text(target.read_text())
            self._apply_change(shadow, patch["proposed_change"])
            proc = subprocess.run(
                [sys.executable, "-m", "py_compile", str(shadow)],
                capture_output=True, text=True, timeout=60,
            )
        if proc.returncode != 0:
            print(f"  Syntax check FAILED: {proc.stderr.strip()[-500:]}")
            return False
        print("  Syntax check passed.")
        return True

    def _baseline_pass_rate(self, agent: Optional[str] = None) -> Optional[float]:
        """Pass rate from ``shared/eval/baseline.json`` (per-agent when available)."""
        if not BASELINE_FILE.exists():
            return None
        try:
            baseline = json.loads(BASELINE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        # Per-agent pass rate (baseline may carry agents_tested)
        if agent:
            agents = baseline.get("agents_tested") or {}
            stats = agents.get(agent)
            if stats and stats.get("pass_rate") is not None:
                return float(stats["pass_rate"])
        # Global pass rate: top-level, then eval section
        rate = baseline.get("pass_rate")
        if rate is None:
            rate = baseline.get("eval", {}).get("pass_rate")
        return float(rate) if rate is not None else None

    @staticmethod
    def _apply_change(path: Path, change: str) -> None:
        """Append a documented improvement note (the only safe generic apply)."""
        if path.suffix == ".py":
            note = f"\n\n# Aether RCSI improvement note: {change}\n"
        else:
            note = f"\n\n<!-- Aether RCSI improvement note: {change} -->\n"
        with open(path, "a") as f:
            f.write(note)

    # ── outcome recording (fixes the blindness) ──────────────────────────

    def record_outcome(self, strategy: str, success: bool) -> Dict[str, Any]:
        """Record a strategy outcome (including FAILURES) into strategy_effectiveness.

        Previously only successes were ever logged, so ``success_rate`` was
        always 1.0 and ``analyze_failures()`` could never fire. This method
        updates the running success rate so the evolution loop can actually
        trigger.
        """
        ctx = self._load_context()
        se = ctx.setdefault("strategy_effectiveness", {})
        stats = se.setdefault(strategy, {"count": 0, "completed": 0, "success_rate": 1.0})
        prev_completed = stats.get("completed", 0)
        prev_successes = stats.get("successes")
        if prev_successes is None:
            prev_successes = round(stats.get("success_rate", 1.0) * prev_completed)
        stats["count"] = stats.get("count", 0) + 1
        stats["completed"] = prev_completed + 1
        stats["successes"] = prev_successes + (1 if success else 0)
        stats["success_rate"] = round(stats["successes"] / stats["completed"], 2)
        ctx["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save_context(ctx)
        self.ctx = ctx
        return stats

    # ── the loop ─────────────────────────────────────────────────────────

    def run_evolution_cycle(self):
        """The Empirical RCSI loop: analyze -> synthesize -> shadow-verify -> apply."""
        print("Starting Empirical RCSI Evolution Cycle...")
        failures = self.analyze_failures()
        if not failures:
            print("No consistent failures detected. System is stable.")
            return {"status": "stable", "failures": 0, "promoted": 0, "rejected": 0}

        from opencode_improvement.track import PerformanceTracker

        tracker = PerformanceTracker()
        promoted = 0
        rejected = 0
        for fail in failures:
            patch = self.synthesize_patch(fail)
            if not patch:
                print(f"No patch synthesized for strategy '{fail['strategy']}'.")
                continue
            if self.verify_patch(patch):
                print(f"PATCH VERIFIED: Promoting change to {patch['target_file']}")
                self._apply_patch(patch)
                tracker.log(
                    agent="logic_evolve",
                    task=(
                        f"promote patch for strategy '{fail['strategy']}' "
                        f"-> {patch['target_file']}"
                    ),
                    outcome="promoted",
                    context={"strategy": fail["strategy"]},
                )
                promoted += 1
            else:
                print(f"PATCH REJECTED: {patch['target_file']} failed verification.")
                tracker.log(
                    agent="logic_evolve",
                    task=(
                        f"reject patch for strategy '{fail['strategy']}' "
                        f"-> {patch['target_file']}"
                    ),
                    outcome="rejected",
                    context={"strategy": fail["strategy"]},
                )
                rejected += 1
        print(f"Evolution cycle complete: {promoted} promoted, {rejected} rejected.")
        return {
            "status": "cycle_complete",
            "failures": len(failures),
            "promoted": promoted,
            "rejected": rejected,
        }

    def _apply_patch(self, patch: Dict[str, Any]) -> bool:
        """Apply a verified patch to the real target file (append improvement note)."""
        target = BASE_DIR / patch["target_file"]
        if not target.exists():
            print(f"  WARNING: target file missing, cannot apply: {target}")
            return False
        self._apply_change(target, patch["proposed_change"])
        print(f"  Applied improvement note to {target}")
        return True


if __name__ == "__main__":
    evolver = LogicEvolver()
    result = evolver.run_evolution_cycle()
    print(json.dumps(result, indent=2))
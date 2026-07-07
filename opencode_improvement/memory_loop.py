"""
Cross-Session Memory Loop — closes the gap between "having memory" and "improving based on memory."

Reads past session data, eval results, and performance metrics to generate
actionable behavior adjustments for future sessions. Creates a feedback record
so each session builds on the last.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path.home() / ".config" / "opencode"
CONTEXT_FILE = BASE_DIR / "shared" / "context.json"
PERFORMANCE_FILE = BASE_DIR / "shared" / "performance.json"
MEMFS_PROJECT_FILE = BASE_DIR / "memory" / "project" / "system" / "project.md"
MEMFS_HANDOFF_FILE = BASE_DIR / "memory" / "project" / "system" / "handoff.md"


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _read_memfs(path: Path) -> str:
    """Read a memory file safely."""
    if path.exists():
        try:
            return path.read_text()
        except OSError:
            return ""
    return ""


def get_session_summary() -> dict:
    """Summarize the current session state from shared context and performance data."""
    ctx = _load_json(CONTEXT_FILE)
    perf = _load_json(PERFORMANCE_FILE)

    strategy_log = ctx.get("strategy_log", [])
    decisions = ctx.get("decisions", [])
    workflow_trace = ctx.get("workflow_trace", [])
    active_tasks = ctx.get("active_tasks", [])
    recent_artifacts = ctx.get("recent_artifacts", [])

    # Performance stats
    entries = perf if isinstance(perf, list) else []
    total_entries = len(entries)
    success_count = sum(1 for e in entries if e.get("outcome") == "success")

    return {
        "session_state": {
            "active_tasks": len(active_tasks),
            "total_decisions": len(decisions),
            "total_strategies_logged": len(strategy_log),
            "total_workflow_steps": len(workflow_trace),
            "recent_artifacts": len(recent_artifacts),
        },
        "performance": {
            "total_tasks": total_entries,
            "success_count": success_count,
            "success_rate": round(success_count / total_entries, 2) if total_entries > 0 else 0,
        },
        "strategy_insights": _extract_strategy_insights(ctx),
    }


def _extract_strategy_insights(ctx: dict) -> list:
    """Extract actionable insights from strategy log."""
    strategy_log = ctx.get("strategy_log", [])
    effectiveness = ctx.get("strategy_effectiveness", {})

    insights = []

    # Which strategies work best?
    best_strategies = sorted(
        effectiveness.items(),
        key=lambda kv: (kv[1].get("success_rate", 0) or 0, kv[1].get("count", 0)),
        reverse=True,
    )[:3]

    for name, stats in best_strategies:
        if stats.get("success_rate", 0) >= 0.8 and stats.get("count", 0) >= 2:
            insights.append({
                "type": "strategy_effectiveness",
                "finding": f"Strategy '{name}' has {stats['success_rate']:.0%} success rate across {stats['count']} applications",
                "action": "Prefer this strategy for similar situations in the future",
                "confidence": stats.get("avg_confidence_after", 0.5),
            })

    # Calibration trends
    for name, stats in effectiveness.items():
        delta = stats.get("calibration_delta", 0)
        count = stats.get("count", 0)
        if abs(delta) > 0.2 and count >= 2:
            direction = "improving" if delta > 0 else "declining"
            insights.append({
                "type": "calibration_trend",
                "finding": f"Confidence calibration for '{name}' is {direction} (delta={delta:+.2f})",
                "action": "Review confidence estimates for this strategy — they may need recalibration",
                "confidence": 0.7,
            })

    return insights


def generate_memory_feedback() -> dict:
    """Generate a structured feedback record from current session to future sessions.

    This is the core of the memory loop — it produces a compact record
    that the NEXT session can read to pick up where this one left off.
    """
    ctx = _load_json(CONTEXT_FILE)
    session_summary = get_session_summary()

    # Extract key decisions made this session
    decisions = ctx.get("decisions", [])
    recent_decisions = decisions[-5:] if len(decisions) > 5 else decisions

    # Strategy effectiveness snapshot
    effectiveness = ctx.get("strategy_effectiveness", {})

    feedback = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "type": "cross_session_feedback",
        "version": "1.0",
        "session_state": session_summary["session_state"],
        "performance_summary": session_summary["performance"],
        "key_decisions": [
            {
                "id": d.get("id", ""),
                "description": d.get("description", ""),
                "rationale": d.get("rationale", ""),
            }
            for d in recent_decisions
        ],
        "strategy_effectiveness_snapshot": {
            name: {
                "success_rate": stats.get("success_rate"),
                "count": stats.get("count"),
                "calibration_delta": stats.get("calibration_delta"),
            }
            for name, stats in effectiveness.items()
            if stats.get("count", 0) > 0
        },
        "actionable_insights": session_summary["strategy_insights"],
        "recommendations_for_next_session": _generate_recommendations(ctx),
    }

    return feedback


def _generate_recommendations(ctx: dict) -> list:
    """Generate specific recommendations for the next session."""
    recommendations = []
    effectiveness = ctx.get("strategy_effectiveness", {})

    # Find best strategies to repeat
    for name, stats in sorted(
        effectiveness.items(),
        key=lambda kv: kv[1].get("success_rate", 0) or 0,
        reverse=True,
    )[:2]:
        if stats.get("success_rate", 0) >= 0.8:
            recommendations.append(
                f"Continue using '{name}' strategy — {stats['success_rate']:.0%} success rate"
            )

    # Find strategies needing improvement
    for name, stats in effectiveness.items():
        if stats.get("success_rate", 0) is not None and stats["success_rate"] < 0.5:
            recommendations.append(
                f"Reconsider '{name}' strategy — only {stats['success_rate']:.0%} success rate "
                f"over {stats['count']} attempts"
            )

    # General recommendations from task patterns
    ctx_tasks = ctx.get("active_tasks", [])
    if ctx_tasks:
        recommendations.append(
            f"Complete {len(ctx_tasks)} pending task(s): "
            + ", ".join(t.get("name", "unknown") for t in ctx_tasks)
        )

    return recommendations


def write_handoff() -> dict:
    """Write a structured handoff record that the next session reads.

    This writes to shared/context.json's findings section for cross-session persistence,
    and optionally to the memfs handoff file.
    """
    feedback = generate_memory_feedback()

    # Load and update context
    ctx = _load_json(CONTEXT_FILE)
    ctx.setdefault("findings", {})

    # Store cross-session feedback
    if "memory_loop" not in ctx["findings"]:
        ctx["findings"]["memory_loop"] = []
    ctx["findings"]["memory_loop"].append(feedback)

    ctx.setdefault("session", {})["last_handoff"] = feedback["generated_at"]
    CONTEXT_FILE.write_text(json.dumps(ctx, indent=2))

    # Also write to memfs handoff if available
    if MEMFS_HANDOFF_FILE:
        try:
            MEMFS_HANDOFF_FILE.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                f"# Session Handoff — {feedback['generated_at']}",
                "",
                "## Performance",
                f"- Tasks: {feedback['performance_summary']['total_tasks']} total, "
                f"{feedback['performance_summary']['success_rate']:.0%} success rate",
                "",
                "## Key Decisions",
            ]
            for d in feedback["key_decisions"]:
                lines.append(f"- {d['description']} ({d['rationale']})")
            lines.append("")
            lines.append("## Recommendations for Next Session")
            for r in feedback["recommendations_for_next_session"]:
                lines.append(f"- {r}")
            lines.append("")
            MEMFS_HANDOFF_FILE.write_text("\n".join(lines))
        except OSError:
            pass

    return {"status": "ok", "feedback_id": feedback["generated_at"]}


def read_past_feedback(limit: int = 3) -> dict:
    """Read the most recent cross-session feedback records."""
    ctx = _load_json(CONTEXT_FILE)
    records = ctx.get("findings", {}).get("memory_loop", [])
    recent = records[-limit:] if records else []

    return {
        "status": "ok",
        "total_records": len(records),
        "recent_feedback": recent,
    }


def run_cli(argv: list = None):
    """CLI entry point for memory loop commands."""
    import argparse as ap
    p = ap.ArgumentParser(prog="memory", description="Cross-session memory loop")
    p.add_argument("--status", "-s", action="store_true", help="Show session summary")
    p.add_argument("--handoff", action="store_true", help="Write handoff record")
    p.add_argument("--feedback", "-f", action="store_true", help="Read past feedback")
    args = p.parse_args(argv if argv else [])

    if args.status:
        print(json.dumps(get_session_summary(), indent=2))
    elif args.handoff:
        result = write_handoff()
        print(json.dumps(result, indent=2))
        if result.get("status") == "ok":
            print(f"\nHandoff written. Next session should read this to pick up context.")
    elif args.feedback:
        print(json.dumps(read_past_feedback(), indent=2))
    else:
        print(json.dumps(get_session_summary(), indent=2))

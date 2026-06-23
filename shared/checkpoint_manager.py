"""Checkpoint writer/reader for agent workflow state persistence.

Each stage writes a checkpoint after completion. The orchestrator and other
agents use checkpoints to resume interrupted workflows and to present state
at human handoff points.

Architecture inspired by OpenMontage's lib/checkpoint.py (stage-based
checkpointing with artifact validation) but generalized for cross-agent use.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum


# ── Canonical Agent Stages ──────────────────────────────────────────────────


class AgentStage(str, Enum):
    """Canonical stages shared across all agents.

    Each agent may also define custom stages (see CUSTOM_STAGES below).
    """
    UNDERSTAND = "understand"
    PATH_SELECTION = "path_selection"
    DELEGATION_CHECK = "delegation_check"
    SPLIT_PARALLELIZE = "split_parallelize"
    EXECUTE = "execute"
    VERIFY = "verify"


ORCHESTRATOR_STAGES = [
    AgentStage.UNDERSTAND,
    AgentStage.PATH_SELECTION,
    AgentStage.DELEGATION_CHECK,
    AgentStage.SPLIT_PARALLELIZE,
    AgentStage.EXECUTE,
    AgentStage.VERIFY,
]

# Custom stage maps per agent type — extend as agents define their own stages.
# Each entry: agent_name -> list of stage names in canonical order.
CUSTOM_STAGES: dict[str, list[str]] = {
    "video-creator": [
        "research",
        "proposal",
        "idea",
        "script",
        "scene_plan",
        "assets",
        "edit",
        "compose",
        "publish",
    ],
    "explore": [
        "query",
        "search",
        "synthesize",
    ],
    "fixer": [
        "parse_context",
        "apply_changes",
        "verify_changes",
    ],
    "test": [
        "analyze",
        "write_tests",
        "run_tests",
        "fix_failures",
    ],
}


def get_agent_stages(agent_name: str) -> list[str]:
    """Return the ordered stage list for a given agent type.

    Falls back to orchestrator stages for unknown agents.
    """
    return CUSTOM_STAGES.get(agent_name, [s.value for s in ORCHESTRATOR_STAGES])


# ── Checkpoint Data ─────────────────────────────────────────────────────────


CHECKPOINT_VERSION = "1.0"

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"


class CheckpointValidationError(ValueError):
    """Raised when a checkpoint structure is invalid."""


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _agent_dir(agent_name: str) -> Path:
    return _ensure_dir(CHECKPOINT_DIR / agent_name)


def _run_dir(agent_name: str, run_id: str) -> Path:
    """Return the run directory path. Creates it if it doesn't exist."""
    return _ensure_dir(_agent_dir(agent_name) / run_id)


def _run_dir_readonly(agent_name: str, run_id: str) -> Path:
    """Return the run directory path. Does NOT create it."""
    return CHECKPOINT_DIR / agent_name / run_id


def _checkpoint_path(agent_name: str, run_id: str, stage: str) -> Path:
    return _run_dir(agent_name, run_id) / f"checkpoint_{stage}.json"


def _checkpoint_path_readonly(agent_name: str, run_id: str, stage: str) -> Path:
    """Read-only version — does not create parent directories."""
    return CHECKPOINT_DIR / agent_name / run_id / f"checkpoint_{stage}.json"


def _run_meta_path(agent_name: str, run_id: str) -> Path:
    return _run_dir(agent_name, run_id) / "run.json"


# ── Validation ──────────────────────────────────────────────────────────────


def validate_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Validate checkpoint structure.

    Raises CheckpointValidationError if the structure is invalid.
    """
    errors = []

    if not isinstance(checkpoint.get("version"), str):
        errors.append("Missing or invalid 'version'")
    if not isinstance(checkpoint.get("agent_name"), str):
        errors.append("Missing or invalid 'agent_name'")
    if not isinstance(checkpoint.get("run_id"), str):
        errors.append("Missing or invalid 'run_id'")
    if not isinstance(checkpoint.get("stage"), str):
        errors.append("Missing or invalid 'stage'")
    if not isinstance(checkpoint.get("status"), str):
        errors.append("Missing or invalid 'status'")
    if checkpoint.get("status") not in ("pending", "in_progress", "completed", "failed", "skipped"):
        errors.append(f"Invalid status: {checkpoint.get('status')!r}")
    if not isinstance(checkpoint.get("timestamp"), str):
        errors.append("Missing or invalid 'timestamp'")
    if not isinstance(checkpoint.get("artifacts"), dict):
        errors.append("Missing or invalid 'artifacts' (must be dict)")

    if errors:
        raise CheckpointValidationError(
            f"Checkpoint validation failed: {'; '.join(errors)}"
        )


# ── Write / Read ────────────────────────────────────────────────────────────


def save_checkpoint(
    agent_name: str,
    run_id: str,
    stage: str,
    status: str,
    *,
    artifacts: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
    snapshot: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Path:
    """Write a checkpoint file for an agent stage.

    Args:
        agent_name: Agent type (e.g., 'orchestrator', 'video-creator')
        run_id: Unique run identifier (e.g., 'run_20260623_abc123')
        stage: Current stage name
        status: One of 'pending', 'in_progress', 'completed', 'failed', 'skipped'
        artifacts: Stage outputs keyed by name
        error: Error message if the stage failed
        snapshot: Snapshot of agent state (active_tasks, decisions, etc.)
        metadata: Additional metadata (e.g., {"model": "claude-4", "tokens": 1234})
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    checkpoint: dict[str, Any] = {
        "version": CHECKPOINT_VERSION,
        "agent_name": agent_name,
        "run_id": run_id,
        "stage": stage,
        "status": status,
        "timestamp": timestamp,
        "artifacts": artifacts or {},
    }
    if error is not None:
        checkpoint["error"] = error
    if snapshot is not None:
        checkpoint["snapshot"] = snapshot
    if metadata is not None:
        checkpoint["metadata"] = metadata

    validate_checkpoint(checkpoint)

    path = _checkpoint_path(agent_name, run_id, stage)
    _ensure_dir(path.parent)
    with open(path, "w") as f:
        json.dump(checkpoint, f, indent=2)

    # Update run metadata
    _update_run_meta(agent_name, run_id, stage, status)

    return path


def load_checkpoint(
    agent_name: str, run_id: str, stage: str
) -> Optional[dict[str, Any]]:
    """Read a checkpoint file. Returns None if not found."""
    path = _checkpoint_path_readonly(agent_name, run_id, stage)
    if not path.exists():
        return None
    with open(path) as f:
        checkpoint = json.load(f)
    return checkpoint


def get_latest_checkpoint(
    agent_name: str, run_id: str
) -> Optional[dict[str, Any]]:
    """Find the most recent checkpoint for a run (by file mtime)."""
    run_dir = _run_dir_readonly(agent_name, run_id)
    if not run_dir.exists():
        return None

    checkpoints = sorted(
        run_dir.glob("checkpoint_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not checkpoints:
        return None

    with open(checkpoints[0]) as f:
        return json.load(f)


def get_completed_stages(
    agent_name: str, run_id: str
) -> list[dict[str, Any]]:
    """Return list of checkpoint dicts for stages with status 'completed'."""
    run_dir = _run_dir_readonly(agent_name, run_id)
    if not run_dir.exists():
        return []

    completed = []
    for cp_file in sorted(run_dir.glob("checkpoint_*.json")):
        with open(cp_file) as f:
            cp = json.load(f)
        if cp.get("status") == "completed":
            completed.append(cp)
    return completed


def get_next_stage(
    agent_name: str, run_id: str
) -> Optional[str]:
    """Determine the next stage to run based on completed checkpoints."""
    stages = get_agent_stages(agent_name)
    completed_stages = {cp["stage"] for cp in get_completed_stages(agent_name, run_id)}

    for stage in stages:
        if stage not in completed_stages:
            return stage
    return None  # All stages complete


def list_runs(agent_name: Optional[str] = None) -> list[dict[str, Any]]:
    """List all checkpoint runs, optionally filtered by agent.

    Returns metadata from each run's run.json.
    """
    if agent_name:
        agent_dirs = [CHECKPOINT_DIR / agent_name] if (CHECKPOINT_DIR / agent_name).exists() else []
    else:
        if not CHECKPOINT_DIR.exists():
            return []
        agent_dirs = [d for d in CHECKPOINT_DIR.iterdir() if d.is_dir()]

    runs = []
    for agent_dir in agent_dirs:
        for run_dir in sorted(agent_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            meta_path = run_dir / "run.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
            else:
                meta = {"run_id": run_dir.name, "agent_name": agent_dir.name}
            runs.append(meta)

    return runs


# ── Resume Helpers ──────────────────────────────────────────────────────────


def resume_run(agent_name: str, run_id: str) -> Optional[dict[str, Any]]:
    """Load the latest checkpoint and return a resume packet.

    Returns:
        dict with:
            - run_id: the run ID
            - agent_name: agent type
            - last_stage: last stage name
            - last_status: status of last stage
            - next_stage: suggested next stage
            - completed_stages: list of completed stage names
            - last_artifacts: artifacts from last checkpoint
            - last_snapshot: snapshot from last checkpoint (if any)
            - run_meta: run metadata
        or None if no checkpoints exist.
    """
    latest = get_latest_checkpoint(agent_name, run_id)
    if latest is None:
        return None

    completed = [cp["stage"] for cp in get_completed_stages(agent_name, run_id)]
    next_stage = get_next_stage(agent_name, run_id)

    run_meta = {}
    meta_path = _run_meta_path(agent_name, run_id)
    if meta_path.exists():
        with open(meta_path) as f:
            run_meta = json.load(f)

    return {
        "run_id": run_id,
        "agent_name": agent_name,
        "last_stage": latest.get("stage"),
        "last_status": latest.get("status"),
        "next_stage": next_stage,
        "completed_stages": completed,
        "last_artifacts": latest.get("artifacts", {}),
        "last_snapshot": latest.get("snapshot"),
        "last_error": latest.get("error"),
        "run_meta": run_meta,
    }


# ── Run Metadata ────────────────────────────────────────────────────────────


def _update_run_meta(
    agent_name: str, run_id: str, stage: str, status: str
) -> None:
    """Update the run metadata file with latest stage info."""
    meta_path = _run_meta_path(agent_name, run_id)
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {
            "version": CHECKPOINT_VERSION,
            "run_id": run_id,
            "agent_name": agent_name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stages": {},
        }

    meta["stages"][stage] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta["last_updated_at"] = datetime.now(timezone.utc).isoformat()

    # Update overall status
    all_statuses = {s["status"] for s in meta["stages"].values()}
    if "in_progress" in all_statuses:
        meta["status"] = "in_progress"
    elif "failed" in all_statuses:
        meta["status"] = "failed"
    elif all(s == "completed" for s in all_statuses):
        meta["status"] = "completed"
    else:
        meta["status"] = "in_progress"

    _ensure_dir(meta_path.parent)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


# ── Pruning ─────────────────────────────────────────────────────────────────


def prune_checkpoints(
    agent_name: Optional[str] = None,
    max_age_hours: int = 168,  # 7 days
    keep_completed_runs: int = 5,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove old or excess checkpoint runs.

    Args:
        agent_name: If set, only prune runs for this agent
        max_age_hours: Remove runs older than this (default 168 = 7 days)
        keep_completed_runs: Keep at least this many completed runs per agent
        dry_run: If True, report what would be removed without deleting

    Returns:
        dict with removed, kept, and freed_size stats
    """
    if CHECKPOINT_DIR.exists():
        agent_dirs = [
            d for d in CHECKPOINT_DIR.iterdir()
            if d.is_dir() and (agent_name is None or d.name == agent_name)
        ]
    else:
        agent_dirs = []

    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
    removed = []
    kept = []
    freed_bytes = 0

    for agent_dir in agent_dirs:
        runs = sorted(
            (d for d in agent_dir.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,  # newest first
        )

        # Separate completed from non-completed
        completed_runs = []
        non_completed_runs = []

        for run_dir in runs:
            meta_path = run_dir / "run.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                is_completed = meta.get("status") == "completed"
            else:
                is_completed = False

            if is_completed:
                completed_runs.append(run_dir)
            else:
                non_completed_runs.append(run_dir)

        # Keep the N most recent completed runs (already sorted newest first)
        excess_completed = completed_runs[keep_completed_runs:] if keep_completed_runs < len(completed_runs) else []

        # All non-completed runs are candidates if old enough
        old_non_completed = [d for d in non_completed_runs if d.stat().st_mtime <= cutoff]

        # Old excess completed runs are also candidates
        old_excess = [d for d in excess_completed if d.stat().st_mtime <= cutoff]

        to_prune = old_non_completed + old_excess

        for run_dir in to_prune:
            size = sum(
                f.stat().st_size for f in run_dir.rglob("*") if f.is_file()
            )
            freed_bytes += size
            if dry_run:
                removed.append({
                    "agent": agent_dir.name,
                    "run_id": run_dir.name,
                    "size_bytes": size,
                })
            else:
                import shutil
                shutil.rmtree(run_dir)
                removed.append({
                    "agent": agent_dir.name,
                    "run_id": run_dir.name,
                    "size_bytes": size,
                })

        # Remaining runs are "kept"
        remaining = [d for d in runs if d not in to_prune]
        for run_dir in remaining:
            kept.append({
                "agent": agent_dir.name,
                "run_id": run_dir.name,
            })

    return {
        "dry_run": dry_run,
        "removed_count": len(removed),
        "kept_count": len(kept),
        "freed_bytes": freed_bytes,
        "removed": removed,
        "kept": kept,
    }


# ── CLI Helpers ─────────────────────────────────────────────────────────────


def format_run_table(runs: list[dict[str, Any]]) -> str:
    """Format runs as a readable table string."""
    if not runs:
        return "No checkpoint runs found."

    lines = []
    lines.append(f"{'Agent':<20} {'Run ID':<30} {'Status':<15} {'Stages':<10} {'Last Updated'}")
    lines.append("-" * 90)
    for run in runs:
        agent = run.get("agent_name", "?")
        run_id = run.get("run_id", "?")
        status = run.get("status", "unknown")
        stages = str(len(run.get("stages", {})))
        updated = run.get("last_updated_at", run.get("started_at", "?"))

        # Truncate long run_ids
        if len(run_id) > 28:
            run_id = run_id[:25] + "..."

        lines.append(f"{agent:<20} {run_id:<30} {status:<15} {stages:<10} {updated[:19]}")
    return "\n".join(lines)


def format_checkpoint_detail(checkpoint: dict[str, Any]) -> str:
    """Format a single checkpoint's details for inspection."""
    lines = []
    lines.append(f"  Run:         {checkpoint.get('run_id', '?')}")
    lines.append(f"  Agent:       {checkpoint.get('agent_name', '?')}")
    lines.append(f"  Stage:       {checkpoint.get('stage', '?')}")
    lines.append(f"  Status:      {checkpoint.get('status', '?')}")
    lines.append(f"  Timestamp:   {checkpoint.get('timestamp', '?')}")
    if checkpoint.get("error"):
        lines.append(f"  Error:       {checkpoint['error']}")
    if checkpoint.get("metadata"):
        lines.append(f"  Metadata:    {json.dumps(checkpoint['metadata'])}")
    artifacts = checkpoint.get("artifacts", {})
    if artifacts:
        lines.append(f"  Artifacts:   {len(artifacts)} key(s)")
        for k, v in list(artifacts.items())[:10]:
            val_str = str(v)
            if len(val_str) > 80:
                val_str = val_str[:77] + "..."
            lines.append(f"    {k}: {val_str}")
        if len(artifacts) > 10:
            lines.append(f"    ... and {len(artifacts) - 10} more")
    if checkpoint.get("snapshot"):
        snap = checkpoint["snapshot"]
        lines.append(f"  Snapshot:    {len(snap)} key(s)")
    return "\n".join(lines)

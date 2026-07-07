"""CLI commands for checkpoint management.

Usage:
    python3 -m opencode_improvement checkpoint <subcommand> [options]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from pathlib import Path

# Add shared to path if needed
_shared_dir = Path(__file__).resolve().parent.parent / "shared"
if _shared_dir.exists():
    sys.path.insert(0, str(_shared_dir.parent))


def add_subparser(subparsers) -> argparse.ArgumentParser:
    """Register the 'checkpoint' subcommand and return the parser."""
    cp = subparsers.add_parser(
        "checkpoint", help="Manage agent workflow checkpoints (save, list, inspect, resume, prune)"
    )
    cp_sub = cp.add_subparsers(dest="checkpoint_command", help="Checkpoint subcommands")

    # --- list ---
    lp = cp_sub.add_parser("list", help="List checkpoint runs")
    lp.add_argument("--agent", "-a", default=None, help="Filter by agent name")

    # --- inspect ---
    ip = cp_sub.add_parser("inspect", help="Inspect a checkpoint run")
    ip.add_argument("--agent", "-a", required=True, help="Agent name")
    ip.add_argument("--run", "-r", required=True, help="Run ID")
    ip.add_argument("--stage", "-s", default=None, help="Specific stage (default: latest)")
    ip.add_argument("--json", action="store_true", help="Output raw JSON")

    # --- save ---
    sp = cp_sub.add_parser("save", help="Save a checkpoint (programmatic use)")
    sp.add_argument("--agent", "-a", required=True, help="Agent name")
    sp.add_argument("--run", "-r", required=True, help="Run ID")
    sp.add_argument("--stage", "-s", required=True, help="Stage name")
    sp.add_argument("--status", choices=["pending", "in_progress", "completed", "failed", "skipped"],
                    required=True, help="Stage status")
    sp.add_argument("--artifacts", default=None, help="JSON string of artifacts dict")
    sp.add_argument("--error", default=None, help="Error message (for failed status)")
    sp.add_argument("--snapshot", default=None, help="JSON string of state snapshot")
    sp.add_argument("--metadata", default=None, help="JSON string of metadata")

    # --- resume ---
    rp = cp_sub.add_parser("resume", help="Get resume packet for a run")
    rp.add_argument("--agent", "-a", required=True, help="Agent name")
    rp.add_argument("--run", "-r", required=True, help="Run ID")
    rp.add_argument("--json", action="store_true", help="Output raw JSON")

    # --- prune ---
    pp = cp_sub.add_parser("prune", help="Remove old checkpoint runs")
    pp.add_argument("--agent", "-a", default=None, help="Prune only this agent's checkpoints")
    pp.add_argument("--max-age", type=int, default=168, help="Max age in hours (default: 168 = 7 days)")
    pp.add_argument("--keep", type=int, default=5, help="Keep at least N completed runs per agent")
    pp.add_argument("--dry-run", action="store_true", help="Preview removals without deleting")
    pp.add_argument("--force", action="store_true", help="Actually perform pruning")

    # --- next-stage ---
    np = cp_sub.add_parser("next-stage", help="Show next stage to run")
    np.add_argument("--agent", "-a", required=True, help="Agent name")
    np.add_argument("--run", "-r", required=True, help="Run ID")

    return cp


def run_checkpoint(args) -> int:
    """Execute the checkpoint subcommand. Returns exit code."""
    from shared.checkpoint_manager import (
        save_checkpoint,
        load_checkpoint,
        get_latest_checkpoint,
        get_next_stage,
        list_runs,
        resume_run,
        prune_checkpoints,
        format_run_table,
        format_checkpoint_detail,
    )

    cmd = args.checkpoint_command
    if cmd is None:
        print("Error: checkpoint subcommand required (list, inspect, save, resume, prune, next-stage)")
        return 1

    if cmd == "list":
        runs = list_runs(agent_name=args.agent)
        print(format_run_table(runs))
        return 0

    if cmd == "inspect":
        if args.stage:
            cp = load_checkpoint(args.agent, args.run, args.stage)
        else:
            cp = get_latest_checkpoint(args.agent, args.run)

        if cp is None:
            print(f"No checkpoint found for {args.agent}/{args.run}" +
                  (f"/{args.stage}" if args.stage else ""))
            return 1

        if args.json:
            print(json.dumps(cp, indent=2))
        else:
            print(format_checkpoint_detail(cp))
        return 0

    if cmd == "save":
        artifacts = {}
        if args.artifacts:
            try:
                artifacts = json.loads(args.artifacts)
            except json.JSONDecodeError as e:
                print(f"Error parsing --artifacts: {e}")
                return 1

        snapshot = None
        if args.snapshot:
            try:
                snapshot = json.loads(args.snapshot)
            except json.JSONDecodeError as e:
                print(f"Error parsing --snapshot: {e}")
                return 1

        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError as e:
                print(f"Error parsing --metadata: {e}")
                return 1

        path = save_checkpoint(
            agent_name=args.agent,
            run_id=args.run,
            stage=args.stage,
            status=args.status,
            artifacts=artifacts or None,
            error=args.error,
            snapshot=snapshot,
            metadata=metadata,
        )
        print(f"Checkpoint saved: {path}")
        return 0

    if cmd == "resume":
        packet = resume_run(args.agent, args.run)
        if packet is None:
            print(f"No checkpoints found for {args.agent}/{args.run}")
            return 1

        if args.json:
            print(json.dumps(packet, indent=2))
        else:
            print("=== Resume Packet ===")
            print(f"  Run:            {packet['run_id']}")
            print(f"  Agent:          {packet['agent_name']}")
            print(f"  Last stage:     {packet['last_stage']} ({packet['last_status']})")
            print(f"  Next stage:     {packet['next_stage'] or 'ALL COMPLETE'}")
            print(f"  Completed:      {', '.join(packet['completed_stages']) or '(none)'}")
            if packet.get("last_error"):
                print(f"  Last error:     {packet['last_error']}")
            if packet.get("last_artifacts"):
                print(f"  Artifacts:      {len(packet['last_artifacts'])} key(s)")
        return 0

    if cmd == "prune":
        if not args.force and not args.dry_run:
            print("Error: must specify --dry-run (preview) or --force (execute)")
            return 1

        result = prune_checkpoints(
            agent_name=args.agent,
            max_age_hours=args.max_age,
            keep_completed_runs=args.keep,
            dry_run=args.dry_run,
        )
        print(f"Prune result: {'DRY RUN - ' if result['dry_run'] else ''}"
              f"{result['removed_count']} removed, {result['kept_count']} kept, "
              f"{_format_size(result['freed_bytes'])} freed")
        return 0

    if cmd == "next-stage":
        stage = get_next_stage(args.agent, args.run)
        if stage:
            print(stage)
        else:
            print("ALL_COMPLETE")
        return 0

    return 1


def _format_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.1f} KB"
    else:
        return f"{bytes_ / (1024*1024):.1f} MB"

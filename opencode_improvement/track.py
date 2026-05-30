#!/usr/bin/env python3
"""
oc-track — Lightweight CLI for agents to log task outcomes.

Usage (from any agent):
    python3 -m opencode_improvement.track <agent> <outcome> <task_description>

    python3 -m opencode_improvement.track build success "implement-login"
    python3 -m opencode_improvement.track media-agent failure "analyze-screenshot" --error "tesseract not found"
    python3 -m opencode_improvement.track web-browser success "navigate-and-scrape" --duration 15

Outcomes: success, failure, partial
"""
import sys
import json
import os
import time
from pathlib import Path

# Resolve config dir
CONFIG_DIR = Path(os.environ.get(
    "OPENCODE_CONFIG_DIR",
    Path.home() / ".config" / "opencode"
))
CONTEXT_PATH = CONFIG_DIR / "shared" / "context.json"


def load_context() -> dict:
    if CONTEXT_PATH.exists():
        try:
            return json.loads(CONTEXT_PATH.read_text())
        except (json.JSONDecodeError, PermissionError):
            return {}
    return {}


def save_context(data: dict):
    CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_PATH.write_text(json.dumps(data, indent=2, default=str))


def log_entry(
    agent: str,
    outcome: str,
    task_description: str,
    duration_s: float = None,
    error: str = None,
    config_snapshot: dict = None,
    context: dict = None,
) -> dict:
    """Record a single task outcome to the shared context."""
    entry = {
        "agent": agent,
        "task": task_description,
        "outcome": outcome,
        "duration_s": duration_s,
        "error": error,
        "config_snapshot": config_snapshot,
        "context": context or {},
        "timestamp": time.time(),
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    data = load_context()
    if "findings" not in data:
        data["findings"] = {}
    if "meta_agent" not in data["findings"]:
        data["findings"]["meta_agent"] = {}
    if "performance_log" not in data["findings"]["meta_agent"]:
        data["findings"]["meta_agent"]["performance_log"] = []

    data["findings"]["meta_agent"]["performance_log"].append(entry)
    save_context(data)
    return entry


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 -m opencode_improvement.track <agent> <outcome> <task> [--duration N] [--error MSG]",
              file=sys.stderr)
        return 1

    agent = sys.argv[1]
    outcome = sys.argv[2]
    task_parts = []
    duration = None
    error = None

    # Parse remaining args
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--duration" and i + 1 < len(sys.argv):
            try:
                duration = float(sys.argv[i + 1])
            except ValueError:
                pass
            i += 2
        elif sys.argv[i] == "--error" and i + 1 < len(sys.argv):
            error = sys.argv[i + 1]
            i += 2
        else:
            task_parts.append(sys.argv[i])
            i += 1

    task_description = " ".join(task_parts) if task_parts else "unknown task"

    if outcome not in ("success", "failure", "partial"):
        print(f"Warning: unknown outcome '{outcome}'. Use: success, failure, partial", file=sys.stderr)

    entry = log_entry(agent, outcome, task_description, duration, error)

    print(json.dumps(entry, indent=2))
    print(f"\n✓ Tracked: [{outcome}] {agent} → {task_description}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    exit(main())

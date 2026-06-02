#!/usr/bin/env python3
"""
OpenCode Context Helper — easy programmatic access to the shared context store.

This script is designed to be called BY AGENTS during their work.
It provides simple one-liner operations for reading, writing, and managing
the shared context without needing to manually manipulate JSON.

Usage (from agent prompts):
    python3 ~/.config/opencode/shared/helpers/context.py read
    python3 ~/.config/opencode/shared/helpers/context.py read-findings debug
    python3 ~/.config/opencode/shared/helpers/context.py add-finding debug '{"summary":"Found bug","severity":"high"}'
    python3 ~/.config/opencode/shared/helpers/context.py add-artifact files_modified src/auth.js
    python3 ~/.config/opencode/shared/helpers/context.py add-decision architecture '{"summary":"Use Redis cache"}'
    python3 ~/.config/opencode/shared/helpers/context.py add-trace-step '{"agent":"debug","status":"completed","summary":"Found root cause"}'
    python3 ~/.config/opencode/shared/helpers/context.py merge-finding debug --summary "Bug title" --detail "Full description" --severity high --file src/auth.js --line 45
"""

import json
import os
import sys
from datetime import datetime, timezone

CONTEXT_PATH = os.path.expanduser("~/.config/opencode/shared/context.json")

VALID_AGENTS = [
    "debug", "security", "architect", "build", "plan",
    "review", "test", "general", "refactor", "docs",
    "explore", "video-creator", "web-browser", "display-agent",
    "pioneer", "meta-agent", "media-agent", "document-agent"
]

VALID_ARTIFACT_CATEGORIES = [
    "files_created", "files_modified", "files_deleted",
    "tests_written", "documentation_updated"
]

VALID_DECISION_CATEGORIES = [
    "architecture", "design", "technology", "workflow", "system"
]


def _load():
    if not os.path.exists(CONTEXT_PATH):
        print(f"Error: Context not found at {CONTEXT_PATH}", file=sys.stderr)
        print("Run: oc-context init", file=sys.stderr)
        sys.exit(1)
    with open(CONTEXT_PATH) as f:
        return json.load(f)


def _save(ctx):
    with open(CONTEXT_PATH, "w") as f:
        json.dump(ctx, f, indent=2)


def cmd_read():
    """Print full context JSON."""
    ctx = _load()
    print(json.dumps(ctx, indent=2))


def cmd_read_findings(agent=None):
    """Print findings, optionally filtered by agent."""
    ctx = _load()
    if agent:
        if agent not in ctx["findings"]:
            print(f"Error: Unknown agent '{agent}'. Valid: {VALID_AGENTS}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(ctx["findings"][agent], indent=2))
    else:
        for a, fs in ctx["findings"].items():
            if fs:
                print(f"--- {a} ({len(fs)} findings) ---")
                for f in fs[-3:]:
                    print(f"  [{f.get('severity','info').upper():8}] {f.get('summary','')[:80]}")
                print()


def cmd_add_finding(agent, finding_json):
    """Add a finding JSON object to a specific agent."""
    ctx = _load()
    if agent not in ctx["findings"]:
        print(f"Error: Unknown agent '{agent}'. Valid: {VALID_AGENTS}", file=sys.stderr)
        sys.exit(1)

    finding = json.loads(finding_json) if isinstance(finding_json, str) else finding_json
    finding.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    finding.setdefault("id", f"{agent}-{int(datetime.now().timestamp())}")

    ctx["findings"][agent].append(finding)
    ctx["state"]["findings_count"] = sum(len(v) for v in ctx["findings"].values())
    ctx["state"]["last_updated_by"] = agent
    ctx["state"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(ctx)
    print(f"Added finding to '{agent}' (total: {len(ctx['findings'][agent])})")


def cmd_merge_finding(agent, **kwargs):
    """Build a finding from keyword args and add it."""
    finding = {
        "id": kwargs.get("id", f"{agent}-{int(datetime.now().timestamp())}"),
        "type": kwargs.get("type", "finding"),
        "summary": kwargs.get("summary", ""),
        "detail": kwargs.get("detail", ""),
        "severity": kwargs.get("severity", "info"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    file_path = kwargs.get("file")
    line = kwargs.get("line")
    function_name = kwargs.get("function")
    if file_path or line or function_name:
        finding["location"] = {}
        if file_path:
            finding["location"]["file"] = file_path
        if line:
            finding["location"]["line"] = int(line)
        if function_name:
            finding["location"]["function"] = function_name

    refs = kwargs.get("references")
    if refs:
        try:
            finding["references"] = json.loads(refs) if isinstance(refs, str) else refs
        except (json.JSONDecodeError, TypeError):
            pass

    cmd_add_finding(agent, finding)


def cmd_add_artifact(category, value):
    """Add a string value to an artifact category."""
    ctx = _load()
    if category not in ctx["artifacts"]:
        print(f"Error: Unknown category '{category}'. Valid: {VALID_ARTIFACT_CATEGORIES}", file=sys.stderr)
        sys.exit(1)
    ctx["artifacts"][category].append(value)
    ctx["state"]["artifacts_count"] = sum(len(v) for v in ctx["artifacts"].values())
    ctx["state"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(ctx)
    print(f"Added to '{category}': {value}")


def cmd_add_decision(category, decision_json):
    """Add a decision JSON to a category."""
    ctx = _load()
    if category not in ctx["decisions"]:
        print(f"Error: Unknown category '{category}'. Valid: {VALID_DECISION_CATEGORIES}", file=sys.stderr)
        sys.exit(1)
    decision = json.loads(decision_json) if isinstance(decision_json, str) else decision_json
    decision.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    ctx["decisions"][category].append(decision)
    ctx["state"]["decisions_count"] = sum(len(v) for v in ctx["decisions"].values())
    ctx["state"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(ctx)
    print(f"Added decision to '{category}'")


def cmd_add_trace_step(step_json):
    """Add a step to the workflow trace."""
    ctx = _load()
    step = json.loads(step_json) if isinstance(step_json, str) else step_json
    step.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    ctx["workflow_trace"].append(step)
    ctx["state"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(ctx)
    print(f"Added trace step (total: {len(ctx['workflow_trace'])})")


def cmd_add_cross_reference(from_agent, to_agent, from_id, to_id, relation):
    """Add a cross-reference between two findings."""
    ctx = _load()
    ref = {
        "from_agent": from_agent,
        "to_agent": to_agent,
        "from_id": from_id,
        "to_id": to_id,
        "relation": relation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ctx["cross_references"].append(ref)
    _save(ctx)
    print(f"Added cross-reference: {from_agent}:{from_id} → {to_agent}:{to_id} ({relation})")


DEFAULT_CONTEXT = {
    "meta": {"version": "2.0.0", "updated": None},
    "session": {
        "current_id": None, "current_title": None,
        "active_agents": [], "workflow_pattern": None, "started_at": None
    },
    "state": {
        "findings_count": 0, "artifacts_count": 0, "decisions_count": 0,
        "last_updated_by": None, "last_updated_at": None
    },
    "findings": {agent: [] for agent in VALID_AGENTS},
    "decisions": {cat: [] for cat in VALID_DECISION_CATEGORIES},
    "artifacts": {
        "files_created": [], "files_modified": [], "files_deleted": [],
        "tests_written": [], "documentation_updated": []
    },
    "cross_references": [],
    "workflow_trace": []
}


def cmd_init():
    """Initialize the shared context store with default empty structure."""
    if os.path.exists(CONTEXT_PATH):
        print(f"Context already exists at {CONTEXT_PATH}", file=sys.stderr)
        print("Use 'clear' to reset it.", file=sys.stderr)
        sys.exit(1)
    now = datetime.now(timezone.utc).isoformat()
    ctx = DEFAULT_CONTEXT.copy()
    ctx["meta"]["updated"] = now
    ctx["state"]["last_updated_at"] = now
    _save(ctx)
    print(f"Initialized shared context at {CONTEXT_PATH}")


def cmd_set_session(session_id=None, title=None, pattern=None):
    """Set session tracking fields."""
    ctx = _load()
    now = datetime.now(timezone.utc).isoformat()
    if session_id:
        ctx["session"]["current_id"] = session_id
    if title:
        ctx["session"]["current_title"] = title
    if pattern:
        ctx["session"]["workflow_pattern"] = pattern
    if session_id and not ctx["session"]["started_at"]:
        ctx["session"]["started_at"] = now
    if session_id:
        ctx["session"]["active_agents"] = []
    ctx["state"]["last_updated_at"] = now
    _save(ctx)
    print(f"Session: id={ctx['session']['current_id']}, pattern={ctx['session']['workflow_pattern']}")


def print_usage():
    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()

    command = sys.argv[1]

    if command == "init":
        cmd_init()
    elif command == "clear":
        import shutil
        os.remove(CONTEXT_PATH)
        cmd_init()
    elif command == "read":
        cmd_read()
    elif command == "read-findings":
        cmd_read_findings(sys.argv[2] if len(sys.argv) > 2 else None)
    elif command == "add-finding":
        if len(sys.argv) < 4:
            print("Usage: context.py add-finding <agent> '<json>'", file=sys.stderr)
            sys.exit(1)
        cmd_add_finding(sys.argv[2], sys.argv[3])
    elif command == "merge-finding":
        kwargs = {}
        i = 2
        while i < len(sys.argv):
            if sys.argv[i].startswith("--"):
                key = sys.argv[i][2:].replace("-", "_")
                i += 1
                if i < len(sys.argv):
                    kwargs[key] = sys.argv[i]
            i += 1
        agent = kwargs.pop("agent", None)
        if not agent:
            print("Error: --agent is required for merge-finding", file=sys.stderr)
            sys.exit(1)
        cmd_merge_finding(agent, **kwargs)
    elif command == "add-artifact":
        if len(sys.argv) < 4:
            print("Usage: context.py add-artifact <category> <value>", file=sys.stderr)
            sys.exit(1)
        cmd_add_artifact(sys.argv[2], sys.argv[3])
    elif command == "add-decision":
        if len(sys.argv) < 4:
            print("Usage: context.py add-decision <category> '<json>'", file=sys.stderr)
            sys.exit(1)
        cmd_add_decision(sys.argv[2], sys.argv[3])
    elif command == "add-trace-step":
        if len(sys.argv) < 3:
            print("Usage: context.py add-trace-step '<json>'", file=sys.stderr)
            sys.exit(1)
        cmd_add_trace_step(sys.argv[2])
    elif command == "add-cross-reference":
        if len(sys.argv) < 6:
            print("Usage: context.py add-cross-reference <from_agent> <to_agent> <from_id> <to_id> <relation>", file=sys.stderr)
            sys.exit(1)
        cmd_add_cross_reference(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    elif command == "set-session":
        kwargs = {}
        i = 2
        while i < len(sys.argv):
            if sys.argv[i].startswith("--"):
                key = sys.argv[i][2:].replace("-", "_")
                i += 1
                if i < len(sys.argv):
                    kwargs[key] = sys.argv[i]
            i += 1
        cmd_set_session(**kwargs)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print_usage()

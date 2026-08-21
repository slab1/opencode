#!/usr/bin/env python3
"""Lane ledger + checkpoint system for interrupted-agent recovery.

Purpose: when a subagent dispatch is interrupted (user message mid-dispatch,
tool-call cancellation, memory pressure), the session ID and gathered context
are normally lost. This module gives the orchestrator a durable record:

  - LEDGER  (~/.config/opencode/shared/lane_ledger.json)
      intent written BEFORE dispatch (lane, agent, prompt_hash, dispatched_at)
      task_id bound AFTER the task tool returns an ID
      lets a resume pass re-dispatch a lane whose ID was never captured

  - CHECKPOINT (/tmp/opencode/lanes/<lane>.json)
      per-lane progress written BY the lane agent as it works
      resume = fresh dispatch that reads the checkpoint and continues
      from `phase` instead of re-discovering

Usage (orchestrator):
    from lane_ledger import open_lane, bind_lane, lane_status, lanes_summary
    open_lane("fixer-build", "fixer", prompt_hash="abc123")
    ... dispatch ...
    bind_lane("fixer-build", "ses_xxx")

Usage (lane agent, via its prompt):
    python3 /root/.config/opencode/shared/lane_ledger.py checkpoint-save fixer-build \
        --phase vite-config --files vite.config.ts --remaining "tsconfig, CI" \
        --context "charts chunk in entry path; vendor chunk orphaned"
    python3 /root/.config/opencode/shared/lane_ledger.py checkpoint-load fixer-build
"""

import argparse
import hashlib
import json
import os
import sys
import time

LEDGER_PATH = os.path.expanduser("~/.config/opencode/shared/lane_ledger.json")
CHECKPOINT_DIR = "/tmp/opencode/lanes"


def _read_ledger():
    try:
        with open(LEDGER_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"lanes": {}}


def _write_ledger(data):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    tmp = LEDGER_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, LEDGER_PATH)


def open_lane(lane, agent, prompt_hash=None, note=""):
    """Record dispatch intent BEFORE calling task(). Returns the lane record."""
    data = _read_ledger()
    rec = data["lanes"].setdefault(lane, {})
    rec.update({
        "agent": agent,
        "prompt_hash": prompt_hash or hashlib.sha256(lane.encode()).hexdigest()[:12],
        "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_id": rec.get("task_id"),  # preserve if already bound
        "status": "dispatched",
        "note": note,
    })
    _write_ledger(data)
    return rec


def bind_lane(lane, task_id):
    """Bind the task tool's returned session ID to a lane."""
    data = _read_ledger()
    rec = data["lanes"].setdefault(lane, {})
    rec["task_id"] = task_id
    rec["bound_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec["status"] = "running"
    _write_ledger(data)
    return rec


def complete_lane(lane, outcome="completed"):
    data = _read_ledger()
    rec = data["lanes"].setdefault(lane, {})
    rec["status"] = outcome
    rec["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_ledger(data)
    return rec


def lane_status(lane):
    data = _read_ledger()
    return data["lanes"].get(lane, {})


def lanes_summary():
    data = _read_ledger()
    return data["lanes"]


def checkpoint_save(lane, phase, files=None, verification=None, remaining=None, context=""):
    """Lane agents call this as they progress. Resume reads it and continues."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = os.path.join(CHECKPOINT_DIR, lane + ".json")
    cp = {
        "lane": lane,
        "phase": phase,
        "files_changed": files or [],
        "verification": verification or {},
        "remaining": remaining or [],
        "gathered_context": context,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cp, f, indent=1)
    os.replace(tmp, path)
    return path


def checkpoint_load(lane):
    path = os.path.join(CHECKPOINT_DIR, lane + ".json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _cli():
    ap = argparse.ArgumentParser(description="Lane ledger + checkpoint CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("open", help="record dispatch intent")
    p.add_argument("lane")
    p.add_argument("--agent", default="fixer")
    p.add_argument("--prompt-hash", default="")
    p.add_argument("--note", default="")

    p = sub.add_parser("bind", help="bind task_id to lane")
    p.add_argument("lane")
    p.add_argument("task_id")

    p = sub.add_parser("complete", help="mark lane completed")
    p.add_argument("lane")
    p.add_argument("--outcome", default="completed")

    p = sub.add_parser("status", help="show one lane")
    p.add_argument("lane")

    p = sub.add_parser("summary", help="show all lanes")

    p = sub.add_parser("checkpoint-save", help="lane agent progress save")
    p.add_argument("lane")
    p.add_argument("--phase", default="")
    p.add_argument("--files", default="")
    p.add_argument("--verification", default="")
    p.add_argument("--remaining", default="")
    p.add_argument("--context", default="")

    p = sub.add_parser("checkpoint-load", help="lane agent resume read")
    p.add_argument("lane")

    args = ap.parse_args()

    if args.cmd == "open":
        print(json.dumps(open_lane(args.lane, args.agent, args.prompt_hash, args.note)))
    elif args.cmd == "bind":
        print(json.dumps(bind_lane(args.lane, args.task_id)))
    elif args.cmd == "complete":
        print(json.dumps(complete_lane(args.lane, args.outcome)))
    elif args.cmd == "status":
        print(json.dumps(lane_status(args.lane)))
    elif args.cmd == "summary":
        print(json.dumps(lanes_summary(), indent=1))
    elif args.cmd == "checkpoint-save":
        print(checkpoint_save(
            args.lane, args.phase,
            files=[f.strip() for f in args.files.split(",") if f.strip()],
            verification=json.loads(args.verification) if args.verification else {},
            remaining=[r.strip() for r in args.remaining.split(",") if r.strip()],
            context=args.context,
        ))
    elif args.cmd == "checkpoint-load":
        print(json.dumps(checkpoint_load(args.lane)))


if __name__ == "__main__":
    _cli()
"""
Performance tracking for evaluated agents.
Logs task outcomes for cross-agent analysis.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _get_base_dir() -> Path:
    env_home = os.environ.get("AGENT_EVAL_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".config" / "opencode"


SHARED_DIR = _get_base_dir() / "shared"
PERFORMANCE_FILE = SHARED_DIR / "performance.json"
CONTEXT_FILE = SHARED_DIR / "context.json"


class PerformanceTracker:
    """Logs and reports on agent task outcomes."""

    def __init__(self, storage_path=None):
        self.storage_path = Path(storage_path) if storage_path else PERFORMANCE_FILE

    def log(self, agent, task, outcome, duration_s=0, error=None, context=None):
        """Record a task outcome."""
        entry = {
            "agent": agent,
            "task": task,
            "outcome": outcome,
            "duration_s": duration_s,
            "error": error,
            "config_snapshot": None,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "timestamp_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data = self._load()
        data.append(entry)
        self._save(data)
        return entry

    def _load(self):
        if self.storage_path.exists():
            try:
                return json.loads(self.storage_path.read_text())
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self, data):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(data, indent=2))

    def report(self, agent=None):
        """Aggregate performance data."""
        data = self._load()
        if agent:
            data = [e for e in data if e.get("agent") == agent]

        if not data:
            return {"status": "ok", "total_entries": 0, "agents": []}

        agents = {}
        for entry in data:
            a = entry.get("agent", "unknown")
            if a not in agents:
                agents[a] = {
                    "total": 0, "success": 0, "failure": 0, "partial": 0,
                    "errors": [], "durations": [],
                }
            agents[a]["total"] += 1
            outcome = entry.get("outcome", "unknown")
            if outcome == "success":
                agents[a]["success"] += 1
            elif outcome == "failure":
                agents[a]["failure"] += 1
            elif outcome == "partial":
                agents[a]["partial"] += 1
            agents[a]["durations"].append(entry.get("duration_s", 0))
            if entry.get("error"):
                agents[a]["errors"].append(entry["error"])

        result = []
        for agent_name in sorted(agents):
            stats = agents[agent_name]
            total = stats["total"]
            success_count = stats["success"]
            avg_dur = (
                round(sum(stats["durations"]) / len(stats["durations"]), 1)
                if stats["durations"]
                else 0
            )
            last_entries = [e for e in data if e.get("agent") == agent_name]
            last = last_entries[-1] if last_entries else {}
            result.append({
                "agent": agent_name,
                "total": total,
                "success": success_count,
                "failure": stats["failure"],
                "partial": stats["partial"],
                "avg_duration_s": avg_dur,
                "recent_errors": stats["errors"][-3:] if stats["errors"] else [],
                "last_outcome": last.get("outcome"),
                "last_task": last.get("task"),
                "success_rate": round((success_count / total) * 100, 1) if total > 0 else 0,
            })

        return {
            "status": "ok",
            "total_entries": len(data),
            "agents": result,
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

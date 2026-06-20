"""
Agent Spawning System — dynamically creates transient multi-agent teams for complex tasks.

When a task requires multiple specialized agents, the spawner creates an ephemeral
team with shared context, tracks progress, and handles cleanup.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path.home() / ".config" / "opencode"
SPAWNED_DIR = BASE_DIR / "shared" / "spawned"

TEAM_TEMPLATES = {
    "bug-fix": {
        "roles": ["debug", "build", "test"],
        "description": "Debug root cause → Build fix → Write regression test",
        "min_complexity": "simple",
    },
    "feature": {
        "roles": ["architect", "build", "review", "test"],
        "description": "Design architecture → Implement → Review → Test",
        "min_complexity": "moderate",
    },
    "research": {
        "roles": ["explore", "pioneer", "general"],
        "description": "Explore codebase → Research options → Synthesize findings",
        "min_complexity": "simple",
    },
    "content": {
        "roles": ["content-creator", "media-agent", "review"],
        "description": "Generate content → Optimize media → Review quality",
        "min_complexity": "simple",
    },
    "full-audit": {
        "roles": ["security", "review", "meta-agent", "explore"],
        "description": "Security audit → Code review → Performance analysis → Explore dependencies",
        "min_complexity": "complex",
    },
    "general": {
        "roles": ["general", "explore", "build"],
        "description": "General-purpose team: Investigate → Build → Verify",
        "min_complexity": "simple",
    },
    "publish": {
        "roles": ["content-creator", "media-agent", "platform-manager"],
        "description": "Generate content → Optimize media → Schedule post",
        "min_complexity": "moderate",
    },
}

COMPLEXITY_LEVELS = {"simple": 0, "moderate": 1, "complex": 2}


def _ensure_spawned_dir():
    SPAWNED_DIR.mkdir(parents=True, exist_ok=True)


def _team_path(team_id: str) -> Path:
    return SPAWNED_DIR / f"{team_id}.json"


def spawn_team(task: dict) -> dict:
    """Create a transient agent team for a complex task.

    Args:
        task: dict with keys:
            - description: str — what needs to be done
            - complexity: str — "simple" | "moderate" | "complex"
            - template: str — optional team template name (default: auto-pick)
            - roles: list — optional override of agent roles

    Returns:
        dict with team_id, members, shared_context_path
    """
    _ensure_spawned_dir()
    team_id = f"team_{uuid.uuid4().hex[:12]}"
    complexity = task.get("complexity", "moderate")
    template_name = task.get("template")

    # Pick template
    if template_name and template_name in TEAM_TEMPLATES:
        template = TEAM_TEMPLATES[template_name]
    elif task.get("roles"):
        template = {"roles": task["roles"], "description": "Custom team"}
    else:
        # Auto-pick based on task description
        desc_lower = task.get("description", "").lower()
        template = TEAM_TEMPLATES["general"]
        for key, tmpl in TEAM_TEMPLATES.items():
            if key in desc_lower:
                template = tmpl
                break
        if not template:
            template = TEAM_TEMPLATES["feature"]

    # Validate complexity
    min_cl = COMPLEXITY_LEVELS.get(template.get("min_complexity", "simple"), 0)
    task_cl = COMPLEXITY_LEVELS.get(complexity, 0)
    if task_cl < min_cl:
        complexity = template.get("min_complexity", "simple")

    members = []
    for i, role in enumerate(template["roles"]):
        members.append({
            "id": f"{team_id}_{role}",
            "role": role,
            "status": "pending",
            "prompt_template": f"Execute role '{role}' for task: {task.get('description', '')}",
        })

    team_data = {
        "team_id": team_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "status": "active",
        "task": task,
        "template": template_name or "auto",
        "complexity": complexity,
        "members": members,
        "findings": [],
        "summaries": {},
    }

    path = _team_path(team_id)
    path.write_text(json.dumps(team_data, indent=2))

    return {
        "status": "ok",
        "team_id": team_id,
        "members": [m["role"] for m in members],
        "shared_context_path": str(path),
        "template": template_name or "auto",
        "description": template.get("description", ""),
    }


class SpawnedTeam:
    """Interface for interacting with a spawned team."""

    def __init__(self, team_id: str):
        self.team_id = team_id
        self.path = _team_path(team_id)
        self._data = None
        self._load()

    def _load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"Team {self.team_id} not found")
        self._data = json.loads(self.path.read_text())

    def _save(self):
        self._data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.path.write_text(json.dumps(self._data, indent=2))

    @property
    def data(self) -> dict:
        if self._data is None:
            self._load()
        return self._data

    def get_member(self, role: str) -> Optional[dict]:
        for m in self.data.get("members", []):
            if m["role"] == role:
                return m
        return None

    def update_status(self, status: str):
        self.data["status"] = status
        self._save()

    def set_member_status(self, role: str, status: str):
        for m in self.data.get("members", []):
            if m["role"] == role:
                m["status"] = status
        self._save()

    def report_finding(self, member_role: str, finding: dict):
        self.data.setdefault("findings", []).append({
            "member": member_role,
            "finding": finding,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        self._save()

    def add_summary(self, member_role: str, summary: str):
        self.data["summaries"][member_role] = summary
        self._save()

    def _parse_created(self) -> datetime:
        created_str = self.data.get("created_at", datetime.utcnow().isoformat() + "Z")
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        return created.replace(tzinfo=None)

    def summarize(self) -> dict:
        members_status = [
            {"role": m["role"], "status": m["status"]}
            for m in self.data.get("members", [])
        ]
        now = datetime.utcnow()
        created = self._parse_created()
        age_min = round((now - created).total_seconds() / 60, 1)
        return {
            "team_id": self.team_id,
            "status": self.data.get("status"),
            "task": self.data.get("task", {}).get("description", ""),
            "members": members_status,
            "findings_count": len(self.data.get("findings", [])),
            "summaries_count": len(self.data.get("summaries", {})),
            "created_at": self.data.get("created_at"),
            "age_minutes": age_min,
        }

    def cleanup(self):
        if self.path.exists():
            self.path.unlink()
        return {"status": "ok", "team_id": self.team_id}


def spawn_subagent(member_info: dict, task_context: str) -> dict:
    """Generate a subagent task call configuration.

    Creates the prompt template for dispatching to a specific agent role
    in the team. The orchestrator uses this to actually invoke the agent.
    """
    role = member_info.get("role", "general")
    prompt = member_info.get("prompt_template", "")

    return {
        "subagent_type": role,
        "prompt": f"""You are part of a multi-agent team (team context below).
Your role: {role}

Task Context:
{task_context}

{prompt}

Coordinate with other team members through the shared context.
Report your findings back to the team lead when complete.
""",
    }


def list_active_teams() -> dict:
    """List all currently spawned teams."""
    _ensure_spawned_dir()
    teams = []
    now = datetime.utcnow()
    for f in sorted(SPAWNED_DIR.glob("team_*.json")):
        try:
            data = json.loads(f.read_text())
            created_str = data.get("created_at", now.isoformat() + "Z")
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            created_naive = created.replace(tzinfo=None)
            age = now - created_naive
            teams.append({
                "team_id": data.get("team_id"),
                "status": data.get("status"),
                "task": data.get("task", {}).get("description", "")[:100],
                "members": [m["role"] for m in data.get("members", [])],
                "age": str(age).split(".")[0],
            })
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    return {
        "status": "ok",
        "active_teams": len(teams),
        "teams": teams,
    }


def cleanup_stale_teams(max_age_hours: int = 24) -> dict:
    """Remove teams older than threshold."""
    _ensure_spawned_dir()
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    removed = 0

    for f in SPAWNED_DIR.glob("team_*.json"):
        try:
            data = json.loads(f.read_text())
            created_str = data.get("created_at", datetime.utcnow().isoformat() + "Z")
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created.replace(tzinfo=None) < cutoff:
                f.unlink()
                removed += 1
        except (json.JSONDecodeError, KeyError, ValueError):
            f.unlink()
            removed += 1

    return {
        "status": "ok",
        "removed": removed,
        "max_age_hours": max_age_hours,
    }

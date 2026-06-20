"""
Delegation Pattern Miner — learns optimal agent delegation from historical data.

Reads performance.json and context.json to extract patterns about which agents
excel at which task types. Provides recommendation engine for optimal routing.
"""

import json
import re
from pathlib import Path
from typing import Optional

BASE_DIR = Path.home() / ".config" / "opencode"

PERFORMANCE_FILE = BASE_DIR / "shared" / "performance.json"
CONTEXT_FILE = BASE_DIR / "shared" / "context.json"
GRAPH_FILE = BASE_DIR / "knowledge-graph" / "graph.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _load_agent_capabilities() -> dict:
    """Load agent capability keywords from knowledge graph."""
    graph = _load_json(GRAPH_FILE)
    agents = graph.get("agents", {})
    result = {}
    for name, info in agents.items():
        caps = info.get("capabilities", [])
        strengths = info.get("strengths", [])
        result[name] = {
            "keywords": caps + strengths,
            "strengths": strengths,
        }
    return result


def mine_delegation_patterns() -> dict:
    """Analyze performance data to extract delegation patterns."""
    perf = _load_json(PERFORMANCE_FILE)
    entries = perf if isinstance(perf, list) else perf.get("agents", [])

    # Aggregate per agent
    agents = {}
    for entry in entries if isinstance(perf, list) else []:
        agent = entry.get("agent", "unknown")
        if agent not in agents:
            agents[agent] = {"total": 0, "success": 0, "failure": 0,
                             "partial": 0, "durations": [], "tasks": []}
        agents[agent]["total"] += 1
        outcome = entry.get("outcome", "unknown")
        if outcome == "success":
            agents[agent]["success"] += 1
        elif outcome == "failure":
            agents[agent]["failure"] += 1
        elif outcome == "partial":
            agents[agent]["partial"] += 1
        agents[agent]["durations"].append(entry.get("duration_s", 0))
        agents[agent]["tasks"].append(entry.get("task", ""))

    # Compute stats and classify task types
    result = {}
    for agent, stats in agents.items():
        total = stats["total"]
        success_rate = round(stats["success"] / total, 3) if total > 0 else 0
        avg_dur = round(sum(stats["durations"]) / len(stats["durations"]), 1) if stats["durations"] else 0

        # Classify task types from task descriptions
        task_types = {}
        for task in stats["tasks"]:
            ttype = _classify_task(task)
            task_types.setdefault(ttype, {"count": 0, "success": 0})
            task_types[ttype]["count"] += 1

        result[agent] = {
            "total_tasks": total,
            "success_rate": success_rate,
            "success_count": stats["success"],
            "failure_count": stats["failure"],
            "partial_count": stats["partial"],
            "avg_duration_s": avg_dur,
            "task_types": task_types,
            "verdict": "excellent" if success_rate >= 0.8 else (
                "good" if success_rate >= 0.6 else "needs_improvement"),
        }

    return {
        "status": "ok",
        "total_agents": len(result),
        "agents": result,
        "as_of": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


def _classify_task(task: str) -> str:
    """Classify a task description into a type."""
    task_lower = task.lower()
    if any(w in task_lower for w in ["bug", "fix", "error", "crash", "issue"]):
        return "bug_fix"
    if any(w in task_lower for w in ["feature", "implement", "create", "add"]):
        return "feature"
    if any(w in task_lower for w in ["audit", "review", "check", "inspect"]):
        return "audit"
    if any(w in task_lower for w in ["test", "coverage", "regression"]):
        return "testing"
    if any(w in task_lower for w in ["post", "publish", "schedule", "content"]):
        return "publishing"
    if any(w in task_lower for w in ["research", "search", "find", "explore"]):
        return "research"
    if any(w in task_lower for w in ["docs", "documentation", "readme"]):
        return "documentation"
    if any(w in task_lower for w in ["deploy", "ci", "pipeline", "release"]):
        return "devops"
    if any(w in task_lower for w in ["refactor", "clean", "optimize"]):
        return "refactoring"
    return "general"


def _get_agent_task_map() -> dict:
    """Hardcoded agent→best_task mapping for recommendation engine.

    This improves on pure keyword matching by using domain knowledge
    about which agents handle which task types best.
    """
    return {
        "build": ["feature", "bug_fix", "refactoring"],
        "debug": ["bug_fix"],
        "test": ["testing"],
        "architect": ["feature"],
        "explore": ["research", "audit"],
        "security": ["audit"],
        "review": ["audit", "refactoring"],
        "general": ["research", "general"],
        "plan": ["feature"],
        "docs": ["documentation"],
        "meta-agent": ["audit"],
        "platform-manager": ["publishing"],
        "content-creator": ["publishing"],
        "media-agent": ["publishing"],
        "pioneer": ["research"],
    }


def recommend_agent(task_description: str, top_n: int = 3) -> dict:
    """Recommend the best agent for a task based on historical patterns."""
    caps = _load_agent_capabilities()
    patterns = mine_delegation_patterns()
    agents = patterns.get("agents", {})
    task_map = _get_agent_task_map()

    task_lower = task_description.lower()
    task_type = _classify_task(task_description)

    # Score each agent
    scores = {}
    for agent_name, info in caps.items():
        score = 0.0
        kw = info.get("keywords", [])

        # Task-type match (highest weight)
        best_for = task_map.get(agent_name, [])
        if task_type in best_for:
            score += 1.0
        elif any(t in task_type for t in best_for):
            score += 0.5

        # Agent name in description (strong signal)
        if agent_name.replace("-", " ") in task_lower:
            score += 0.8

        # Keyword match against task description
        matches = sum(1 for k in kw if k.lower() in task_lower)
        if matches > 0:
            score += matches * 0.2

        # Strength match
        strengths = info.get("strengths", [])
        strength_matches = sum(1 for s in strengths if s.lower() in task_lower)
        if strength_matches > 0:
            score += strength_matches * 0.3

        # Historical performance bonus
        hist = agents.get(agent_name, {})
        if hist.get("task_types", {}).get(task_type, {}).get("count", 0) > 0:
            score += 0.2  # Has done this before

        if score > 0:
            scores[agent_name] = round(score, 2)

    # If no keyword matches, use task_map as fallback
    if not scores:
        for agent_name, task_types in task_map.items():
            if task_type in task_types:
                scores[agent_name] = round(1.0 - (list(task_map.keys()).index(agent_name) * 0.01), 2)

    # Rank
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return {
        "status": "ok",
        "task": task_description,
        "task_type": task_type,
        "recommendations": [
            {"agent": name, "confidence": score}
            for name, score in ranked[:top_n]
        ],
        "alternative_agents": [
            {"agent": name, "confidence": score}
            for name, score in ranked[top_n:]
        ],
    }


def analyze_delegation_trends() -> dict:
    """Analyze delegation trends — improving/declining agents, chains, bottlenecks."""
    perf = _load_json(PERFORMANCE_FILE)
    entries = perf if isinstance(perf, list) else []

    # Time-based success rates (first half vs second half of entries)
    mid = len(entries) // 2
    first_half = entries[:mid]
    second_half = entries[mid:]

    def success_rate_for(entries_slice):
        rates = {}
        for e in entries_slice:
            a = e.get("agent", "unknown")
            rates.setdefault(a, {"total": 0, "success": 0})
            rates[a]["total"] += 1
            rates[a]["success"] += 1 if e.get("outcome") == "success" else 0
        return {
            a: round(r["success"] / r["total"], 2) if r["total"] > 0 else 0
            for a, r in rates.items()
        }

    first_rates = success_rate_for(first_half)
    second_rates = success_rate_for(second_half)

    trends = {}
    all_agents = set(list(first_rates.keys()) + list(second_rates.keys()))
    for agent in sorted(all_agents):
        fr = first_rates.get(agent, 0)
        sr = second_rates.get(agent, 0)
        delta = round(sr - fr, 2)
        trends[agent] = {
            "first_half_rate": fr,
            "second_half_rate": sr,
            "delta": delta,
            "trend": "improving" if delta > 0.05 else (
                "declining" if delta < -0.05 else "stable"),
        }

    # Most delegated-to agents
    delegation_counts = {}
    for e in entries:
        agent = e.get("agent", "unknown")
        delegation_counts[agent] = delegation_counts.get(agent, 0) + 1
    most_delegated = sorted(delegation_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "status": "ok",
        "total_entries": len(entries),
        "trends": trends,
        "most_delegated": [
            {"agent": a, "times": c} for a, c in most_delegated
        ],
    }


def run_cli(argv: list = None):
    """CLI entry point for delegation pattern commands."""
    import argparse as ap
    p = ap.ArgumentParser(prog="patterns", description="Delegation pattern mining")
    p.add_argument("--recommend", "-r", type=str, help="Recommend agent for task")
    p.add_argument("--trends", "-t", action="store_true", help="Show trends")
    p.add_argument("--heatmap", "-m", action="store_true", help="Show heatmap")
    args = p.parse_args(argv if argv else [])

    if args.recommend:
        print(json.dumps(recommend_agent(args.recommend), indent=2))
    elif args.trends:
        print(json.dumps(analyze_delegation_trends(), indent=2))
    elif args.heatmap:
        print(json.dumps(delegation_heatmap(), indent=2))
    else:
        print(json.dumps(mine_delegation_patterns(), indent=2))


def delegation_heatmap() -> dict:
    """Generate agent × task_type matrix with success rates for visualization."""
    patterns = mine_delegation_patterns()
    agents_data = patterns.get("agents", {})

    task_types = set()
    for info in agents_data.values():
        task_types.update(info.get("task_types", {}).keys())
    task_types = sorted(task_types)

    matrix = {}
    for agent, info in sorted(agents_data.items()):
        row = {}
        for tt in task_types:
            tt_data = info.get("task_types", {}).get(tt, {})
            count = tt_data.get("count", 0)
            row[tt] = {"count": count, "has_done": count > 0}
        matrix[agent] = row

    return {
        "status": "ok",
        "task_types": list(task_types),
        "agents": list(sorted(agents_data.keys())),
        "matrix": matrix,
        "agent_summaries": {
            a: {"total": v["total_tasks"], "success_rate": v["success_rate"],
                "verdict": v["verdict"]}
            for a, v in agents_data.items()
        },
    }

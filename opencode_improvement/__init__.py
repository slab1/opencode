"""
OpenCode Self-Improvement Engine (opencode_improvement)

A meta-cognitive module that audits agent configs, tracks performance,
suggests improvements, and drives cross-domain capability transfers.
"""

from pathlib import Path

from opencode_improvement.track import PerformanceTracker

__all__ = [
    "PerformanceTracker",
    "audit_agents",
    "generate_report",
    "suggest_improvements",
]

AGENTS_DIR = Path.home() / ".config" / "opencode" / "agents"
SHARED_DIR = Path.home() / ".config" / "opencode" / "shared"
CONTEXT_FILE = SHARED_DIR / "context.json"

# Sections every agent should have
REQUIRED_STRUCTURE = [
    "frontmatter_has_description",
    "frontmatter_has_mode",
    "frontmatter_has_permission",
    "has_role",
    "has_capabilities",
    "has_shared_context",
    "has_context_section",
    "has_rules",
    "has_workflow",
    "has_task_tracking",
]

# Structural sections that must appear in agent .md files
REQUIRED_TAGS = [
    ("<role>", "has_role"),
    ("<capabilities>", "has_capabilities"),
    ("<shared-context>", "has_shared_context"),
]


def audit_agents(agent_name=None):
    """Scan all agent .md files and report structural completeness."""
    if not AGENTS_DIR.exists():
        return {"status": "error", "message": f"Agents directory not found: {AGENTS_DIR}"}

    md_files = sorted(AGENTS_DIR.glob("*.md"))
    results = []

    for fpath in md_files:
        name = fpath.stem
        if agent_name and name != agent_name:
            continue

        text = fpath.read_text(encoding="utf-8")
        info = {
            "filename": fpath.name,
            "size_bytes": len(text),
            "line_count": text.count("\n") + 1,
        }

        # --- Frontmatter (YAML between --- markers) ---
        frontmatter = {}
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                for line in text[3:end].strip().split("\n"):
                    if ":" in line:
                        key, _, val = line.partition(":")
                        frontmatter[key.strip()] = val.strip()
            else:
                frontmatter = None  # malformed

        info["has_frontmatter"] = frontmatter is not None
        info["frontmatter_has_description"] = "description" in frontmatter if frontmatter else False
        info["frontmatter_has_mode"] = "mode" in frontmatter if frontmatter else False
        info["frontmatter_has_permission"] = "permission" in frontmatter if frontmatter else False

        # --- Structural sections ---
        for tag, key in REQUIRED_TAGS:
            info[key] = tag in text

        # Check for <context> section (used by meta-agent to know agent's invocation scope)
        info["has_context_section"] = "<context>" in text

        # Check for <rules>
        info["has_rules"] = "<rules>" in text

        # Check for <workflow>
        info["has_workflow"] = "<workflow>" in text

        # Check for <task-tracking>
        info["has_task_tracking"] = "<task-tracking>" in text

        # Check for <memory>
        info["has_memory"] = "<memory>" in text

        # Count capability sections (### heading lines under <capabilities>)
        in_caps = False
        cap_count = 0
        for line in text.split("\n"):
            if "<capabilities>" in line:
                in_caps = True
                continue
            if in_caps and line.startswith("##"):
                in_caps = False
            if in_caps and line.startswith("### "):
                cap_count += 1
        info["capability_sections"] = cap_count

        # Overall score
        info["structure_complete"] = all(
            info.get(s) for s in REQUIRED_STRUCTURE
        )

        results.append(info)

    return {
        "status": "ok",
        "total_agents": len(results),
        "agents": results,
    }


def generate_report(agent_name=None):
    """Pull performance data from the tracker."""
    tracker = PerformanceTracker()
    return tracker.report(agent_name)


def suggest_improvements(agent_name):
    """Analyze an agent and suggest structural improvements."""
    audit = audit_agents(agent_name)
    if audit["status"] != "ok" or not audit["agents"]:
        return {"status": "error", "message": f"Agent '{agent_name}' not found"}

    agent = audit["agents"][0]
    missing = []
    suggestions = []

    # Check frontmatter
    if not agent["frontmatter_has_description"]:
        missing.append("description in frontmatter")
        suggestions.append({
            "priority": "high",
            "section": "frontmatter",
            "detail": "Add 'description:' field to frontmatter",
        })

    if not agent["frontmatter_has_mode"]:
        missing.append("mode in frontmatter")
        suggestions.append({
            "priority": "high",
            "section": "frontmatter",
            "detail": "Add 'mode: primary' or 'mode: subagent' to frontmatter",
        })

    if not agent["frontmatter_has_permission"]:
        missing.append("permission in frontmatter")
        suggestions.append({
            "priority": "high",
            "section": "frontmatter",
            "detail": "Add 'permission:' section to frontmatter with tool access rules",
        })

    # Check structural tags
    for tag, key in REQUIRED_TAGS:
        if not agent.get(key):
            missing.append(tag)
            suggestions.append({
                "priority": "high",
                "section": tag.strip("<>"),
                "detail": f"Add missing <{tag.strip('<>')}> section to agent config",
            })

    if not agent.get("has_context_section"):
        missing.append("<context>")
        suggestions.append({
            "priority": "high",
            "section": "context",
            "detail": "Add <context> section clarifying when and how this agent should be invoked",
        })

    if not agent.get("has_rules"):
        missing.append("<rules>")
        suggestions.append({
            "priority": "medium",
            "section": "rules",
            "detail": "Consider adding <rules> section with operational guardrails",
        })

    if not agent.get("has_workflow"):
        missing.append("<workflow>")
        suggestions.append({
            "priority": "medium",
            "section": "workflow",
            "detail": "Consider adding <workflow> section with step-by-step methodology",
        })

    if not agent.get("has_task_tracking"):
        missing.append("<task-tracking>")
        suggestions.append({
            "priority": "medium",
            "section": "task-tracking",
            "detail": "Consider adding <task-tracking> section for logging outcomes",
        })

    # Capability count
    if agent.get("capability_sections", 0) < 3:
        suggestions.append({
            "priority": "low",
            "section": "capabilities",
            "detail": f"Only {agent['capability_sections']} capability sections. Consider adding more specialized capabilities (target 5+)",
        })

    return {
        "status": "ok",
        "agent": agent_name,
        "file": agent["filename"],
        "size_bytes": agent["size_bytes"],
        "capability_sections": agent["capability_sections"],
        "structure_complete": agent["structure_complete"],
        "missing_sections": missing,
        "improvements": suggestions,
    }

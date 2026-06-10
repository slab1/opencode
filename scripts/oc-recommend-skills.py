#!/usr/bin/env python3
"""oc-recommend-skills - Recommend skills and agent for a given task description.

Usage:
    oc-recommend-skills "<task description>"
    oc-recommend-skills --list                    # list all task categories
    oc-recommend-skills --agent <agent_name>      # show skills for an agent
    oc-recommend-skills --category <category>     # show skills for a category

The script uses keyword matching against the task_skill_map. Higher match scores
indicate stronger recommendations.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SHARED_DIR = Path.home() / ".config" / "opencode" / "shared"
TASK_SKILL_MAP_PATH = SHARED_DIR / "task_skill_map.json"
SKILLS_CATALOG_PATH = SHARED_DIR / "context.json"


def load_task_skill_map():
    if not TASK_SKILL_MAP_PATH.exists():
        print(f"ERROR: {TASK_SKILL_MAP_PATH} not found", file=sys.stderr)
        sys.exit(1)
    return json.loads(TASK_SKILL_MAP_PATH.read_text())


def load_skills_catalog():
    if not SKILLS_CATALOG_PATH.exists():
        return None
    ctx = json.loads(SKILLS_CATALOG_PATH.read_text())
    return ctx.get("skills_catalog", {})


def recommend(task_description, task_skill_map, skills_catalog=None):
    """Return list of (category, score, agent, skills) sorted by score."""
    task_lower = task_description.lower()
    # Use word boundary matching for short keywords to avoid partial matches
    matches = []
    for category, info in task_skill_map.items():
        score = 0
        matched_keywords = []
        for kw in info.get("keywords", []):
            # For short keywords (<=4 chars), use word boundary
            if len(kw) <= 4:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, task_lower):
                    score += len(kw.split()) + 1  # bonus for short keyword match
                    matched_keywords.append(kw)
            else:
                if kw in task_lower:
                    score += len(kw.split())
                    matched_keywords.append(kw)
        if score > 0:
            matches.append({
                "category": category,
                "score": score,
                "matched_keywords": matched_keywords,
                "agent": info.get("primary_agent", "?"),
                "skills": info.get("skills", []),
            })
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def recommend_for_agent(agent_name, task_skill_map, skills_catalog):
    """Show all skills recommended for an agent across all task categories."""
    if not skills_catalog or "agent_skill_map" not in skills_catalog:
        return []
    return skills_catalog["agent_skill_map"].get(agent_name, [])


def print_recommendation(task, matches, skills_catalog):
    print(f"Task: {task}")
    print()
    if not matches:
        print("No matches found. Try different keywords, or check `oc-recommend-skills --list`")
        return
    print("Recommendations (ranked by relevance):")
    print()
    for i, m in enumerate(matches[:5], 1):
        print(f"  #{i}  {m['category']} (score: {m['score']})")
        print(f"      Agent:  {m['agent']}")
        print(f"      Match:  {', '.join(m['matched_keywords'])}")
        if m["skills"]:
            print(f"      Skills: {', '.join(m['skills'])}")
        # Enrich with skill purpose if catalog available
        if skills_catalog and skills_catalog.get("skills"):
            for s in m["skills"][:3]:
                purpose = skills_catalog["skills"].get(s, {}).get("purpose", "")
                if purpose:
                    print(f"        - {s}: {purpose}")
        print()


def print_list_categories(task_skill_map):
    print("Available task categories:")
    print()
    for cat, info in sorted(task_skill_map.items()):
        print(f"  {cat}")
        print(f"    Keywords: {', '.join(info.get('keywords', []))}")
        print(f"    Agent:    {info.get('primary_agent', '?')}")
        print(f"    Skills:   {', '.join(info.get('skills', []))}")
        print()


def print_agent_skills(agent_name, skills_catalog):
    if not skills_catalog:
        print("Skills catalog not loaded")
        return
    skills = recommend_for_agent(agent_name, None, skills_catalog)
    if not skills:
        print(f"Agent '{agent_name}' has no skills in the catalog")
        return
    print(f"Skills for agent '{agent_name}':")
    for s in skills:
        purpose = skills_catalog.get("skills", {}).get(s, {}).get("purpose", "")
        print(f"  - {s:30s} {purpose}")


def main():
    parser = argparse.ArgumentParser(
        description="Recommend skills and agents for a task description"
    )
    parser.add_argument("task", nargs="?", help="Task description to analyze")
    parser.add_argument("--list", action="store_true", help="List all task categories")
    parser.add_argument("--agent", help="Show skills for a specific agent")
    parser.add_argument("--category", help="Show skills for a specific category")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    task_skill_map = load_task_skill_map()
    skills_catalog = load_skills_catalog()

    if args.list:
        if args.json:
            print(json.dumps(task_skill_map, indent=2))
        else:
            print_list_categories(task_skill_map)
        return

    if args.agent:
        if args.json:
            print(json.dumps({
                "agent": args.agent,
                "skills": recommend_for_agent(args.agent, task_skill_map, skills_catalog)
            }, indent=2))
        else:
            print_agent_skills(args.agent, skills_catalog)
        return

    if args.category:
        cat = task_skill_map.get(args.category)
        if not cat:
            print(f"Unknown category: {args.category}", file=sys.stderr)
            print(f"Available: {', '.join(sorted(task_skill_map.keys()))}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps({args.category: cat}, indent=2))
        else:
            print(f"Category: {args.category}")
            print(f"  Keywords: {', '.join(cat.get('keywords', []))}")
            print(f"  Agent:    {cat.get('primary_agent', '?')}")
            print(f"  Skills:   {', '.join(cat.get('skills', []))}")
        return

    if not args.task:
        parser.print_help()
        sys.exit(1)

    matches = recommend(args.task, task_skill_map, skills_catalog)
    if args.json:
        print(json.dumps({"task": args.task, "recommendations": matches}, indent=2))
    else:
        print_recommendation(args.task, matches, skills_catalog)


if __name__ == "__main__":
    main()

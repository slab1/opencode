
import json
import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# ─── Paths ────────────────────────────────────────────────────────────────────
CONFIG_DIR = Path(os.environ.get("OPENCODE_CONFIG_DIR", "/home/.config/opencode"))
AGENTS_DIR = CONFIG_DIR / "agents"
SHARED_DIR = CONFIG_DIR / "shared"
GOLDEN_DIR = SHARED_DIR / "golden"
EVAL_DIR = SHARED_DIR / "eval"

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="OpenCode Agent Dashboard")
HERE = Path(__file__).parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_read_json(path):
    """Read a JSON file, return None on failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def safe_read_file(path):
    """Read a text file, return None on failure."""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return None


def parse_agent_frontmatter(content):
    """Extract YAML-like frontmatter from agent .md file."""
    fm = {}
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line and not line.startswith(" "):
                key, val = line.split(":", 1)
                fm[key.strip()] = val.strip()
    return fm


def parse_agent_sections(content):
    """Extract all <tag>...</tag> sections from agent .md file."""
    sections = {}
    for m in re.finditer(r"<(\w+)>(.*?)</\1>", content, re.DOTALL):
        sections[m.group(1)] = m.group(2).strip()
    return sections


def get_agent_info(name):
    """Parse a single agent .md file and return structured info."""
    path = AGENTS_DIR / f"{name}.md"
    content = safe_read_file(path)
    if not content:
        return None
    fm = parse_agent_frontmatter(content)
    sections = parse_agent_sections(content)

    caps = []
    if "capabilities" in sections:
        caps = re.findall(r"^### (.+)$", sections["capabilities"], re.MULTILINE)

    return {
        "name": name,
        "frontmatter": fm,
        "sections": sections,
        "capabilities": caps,
        "line_count": content.count("\n") + 1,
        "size_bytes": len(content.encode()),
        "raw": content,
    }


def get_all_agents():
    """Return a list of all agents with structural metadata."""
    agents = []
    baseline = safe_read_json(EVAL_DIR / "baseline.json")
    audit_map = {}
    if baseline and "audit" in baseline and "agents" in baseline["audit"]:
        for a in baseline["audit"]["agents"]:
            audit_map[a["filename"].replace(".md", "")] = a

    for f in sorted(AGENTS_DIR.glob("*.md")):
        name = f.stem
        audit = audit_map.get(name, {})
        info = get_agent_info(name)
        raw = info["raw"] if info else ""

        agents.append({
            "name": name,
            "has_role": "<role>" in raw,
            "has_capabilities": "<capabilities>" in raw,
            "capabilities_count": audit.get("capability_sections",
                                             len(info.get("capabilities", [])) if info else 0),
            "frontmatter_valid": (audit.get("has_frontmatter", False)
                                  and audit.get("frontmatter_has_description", False)),
            "has_shared_context": "<shared-context>" in raw,
            "has_context_section": "<context>" in raw,
            "has_task_tracking": audit.get("has_task_tracking", False),
            "has_rules": "<rules>" in raw,
            "has_workflow": audit.get("has_workflow", False),
            "structure_complete": audit.get("structure_complete", False),
            "size_bytes": audit.get("size_bytes", info["size_bytes"] if info else 0),
            "line_count": audit.get("line_count", info["line_count"] if info else 0),
            "mode": info.get("frontmatter", {}).get("mode", "primary") if info else "primary",
        })
    return agents


def get_perf_stats():
    """Aggregate performance.json into per-agent stats."""
    data = safe_read_json(SHARED_DIR / "performance.json") or []
    stats = defaultdict(lambda: {
        "total": 0, "success": 0, "failure": 0, "partial": 0,
        "total_duration": 0, "errors": [], "tasks": []})
    for entry in data:
        agent = entry.get("agent", "unknown")
        s = stats[agent]
        s["total"] += 1
        outcome = entry.get("outcome", "")
        if outcome == "success":
            s["success"] += 1
        elif outcome == "failure":
            s["failure"] += 1
        else:
            s["partial"] += 1
        s["total_duration"] += entry.get("duration_s", 0)
        if entry.get("error"):
            s["errors"].append({
                "task": entry.get("task", ""),
                "error": entry["error"],
                "time": entry.get("timestamp_iso", ""),
            })
        s["tasks"].append({
            "task": entry.get("task", ""),
            "outcome": outcome,
            "duration_s": entry.get("duration_s", 0),
            "timestamp_iso": entry.get("timestamp_iso", ""),
            "error": entry.get("error"),
        })
    for agent, s in stats.items():
        s["success_rate"] = round(s["success"] / s["total"], 3) if s["total"] > 0 else 0
        s["avg_duration"] = round(s["total_duration"] / s["total"], 1) if s["total"] > 0 else 0
        s["tasks"].sort(key=lambda t: t.get("timestamp_iso", ""), reverse=True)
    return dict(stats)


def get_test_cases_by_agent():
    """Group golden test cases by agent."""
    data = safe_read_json(GOLDEN_DIR / "agent_tasks.json")
    if not data or "test_cases" not in data:
        return {}, 0
    cases = data["test_cases"]
    by_agent = defaultdict(list)
    for c in cases:
        by_agent[c.get("agent", "unknown")].append(c)
    return dict(by_agent), len(cases)


def compute_agent_completeness(agent):
    """Compute a 0-100 completeness score for an agent based on structure flags."""
    score = 0
    total = 9
    if agent.get("has_role"): score += 1
    if agent.get("has_capabilities"): score += 1
    if agent.get("frontmatter_valid"): score += 1
    if agent.get("has_shared_context"): score += 1
    if agent.get("has_context_section"): score += 1
    if agent.get("has_task_tracking"): score += 1
    if agent.get("has_rules"): score += 1
    if agent.get("has_workflow"): score += 1
    if agent.get("structure_complete"): score += 1
    return int(score / total * 100)


def get_color_class(pct):
    """Return CSS class based on percentage threshold."""
    if pct >= 80:
        return "green"
    elif pct >= 60:
        return "yellow"
    else:
        return "red"


# ─── Context Data Loaders ─────────────────────────────────────────────────────

def get_context():
    return safe_read_json(SHARED_DIR / "context.json") or {}


def get_baseline():
    return safe_read_json(EVAL_DIR / "baseline.json") or {}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    ctx = get_context()
    baseline = get_baseline()
    agents = get_all_agents()
    perf = get_perf_stats()
    test_cases_by_agent, total_test_cases = get_test_cases_by_agent()

    # System health
    total_agents = len(agents)
    strategies_complete = sum(
        1 for s in ctx.get("strategy_log", []) if s.get("outcome") == "success"
    )
    total_strategies = len(ctx.get("strategy_log", []))

    # Pass rate from baseline
    eval_info = baseline.get("eval", {})
    pass_rate = eval_info.get("pass_rate", 0)
    passed = eval_info.get("passed", 0)

    # Top 3 strategies by success rate
    se = ctx.get("strategy_effectiveness", {})
    sorted_strategies = sorted(
        [(k, v) for k, v in se.items() if v.get("success_rate") is not None],
        key=lambda x: x[1].get("success_rate", 0) * x[1].get("count", 1),
        reverse=True,
    )[:5]

    # Recent workflow trace
    workflow = ctx.get("workflow_trace", [])[-5:]

    # Agent pass rates (simulated from test case distribution + overall rate)
    agent_pass_rates = []
    for a in agents:
        tc = test_cases_by_agent.get(a["name"], [])
        agent_pass_rates.append({
            "name": a["name"],
            "test_count": len(tc),
            "completeness": compute_agent_completeness(a),
        })

    return templates.TemplateResponse(request, "base.html", {
        "page": "dashboard",
        "page_title": "Dashboard — OpenCode Agent Dashboard",
        "total_agents": total_agents,
        "total_test_cases": total_test_cases,
        "pass_rate": pass_rate,
        "passed": passed,
        "strategies_complete": strategies_complete,
        "total_strategies": total_strategies,
        "top_strategies": sorted_strategies,
        "workflow_entries": workflow,
        "agent_pass_rates": agent_pass_rates,
        "perf_stats": perf,
    })


@app.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request):
    agents = get_all_agents()
    for a in agents:
        a["completeness"] = compute_agent_completeness(a)
    return templates.TemplateResponse(request, "base.html", {
        "page": "agents",
        "page_title": "Agents — OpenCode Agent Dashboard",
        "agents": agents,
    })


@app.get("/agents/{name}", response_class=HTMLResponse)
async def agent_detail(name: str, request: Request):
    info = get_agent_info(name)
    if not info:
        return templates.TemplateResponse(request, "base.html", {
            "page": "error",
            "page_title": "Agent Not Found",
            "error_msg": f"Agent '{name}' not found.",
        })
    perf = get_perf_stats()
    agent_perf = perf.get(name, {
        "total": 0, "success": 0, "failure": 0, "partial": 0,
        "success_rate": 0, "avg_duration": 0, "errors": [], "tasks": []
    })
    test_cases_by_agent, _ = get_test_cases_by_agent()
    agent_tests = test_cases_by_agent.get(name, [])

    # Count severity distribution
    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    for tc in agent_tests:
        severity_counts[tc.get("severity", "info")] += 1
        category_counts[tc.get("category", "other")] += 1

    return templates.TemplateResponse(request, "base.html", {
        "page": "agent_detail",
        "page_title": f"{name} — Agent Detail",
        "agent": info,
        "agent_name": name,
        "perf": agent_perf,
        "test_cases": agent_tests,
        "severity_counts": dict(severity_counts),
        "category_counts": dict(category_counts),
        "completeness": compute_agent_completeness_from_list(get_all_agents(), name),
    })


def compute_agent_completeness_from_list(agents, name):
    for a in agents:
        if a["name"] == name:
            return compute_agent_completeness(a)
    return 0


@app.get("/eval", response_class=HTMLResponse)
async def eval_page(request: Request):
    baseline = get_baseline()
    ctx = get_context()
    agents = get_all_agents()
    test_cases_by_agent, total_test_cases = get_test_cases_by_agent()

    eval_info = baseline.get("eval", {})
    pass_rate = eval_info.get("pass_rate", 0)
    passed = eval_info.get("passed", 0)

    # Per-agent eval breakdown
    agent_eval = []
    for a in agents:
        tc = test_cases_by_agent.get(a["name"], [])
        n_tests = len(tc)
        completeness = compute_agent_completeness(a)
        agent_eval.append({
            "name": a["name"],
            "test_count": n_tests,
            "completeness": completeness,
            "pass_rate": pass_rate,
            "estimated_passed": round(n_tests * pass_rate) if n_tests > 0 else 0,
        })

    agent_eval.sort(key=lambda x: x["completeness"], reverse=True)

    return templates.TemplateResponse(request, "base.html", {
        "page": "eval",
        "page_title": "Evaluation — OpenCode Agent Dashboard",
        "pass_rate": pass_rate,
        "passed": passed,
        "total_tests": total_test_cases,
        "agent_eval": agent_eval,
        "strategy_effectiveness": ctx.get("strategy_effectiveness", {}),
    })


@app.get("/strategies", response_class=HTMLResponse)
async def strategies(request: Request):
    ctx = get_context()
    se = ctx.get("strategy_effectiveness", {})
    strategy_log = ctx.get("strategy_log", [])

    # Transform to list with computed fields
    strategies_list = []
    for name, data in se.items():
        strategies_list.append({
            "name": name,
            "count": data.get("count", 0),
            "completed": data.get("completed", 0),
            "success_rate": data.get("success_rate"),
            "avg_confidence_before": data.get("avg_confidence_before", 0),
            "avg_confidence_after": data.get("avg_confidence_after"),
            "calibration_delta": data.get("calibration_delta"),
        })

    # Sort by success rate desc, then by count desc
    strategies_list.sort(
        key=lambda s: (s["success_rate"] if s["success_rate"] is not None else -1, s["count"]),
        reverse=True,
    )

    # Strategy log with full details (newest first)
    log_entries = list(reversed(strategy_log))

    return templates.TemplateResponse(request, "base.html", {
        "page": "strategies",
        "page_title": "Strategies — OpenCode Agent Dashboard",
        "strategies": strategies_list,
        "log_entries": log_entries,
    })


@app.get("/performance", response_class=HTMLResponse)
async def performance(request: Request):
    perf = get_perf_stats()

    # Sort by total tasks desc
    sorted_perf = sorted(
        [{"agent": k, **v} for k, v in perf.items()],
        key=lambda x: x["total"],
        reverse=True,
    )

    # Collect all errors
    all_errors = []
    for agent_name, stats in perf.items():
        for err in stats.get("errors", []):
            all_errors.append({"agent": agent_name, **err})

    totals = {
        "total_tasks": sum(s["total"] for s in perf.values()),
        "total_success": sum(s["success"] for s in perf.values()),
        "total_failure": sum(s["failure"] for s in perf.values()),
        "total_partial": sum(s["partial"] for s in perf.values()),
    }

    return templates.TemplateResponse(request, "base.html", {
        "page": "performance",
        "page_title": "Performance — OpenCode Agent Dashboard",
        "perf_data": sorted_perf,
        "errors": all_errors,
        "totals": totals,
    })


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OpenCode Agent Dashboard")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("AGENT_DASHBOARD_PORT", 8080)),
        help="Port to listen on (env: AGENT_DASHBOARD_PORT, default: 8080)",
    )
    args = parser.parse_args()
    print(f"Starting OpenCode Agent Dashboard on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()

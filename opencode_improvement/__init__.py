"""
opencode_improvement — Self-Improvement Engine for OpenCode Agents

Inspired by HyperAgents (Zhang et al., 2026) and the Darwin Gödel Machine,
this module enables agents to:

  Phase 1 — Track: Log every task outcome, build a performance history
  Phase 2 — Evolve: Suggest and apply config changes to agent .md files
  Phase 3 — Transfer: Carry successful improvement strategies across agents

Architecture:
    PerformanceTracker  → logs what happened
    ConfigEvolution     → modifies agent .md files
    CrossDomainTransfer → reuses strategies across agents
    MetaAgentRunner     → orchestrates the improvement cycle

Usage:
    from opencode_improvement import PerformanceTracker

    tracker = PerformanceTracker()
    tracker.log("build", "implement-login", "success", duration_s=120)
    report = tracker.report()
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

__version__ = "0.1.0"

# ── Default Paths ───────────────────────────────────────────────────────
SHARED_CONTEXT_PATH = Path(os.environ.get(
    "OPENCODE_CONFIG_DIR",
    Path.home() / ".config" / "opencode"
)) / "shared" / "context.json"

AGENTS_DIR = SHARED_CONTEXT_PATH.parent.parent / "agents"
GRAPH_PATH = SHARED_CONTEXT_PATH.parent.parent / "knowledge-graph" / "graph.json"


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Performance Tracking
# ═══════════════════════════════════════════════════════════════════════════

class PerformanceTracker:
    """Logs task outcomes and builds a performance history for every agent.

    Each entry records:
      - agent: which agent ran
      - task_description: what it was asked to do
      - outcome: success / failure / partial
      - duration_s: how long it took
      - error: error message if failed
      - context: free-form additional data
      - timestamp: epoch seconds

    Stored under shared context → findings.meta_agent.performance_log
    """

    def __init__(self, context_path: Optional[Path] = None):
        self.context_path = context_path or SHARED_CONTEXT_PATH

    def _read_context(self) -> dict:
        if self.context_path.exists():
            try:
                return json.loads(self.context_path.read_text())
            except (json.JSONDecodeError, PermissionError):
                return {}
        return {}

    def _write_context(self, data: dict):
        self.context_path.parent.mkdir(parents=True, exist_ok=True)
        self.context_path.write_text(json.dumps(data, indent=2, default=str))

    # ── Public API ───────────────────────────────────────────────────

    def log(
        self,
        agent: str,
        task_description: str,
        outcome: str,
        duration_s: Optional[float] = None,
        error: Optional[str] = None,
        config_snapshot: Optional[dict] = None,
        context: Optional[dict] = None,
    ) -> dict:
        """Record a task outcome.

        Returns the entry that was logged.
        """
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

        data = self._read_context()
        if "findings" not in data:
            data["findings"] = {}
        if "meta_agent" not in data["findings"]:
            data["findings"]["meta_agent"] = {}
        if "performance_log" not in data["findings"]["meta_agent"]:
            data["findings"]["meta_agent"]["performance_log"] = []

        data["findings"]["meta_agent"]["performance_log"].append(entry)
        self._write_context(data)
        return entry

    def report(
        self,
        agent: Optional[str] = None,
        last_n: Optional[int] = None,
        min_outcomes: int = 1,
    ) -> dict:
        """Generate a performance summary.

        Args:
            agent: Filter to one agent. None = all agents.
            last_n: Only consider the N most recent entries.
            min_outcomes: Minimum entries required to report stats.

        Returns:
            Dict with summary stats per agent.
        """
        data = self._read_context()
        log = (
            data
            .get("findings", {})
            .get("meta_agent", {})
            .get("performance_log", [])
        )

        if not log:
            return {"status": "no_data", "message": "No performance data logged yet."}

        # Filter + sort
        if agent:
            log = [e for e in log if e.get("agent") == agent]
        log.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        if last_n and len(log) > last_n:
            log = log[:last_n]

        # Group by agent
        by_agent: Dict[str, dict] = {}
        for entry in log:
            a = entry.get("agent", "unknown")
            if a not in by_agent:
                by_agent[a] = {
                    "agent": a,
                    "total": 0,
                    "success": 0,
                    "failure": 0,
                    "partial": 0,
                    "avg_duration_s": 0.0,
                    "recent_errors": [],
                    "last_outcome": None,
                }
            stats = by_agent[a]
            stats["total"] += 1
            outcome = entry.get("outcome", "unknown")
            if outcome == "success":
                stats["success"] += 1
            elif outcome == "failure":
                stats["failure"] += 1
            elif outcome == "partial":
                stats["partial"] += 1

            dur = entry.get("duration_s")
            if dur:
                old_total = stats["avg_duration_s"] * (stats["total"] - 1)
                stats["avg_duration_s"] = (old_total + dur) / stats["total"]

            if entry.get("error"):
                stats["recent_errors"].append(entry["error"])

            stats["last_outcome"] = outcome
            stats["last_task"] = entry.get("task")

        # Compute success rates
        for a, stats in by_agent.items():
            if stats["total"] >= min_outcomes:
                stats["success_rate"] = round(
                    stats["success"] / stats["total"] * 100, 1
                )
            else:
                stats["success_rate"] = None

        return {
            "status": "ok",
            "total_entries": len(log),
            "agents": list(by_agent.values()),
            "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def get_log(self, agent: Optional[str] = None) -> List[dict]:
        """Raw access to the performance log."""
        data = self._read_context()
        log = (
            data
            .get("findings", {})
            .get("meta_agent", {})
            .get("performance_log", [])
        )
        if agent:
            log = [e for e in log if e.get("agent") == agent]
        return sorted(log, key=lambda e: e.get("timestamp", 0), reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: Config Evolution
# ═══════════════════════════════════════════════════════════════════════════

class ConfigEvolution:
    """Analyzes agent .md files and suggests improvements.

    This is the core of Phase 2 self-improvement:
    - Read agent configs
    - Identify gaps and improvement opportunities
    - Generate new capability sections
    - Apply patches (with validation)
    - Track what changed
    """

    def __init__(self, agents_dir: Optional[Path] = None):
        self.agents_dir = Path(agents_dir or AGENTS_DIR)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agent .md files with basic metadata."""
        agents = []
        for f in sorted(self.agents_dir.glob("*.md")):
            content = f.read_text()
            agents.append({
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "has_role": "<role>" in content,
                "has_capabilities": "<capabilities>" in content,
                "has_shared_context": "<shared-context>" in content,
                "capability_sections": self._count_capability_sections(content),
            })
        return agents

    def _count_capability_sections(self, content: str) -> int:
        """Count ### headings in <capabilities> block."""
        in_block = False
        count = 0
        for line in content.split("\n"):
            if "<capabilities>" in line:
                in_block = True
                continue
            if "</capabilities>" in line:
                break
            if in_block and line.strip().startswith("###"):
                count += 1
        return count

    def analyze_agent(self, agent_name: str) -> Dict[str, Any]:
        """Deep-analyze a single agent's config for improvement opportunities."""
        path = self.agents_dir / agent_name
        if not path.exists():
            # Try with .md extension
            path = self.agents_dir / f"{agent_name}.md"
        if not path.exists():
            return {"error": f"Agent '{agent_name}' not found", "improvements": []}

        content = path.read_text()
        improvements = []

        # Check 1: Has all required sections
        if "<role>" not in content:
            improvements.append("missing_role_section")
        if "<capabilities>" not in content:
            improvements.append("missing_capabilities_section")
        if "<shared-context>" not in content:
            improvements.append("missing_shared_context_section")

        # Check 2: Has structured capability headings
        cap_count = self._count_capability_sections(content)
        if cap_count < 2:
            improvements.append("low_capability_detail")

        # Check 3: Has frontmatter with description
        if not content.startswith("---"):
            improvements.append("missing_frontmatter")
        else:
            # Check for permission section
            if "permission:" not in content[:content.index("---", 2)]:
                improvements.append("missing_permissions")

        # Check 4: Size check — tiny agents may be too brief
        if len(content) < 500:
            improvements.append("agent_config_too_small")

        return {
            "agent": agent_name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "improvements": improvements,
            "improvement_count": len(improvements),
        }

    def generate_capability_block(
        self,
        agent_name: str,
        new_capabilities: List[str],
    ) -> str:
        """Generate a <capabilities> block for a new agent.

        Args:
            agent_name: Name of the agent
            new_capabilities: List of capability descriptions

        Returns:
            Markdown string with formatted capability sections
        """
        lines = ["<capabilities>"]
        for cap in new_capabilities:
            # Use the capability text as a section heading
            heading = cap.split(":")[0].strip() if ":" in cap else cap
            desc = cap.split(":", 1)[1].strip() if ":" in cap else ""
            lines.append(f"### {heading}")
            if desc:
                lines.append(f"- **{heading}**: {desc}")
            lines.append("")
        lines.append("</capabilities>")
        return "\n".join(lines)

    def propose_patch(
        self,
        agent_name: str,
        section: str,
        new_content: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Propose a change to an agent's .md file without applying it.

        Returns a patch dict that can be reviewed before applying.
        """
        path = self.agents_dir / agent_name
        if not path.exists():
            path = self.agents_dir / f"{agent_name}.md"
        if not path.exists():
            return {"error": f"Agent '{agent_name}' not found"}

        return {
            "agent": agent_name,
            "file": str(path),
            "section": section,
            "new_content_preview": new_content[:200] + ("..." if len(new_content) > 200 else ""),
            "reason": reason,
            "applied": False,
        }

    def apply_patch(
        self,
        agent_name: str,
        section: str,
        old_string: str,
        new_string: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Apply a change to an agent's .md file.

        Returns the result of the edit.
        """
        path = self.agents_dir / agent_name
        if not path.exists():
            path = self.agents_dir / f"{agent_name}.md"
        if not path.exists():
            return {"error": f"Agent '{agent_name}' not found", "applied": False}

        try:
            content = path.read_text()
            if old_string not in content:
                return {
                    "error": f"old_string not found in {path.name}",
                    "applied": False,
                }

            # Check for uniqueness
            if content.count(old_string) > 1:
                return {
                    "error": f"Multiple matches for old_string in {path.name} — be more specific",
                    "applied": False,
                }

            new_content = content.replace(old_string, new_string, 1)
            path.write_text(new_content)

            # Log the change in shared context
            tracker = PerformanceTracker()
            tracker.log(
                agent="meta_agent",
                task_description=f"config_patch: {agent_name} → {section}",
                outcome="success",
                context={
                    "patched_agent": agent_name,
                    "section": section,
                    "reason": reason,
                },
            )

            return {
                "applied": True,
                "agent": agent_name,
                "section": section,
                "reason": reason,
                "bytes_changed": len(new_content) - len(content),
            }

        except Exception as e:
            return {"error": str(e), "applied": False}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3: Cross-Domain Transfer
# ═══════════════════════════════════════════════════════════════════════════

class CrossDomainTransfer:
    """Identifies patterns that worked in one agent and applies them to others.

    This implements the HyperAgent insight that meta-level improvements
    (persistent memory, performance tracking, self-modification strategies)
    can transfer across domains without hand-tuning.
    """

    def __init__(self):
        self.tracker = PerformanceTracker()

    def find_transferable_patterns(self) -> List[Dict[str, Any]]:
        """Scan all agents for improvement patterns that could transfer.

        Looks for:
        - Agents with high success rates → what do they have that others don't?
        - Common missing sections across agents
        - Capability patterns that correlate with success
        """
        log = self.tracker.get_log()
        report = self.tracker.report()
        patterns = []

        # Look at all agents' success rates from the performance log
        agent_stats = report.get("agents", [])
        if not agent_stats:
            return [{"message": "Not enough performance data yet. Run tasks first."}]

        # Find high-performers vs low-performers
        sorted_agents = sorted(
            [a for a in agent_stats if a.get("success_rate") is not None],
            key=lambda a: a["success_rate"],
            reverse=True,
        )

        if len(sorted_agents) >= 2:
            top = sorted_agents[0]
            bottom = sorted_agents[-1]
            if top["success_rate"] - bottom["success_rate"] > 20:
                patterns.append({
                    "type": "success_rate_gap",
                    "from_agent": top["agent"],
                    "to_agent": bottom["agent"],
                    "gap_pct": round(top["success_rate"] - bottom["success_rate"], 1),
                    "hypothesis": (
                        f"{top['agent']} has {top['success_rate']}% success vs "
                        f"{bottom['agent']} at {bottom['success_rate']}%. "
                        f"Analyze {top['agent']} config for patterns to transfer."
                    ),
                })

        return patterns

    def suggest_cross_train(
        self,
        source_agent: str,
        target_agents: List[str],
    ) -> Dict[str, Any]:
        """Suggest transferring capabilities from source to target agents.

        In HyperAgent terms: this is the meta-level improvement transfer.
        """
        config = ConfigEvolution()
        source_analysis = config.analyze_agent(source_agent)
        if "error" in source_analysis:
            return source_analysis

        suggestions = []
        for target in target_agents:
            target_analysis = config.analyze_agent(target)
            if "error" in target_analysis:
                continue

            # Compare what the source has that the target is missing
            source_caps = set(self._extract_capability_names(source_agent))
            target_caps = set(self._extract_capability_names(target))
            missing = source_caps - target_caps

            if missing:
                suggestions.append({
                    "target": target,
                    "missing_capabilities": list(missing),
                    "transfer_count": len(missing),
                })

        return {
            "source": source_agent,
            "targets": target_agents,
            "suggestions": suggestions,
        }

    def _extract_capability_names(self, agent_name: str) -> List[str]:
        """Extract ### heading names from an agent's <capabilities> block."""
        path = AGENTS_DIR / agent_name
        if not path.exists():
            path = AGENTS_DIR / f"{agent_name}.md"
        if not path.exists():
            return []

        content = path.read_text()
        in_block = False
        caps = []
        for line in content.split("\n"):
            if "<capabilities>" in line:
                in_block = True
                continue
            if "</capabilities>" in line:
                break
            if in_block and line.strip().startswith("###"):
                caps.append(line.strip().lstrip("#").strip())
        return caps

    def suggest_capability_boost(
        self,
        agent_name: str,
        domain: str,
        new_capabilities: List[str],
    ) -> Dict[str, Any]:
        """Generate a complete recommendation to boost an agent with new capabilities.

        This is the end-to-end transfer flow:
        1. Reads the agent's current config
        2. Generates a new <capabilities> block with added capabilities
        3. Returns as a patch ready for review + apply
        """
        config = ConfigEvolution()
        analysis = config.analyze_agent(agent_name)
        new_block = config.generate_capability_block(agent_name, new_capabilities)

        path = AGENTS_DIR / agent_name
        if not path.exists():
            path = AGENTS_DIR / f"{agent_name}.md"

        return {
            "agent": agent_name,
            "domain": domain,
            "new_capabilities": new_capabilities,
            "proposed_capability_block": new_block,
            "analysis": analysis,
            "transfer_from": "cross_domain_transfer",
        }


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2+3 Runner: Full Improvement Cycle
# ═══════════════════════════════════════════════════════════════════════════

class MetaAgentRunner:
    """Orchestrates the full improvement cycle.

    This is the meta-agent's runtime — it:
    1. Reviews performance data
    2. Identifies weak spots
    3. Generates candidate improvements
    4. Validates them
    5. Applies them
    6. Logs everything for future cycles
    """

    def __init__(self):
        self.tracker = PerformanceTracker()
        self.config = ConfigEvolution()
        self.transfer = CrossDomainTransfer()

    def full_audit(self) -> Dict[str, Any]:
        """Run a full system audit — the starting point for any improvement cycle.

        Returns a comprehensive report of agent health, performance, and
        improvement opportunities.
        """
        agents = self.config.list_agents()
        performance = self.tracker.report()
        improvements = {}
        for a in agents:
            name = a["filename"].replace(".md", "")
            improvements[name] = self.config.analyze_agent(name)

        return {
            "agent_count": len(agents),
            "agents": agents,
            "performance": performance,
            "improvement_opportunities": improvements,
            "transferable_patterns": self.transfer.find_transferable_patterns(),
        }

    def suggest_improvement_cycle(self, target_agent: str) -> Dict[str, Any]:
        """Generate a full improvement cycle for one agent.

        This is what the meta-agent runs to evolve a single agent:
        1. Analyze current config
        2. Check performance history
        3. Look for transferable patterns from high-performers
        4. Generate patch proposals
        5. Return structured improvement plan
        """
        analysis = self.config.analyze_agent(target_agent)
        perf = self.tracker.report(agent=target_agent)
        patterns = self.transfer.find_transferable_patterns()

        return {
            "target": target_agent,
            "analysis": analysis,
            "performance": perf,
            "transfer_opportunities": patterns,
            "improvement_plan": self._build_improvement_plan(analysis, perf, patterns),
        }

    def _build_improvement_plan(
        self,
        analysis: dict,
        performance: dict,
        patterns: list,
    ) -> List[Dict[str, str]]:
        """Build a prioritized list of improvement actions."""
        plan = []

        # Priority 1: Fix missing sections
        for imp in analysis.get("improvements", []):
            if imp.startswith("missing_"):
                plan.append({
                    "priority": "high",
                    "action": f"Fix {imp}",
                    "detail": f"Agent is missing required section: {imp}",
                })

        # Priority 2: Transfer from high-performers
        for p in patterns:
            if p.get("type") == "success_rate_gap":
                plan.append({
                    "priority": "medium",
                    "action": f"Transfer patterns from {p['from_agent']}",
                    "detail": p["hypothesis"],
                })

        # Priority 3: Performance issues
        perf_agents = performance.get("agents", [])
        for a in perf_agents:
            if a.get("success_rate") is not None and a["success_rate"] < 60:
                plan.append({
                    "priority": "high",
                    "action": f"Investigate low success rate ({a['success_rate']}%)",
                    "detail": f"Agent has {a['total']} tasks logged with {a['failure']} failures",
                })

        return plan


# ── CLI Entry Point ─────────────────────────────────────────────────────

def main():
    """CLI entry point for the improvement engine."""
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenCode Improvement Engine — Performance tracking, config evolution, cross-domain transfer"
    )
    parser.add_argument("action", choices=["audit", "report", "analyze", "suggest"],
                        help="Action to perform")
    parser.add_argument("--agent", "-a", help="Target agent name")
    parser.add_argument("--last-n", type=int, default=50, help="Last N entries for report")

    args = parser.parse_args()
    runner = MetaAgentRunner()

    if args.action == "audit":
        result = runner.full_audit()
        print(json.dumps(result, indent=2, default=str))

    elif args.action == "report":
        result = runner.tracker.report(agent=args.agent, last_n=args.last_n)
        print(json.dumps(result, indent=2, default=str))

    elif args.action == "analyze":
        if not args.agent:
            print("ERROR: --agent is required for analyze")
            return 1
        result = runner.config.analyze_agent(args.agent)
        print(json.dumps(result, indent=2, default=str))

    elif args.action == "suggest":
        if not args.agent:
            print("ERROR: --agent is required for suggest")
            return 1
        result = runner.suggest_improvement_cycle(args.agent)
        print(json.dumps(result, indent=2, default=str))

    return 0


if __name__ == "__main__":
    exit(main())

import json
import re
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from shared.memory_controller import MemoryController
from opencode_improvement.logic_evolve import LogicEvolver

# Paths
BASE_DIR = Path.home() / ".config" / "opencode"
CONTEXT_FILE = BASE_DIR / "shared" / "context.json"

class AetherCore:
    """
    Hourly maintenance pulse for the OpenCode agent ecosystem.

    Runs three scheduled maintenance tasks (see cron: oc-aether-pulse.sh):
      1. Memory consolidation: L2 episodic -> L3 semantic facts (heuristic).
      2. Logic evolution: RCSI loop over strategy effectiveness (LogicEvolver).
      3. Capability audit: scan strategy_effectiveness + skill frontmatter.

    This is a scheduled maintenance job whose outputs are logged for review,
    NOT an autonomous self-improving system.
    """

    def __init__(self):
        self.memory = MemoryController()
        self.evolver = LogicEvolver()
        self.heartbeat_log = BASE_DIR / "shared" / "aether_heartbeat.jsonl"

    def pulse(self):
        """
        A single 'Cognitive Cycle'.
        Triggers maintenance and evolution tasks.
        """
        print("--- Aether Heartbeat Pulse Starting ---")
        
        # 1. Memory Consolidation (L2 -> L3)
        self._consolidate_memory()
        
        # 2. Logic Evolution (Empirical Patching)
        self._evolve_logic()
        
        # 3. Capability Audit
        self._audit_capabilities()
        
        self._log_pulse("Success")
        print("--- Aether Heartbeat Pulse Complete ---")

    def _consolidate_memory(self):
        """Convert successful Episodic trajectories into Semantic facts (heuristic).

        Reads memory/aether/episodic_memory.jsonl, keeps experiences whose
        outcome contains success/pass/done, groups them by task, and writes one
        (subject, solved_by, action) fact per task into semantic_memory.json via
        MemoryController.store_fact. Facts already present are skipped (dedupe).
        """
        print("Consolidating memory (L2 -> L3)...")
        episodic = BASE_DIR / "memory" / "aether" / "episodic_memory.jsonl"
        if not episodic.exists():
            print("  No episodic memory file found; nothing to consolidate.")
            return

        # Load existing semantic facts for dedupe.
        existing = set()
        semantic_file = BASE_DIR / "memory" / "aether" / "semantic_memory.json"
        if semantic_file.exists():
            try:
                data = json.loads(semantic_file.read_text())
                existing = {(r["s"], r["p"], r["o"]) for r in data.get("relations", [])}
            except (json.JSONDecodeError, KeyError, OSError):
                existing = set()

        # Group successful experiences by task; one fact per task.
        seen_tasks = set()
        added = 0
        with open(episodic) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    exp = json.loads(line)
                except json.JSONDecodeError:
                    continue
                outcome = str(exp.get("outcome", "")).lower()
                if not any(marker in outcome for marker in ("success", "pass", "done")):
                    continue
                task = str(exp.get("task", "")).strip()
                action = str(exp.get("action", "")).strip()
                if not task or not action:
                    continue
                subject = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")
                if subject in seen_tasks:
                    continue
                seen_tasks.add(subject)
                fact = (subject, "solved_by", action)
                if fact in existing:
                    continue
                self.memory.store_fact(*fact)
                existing.add(fact)
                added += 1

        if added:
            print(f"  Added {added} semantic fact(s) from episodic memory.")
        else:
            print("  No new semantic facts to add (all already present or no successes).")

    def _evolve_logic(self):
        """Run the RCSI loop to patch systemic failures."""
        print("Running Logic Evolution loop...")
        self.evolver.run_evolution_cycle()

    def _audit_capabilities(self):
        """Audit capability gaps: low-success strategies + skills missing frontmatter.

        Scans shared/context.json strategy_effectiveness for strategies with
        success_rate < 0.8, and skills/skills/ for SKILL.md files missing the
        required name/description frontmatter. Prints a JSON summary and
        appends it to the heartbeat log.
        """
        print("Auditing system capabilities...")
        findings = {"low_success_strategies": [], "skills_missing_frontmatter": []}

        # 1. Strategies with success_rate < 0.8
        try:
            context = json.loads(CONTEXT_FILE.read_text())
            effectiveness = context.get("strategy_effectiveness", {})
            for name, stats in effectiveness.items():
                if isinstance(stats, dict) and stats.get("success_rate", 1.0) < 0.8:
                    findings["low_success_strategies"].append({
                        "strategy": name,
                        "success_rate": stats.get("success_rate"),
                        "count": stats.get("count"),
                    })
        except (json.JSONDecodeError, OSError) as e:
            findings["context_error"] = str(e)

        # 2. SKILL.md files missing required frontmatter (name/description)
        skills_root = BASE_DIR / "skills" / "skills"
        if skills_root.exists():
            for skill_md in sorted(skills_root.rglob("SKILL.md")):
                try:
                    head = skill_md.read_text(errors="replace")[:2000]
                except OSError:
                    continue
                rel = str(skill_md.relative_to(BASE_DIR))
                if not head.startswith("---"):
                    findings["skills_missing_frontmatter"].append(rel)
                    continue
                parts = head.split("---", 2)
                fm = parts[1] if len(parts) >= 2 else ""
                if "name:" not in fm or "description:" not in fm:
                    findings["skills_missing_frontmatter"].append(rel)

        summary = {
            "type": "capability_audit",
            "timestamp": time.time(),
            "low_success_strategies": findings["low_success_strategies"],
            "skills_missing_frontmatter": findings["skills_missing_frontmatter"],
        }
        print(json.dumps(summary, indent=2))
        if not findings["low_success_strategies"] and not findings["skills_missing_frontmatter"]:
            print("  No capability gaps found: all strategies >= 0.8, all skills have frontmatter.")

        # Append to heartbeat log
        with open(self.heartbeat_log, "a") as f:
            f.write(json.dumps(summary) + "\n")

    def _log_pulse(self, status: str):
        entry = {
            "timestamp": time.time(),
            "status": status,
            "version": "1.0"
        }
        with open(self.heartbeat_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    core = AetherCore()
    core.pulse()

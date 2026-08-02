import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Paths
BASE_DIR = Path.home() / ".config" / "opencode"
SHARED_DIR = BASE_DIR / "shared"
MEMORY_DIR = BASE_DIR / "memory" / "aether"
EPISODIC_DB = MEMORY_DIR / "episodic_memory.jsonl"
SEMANTIC_DB = MEMORY_DIR / "semantic_memory.json"

class MemoryController:
    """
    Project Aether: Hierarchical Cognitive Memory (HCM) Controller.
    Manages transitions between L1 (Working), L2 (Episodic), L3 (Semantic), and L4 (Procedural).
    """

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._init_storage()

    def _init_storage(self):
        if not EPISODIC_DB.exists():
            EPISODIC_DB.write_text("")
        if not SEMANTIC_DB.exists():
            SEMANTIC_DB.write_text(json.dumps({"entities": {}, "relations": []}, indent=2))

    # --- L2: Episodic Memory (Trajectories) ---

    def store_experience(self, task: str, action: str, outcome: str, metadata: Dict[str, Any] = None):
        """Store a specific experience (Trajectory) in Episodic Memory."""
        entry = {
            "timestamp": time.time(),
            "task": task,
            "action": action,
            "outcome": outcome,
            "metadata": metadata or {}
        }
        with open(EPISODIC_DB, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def retrieve_similar_experiences(self, task_query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieve past experiences similar to the current task query."""
        # Simple keyword match for now; will be replaced by embedding search in Phase 2
        experiences = []
        with open(EPISODIC_DB, "r") as f:
            for line in f:
                exp = json.loads(line)
                if any(word in exp["task"].lower() for word in task_query.lower().split()):
                    experiences.append(exp)
        
        return sorted(experiences, key=lambda x: x["timestamp"], reverse=True)[:limit]

    # --- L3: Semantic Memory (Knowledge Graph) ---

    def store_fact(self, subject: str, predicate: str, object_: str):
        """Store a semantic fact: (S, P, O)."""
        data = self._load_semantic()
        # Simple relation storage
        relation = {"s": subject, "p": predicate, "o": object_, "timestamp": time.time()}
        data["relations"].append(relation)
        
        # Update entities for fast lookup
        for entity in [subject, object_]:
            if entity not in data["entities"]:
                data["entities"][entity] = {"mentions": 0}
            data["entities"][entity]["mentions"] += 1
            
        self._save_semantic(data)

    def query_semantic(self, entity: str) -> List[Dict[str, Any]]:
        """Find all facts related to a specific entity (exact or token match)."""
        data = self._load_semantic()
        entity_l = entity.lower()
        hits = [r for r in data["relations"] if r["s"] == entity or r["o"] == entity]
        if hits:
            return hits
        # Fallback: token match across subject/object for fuzzy recall
        tokens = [t for t in entity_l.split() if len(t) > 3]
        if tokens:
            return [r for r in data["relations"]
                    if any(t in r["s"].lower() or t in r["o"].lower() for t in tokens)]
        return []

    def _load_semantic(self) -> Dict[str, Any]:
        return json.loads(SEMANTIC_DB.read_text())

    def _save_semantic(self, data: Dict[str, Any]):
        SEMANTIC_DB.write_text(json.dumps(data, indent=2))

    # --- L4: Procedural Memory (Skills) ---

    def get_relevant_skills(self, task_query: str) -> List[str]:
        """Interface with oc-recommend-skills to get L4 procedural memory."""
        import subprocess
        try:
            # Use canonical script location with fallback to temp path
            script = Path.home() / ".config" / "opencode" / "scripts" / "oc-recommend-skills.py"
            if not script.exists():
                script = Path("/tmp/slab1-opencode/scripts/oc-recommend-skills.py")
            cmd = ["python3", str(script), task_query, "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            data = json.loads(result.stdout)
            
            skills = []
            if data.get("recommendations"):
                for rec in data["recommendations"]:
                    skills.extend(rec.get("skills", []))
            if skills:
                return list(set(skills))
        except Exception as e:
            print(f"L4 Retrieval Error: {e}")

        # Fallback: domain-based skill heuristics when recommender returns nothing
        q = task_query.lower()
        domain_skills = {
            ("error", "bug", "fix", "fail", "crash", "compile", "e0", "e1"): [
                "debug-systematic-investigation", "error-recovery-protocol",
            ],
            ("refactor", "rename", "migrat", "simplif", "clean"): [
                "refactor-safe", "simplify-code",
            ],
            ("test", "spec", "assert", "coverage"): [
                "tdd-workflow", "test-driven-development",
            ],
            ("security", "vuln", "audit", "threat", "secret"): [
                "security-audit", "security-threat-model",
            ],
            ("search", "find", "explore", "locate"): [
                "codebase-inspection", "explore",
            ],
            ("document", "doc", "readme", "changelog"): [
                "documentation-skeleton",
            ],
            ("review", "pull request", "pr"): [
                "github-code-review", "requesting-code-review",
            ],
        }
        for keywords, skills in domain_skills.items():
            if any(k in q for k in keywords):
                return skills
        return []

    # --- L1: Working Memory Controller ---

    def generate_cognitive_packet(self, task_query: str) -> Dict[str, Any]:
        """
        The 'Attention' mechanism. 
        Combines L2, L3, and L4 into a single packet for L1 (Working Memory).
        """
        return {
            "episodic": self.retrieve_similar_experiences(task_query),
            "semantic": self.query_semantic(task_query),
            "procedural": self.get_relevant_skills(task_query),
            "timestamp": time.time()
        }

if __name__ == "__main__":
    # Quick test
    mc = MemoryController()
    mc.store_experience("Fix E0659", "Remove conflicting imports", "Success")
    print("Cognitive Packet for 'Fix E0659':")
    print(json.dumps(mc.generate_cognitive_packet("Fix E0659"), indent=2))

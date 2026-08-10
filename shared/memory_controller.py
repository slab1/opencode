import json
import re
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
        """Retrieve past experiences similar to the current task query.

        Uses TF-IDF vectorization + cosine similarity (numpy) over the
        task+action+outcome text of every stored experience. Falls back to
        keyword matching if numpy is unavailable. Returns [] when the store
        is empty. Each returned dict gains a ``score`` field (0.0-1.0).
        """
        experiences = self._load_experiences()
        if not experiences:
            return []

        try:
            import numpy as np
        except ImportError:
            return self._keyword_match(task_query, experiences, limit)

        def tokenize(text: str) -> List[str]:
            return re.findall(r"[a-z0-9]+", text.lower())

        query_tokens = tokenize(task_query)
        if not query_tokens:
            return []

        # Corpus: one document per experience (task + action + outcome)
        corpus = [
            tokenize(" ".join([
                str(exp.get("task", "")),
                str(exp.get("action", "")),
                str(exp.get("outcome", "")),
            ]))
            for exp in experiences
        ]

        # Vocabulary
        vocab = {}
        for doc in corpus:
            for tok in doc:
                if tok not in vocab:
                    vocab[tok] = len(vocab)
        if not vocab:
            return []

        # Document frequency + smoothed IDF
        df = np.zeros(len(vocab))
        for doc in corpus:
            for tok in set(doc):
                df[vocab[tok]] += 1
        idf = np.log((1.0 + len(corpus)) / (1.0 + df)) + 1.0

        def tfidf_vector(tokens: List[str]) -> np.ndarray:
            vec = np.zeros(len(vocab))
            counts = {}
            for tok in tokens:
                if tok in vocab:
                    counts[tok] = counts.get(tok, 0) + 1
            for tok, count in counts.items():
                vec[vocab[tok]] = (count / len(tokens)) * idf[vocab[tok]]
            return vec

        query_vec = tfidf_vector(query_tokens)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        scored = []
        for exp, doc_tokens in zip(experiences, corpus):
            doc_vec = tfidf_vector(doc_tokens)
            doc_norm = np.linalg.norm(doc_vec)
            score = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm)) if doc_norm > 0 else 0.0
            result = dict(exp)
            result["score"] = round(score, 4)
            scored.append(result)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def _load_experiences(self) -> List[Dict[str, Any]]:
        """Read all episodic entries, skipping malformed lines."""
        experiences = []
        try:
            with open(EPISODIC_DB, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        experiences.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        return experiences

    def _keyword_match(self, task_query: str, experiences: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
        """Fallback retrieval: naive keyword match (used if numpy is unavailable)."""
        query_words = [w for w in task_query.lower().split() if w]
        if not query_words:
            return []
        matches = []
        for exp in experiences:
            text = " ".join([
                str(exp.get("task", "")),
                str(exp.get("action", "")),
                str(exp.get("outcome", "")),
            ]).lower()
            if any(w in text for w in query_words):
                result = dict(exp)
                result["score"] = round(sum(1 for w in query_words if w in text) / len(query_words), 4)
                matches.append(result)
        matches.sort(key=lambda x: (x["score"], x["timestamp"]), reverse=True)
        return matches[:limit]

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
        # Fallback: token match across subject/object for fuzzy recall,
        # ranked by token-overlap score (most relevant facts first).
        tokens = [t for t in entity_l.split() if len(t) > 3]
        if tokens:
            scored = []
            for r in data["relations"]:
                text = f"{r['s']} {r['o']}".lower()
                overlap = sum(1 for t in tokens if t in text)
                if overlap:
                    result = dict(r)
                    result["score"] = round(overlap / len(tokens), 4)
                    scored.append(result)
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored
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

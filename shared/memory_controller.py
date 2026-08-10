import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Portability bundle identifiers (Bet 6)
EXPORT_FORMAT = "aether-memory"
EXPORT_VERSION = 1

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
            f.flush()
            os.fsync(f.fileno())  # anti-data-loss: never lose a session write

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
        try:
            return json.loads(SEMANTIC_DB.read_text())
        except OSError:
            return {"entities": {}, "relations": []}

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

    # --- Portability (Bet 6): export / import / backup ---
    #
    # The anti-data-loss + portability guarantee: episodic memory is written
    # append-only with fsync (never lose a write), and the whole store can be
    # exported to a self-describing bundle, carried to another machine, and
    # restored idempotently (no duplicates when re-imported).

    @staticmethod
    def _entry_key(entry: Dict[str, Any]) -> Tuple[str, float]:
        """Dedupe key: normalized task + timestamp rounded to 3 decimals
        (matches scripts/seed-episodic-memory.py)."""
        task = str(entry.get("task", "")).lower().strip()
        try:
            ts = round(float(entry.get("timestamp", 0.0)), 3)
        except (TypeError, ValueError):
            ts = 0.0
        return (task, ts)

    def export_memory(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Export episodic + semantic memory to a portable, self-describing JSON bundle."""
        episodes = self._load_experiences()
        semantic = self._load_semantic()
        bundle = {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "stats": {
                "episodic": len(episodes),
                "semantic_relations": len(semantic.get("relations", [])),
            },
            "episodic": episodes,
            "semantic": semantic,
        }
        out = Path(path) if path else MEMORY_DIR / "memory_export.json"
        out.write_text(json.dumps(bundle, indent=2))
        return bundle

    def import_memory(self, path: Path) -> Dict[str, Any]:
        """Restore a bundle produced by export_memory into this store.

        Idempotent: entries already present (same task + rounded timestamp)
        are skipped, so re-importing or importing over a store that already
        has the data adds zero duplicates. Semantic facts deduped by (s, p, o).
        """
        data = json.loads(Path(path).read_text())
        if data.get("format") != EXPORT_FORMAT:
            raise ValueError(
                f"Not an aether-memory export (format={data.get('format')!r})"
            )
        if data.get("version", 0) > EXPORT_VERSION:
            raise ValueError(
                f"Export version {data['version']} is newer than supported {EXPORT_VERSION}"
            )

        existing = self._load_experiences()
        existing_keys = {self._entry_key(e) for e in existing}

        added = 0
        skipped = 0
        seen_in_bundle = set()
        for entry in data.get("episodic", []):
            key = self._entry_key(entry)
            if key in existing_keys or key in seen_in_bundle:
                skipped += 1
                continue
            seen_in_bundle.add(key)
            # Write verbatim (preserve the ORIGINAL timestamp) so a restored
            # store is a faithful copy and re-import dedupes on the same keys.
            with open(EPISODIC_DB, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
                os.fsync(f.fileno())
            added += 1
            existing_keys.add(key)

        semantic = self._load_semantic()
        existing_facts = {
            (r.get("s"), r.get("p"), r.get("o"))
            for r in semantic.get("relations", [])
        }
        sem_added = 0
        for rel in data.get("semantic", {}).get("relations", []):
            fact = (rel.get("s"), rel.get("p"), rel.get("o"))
            if fact in existing_facts:
                continue
            existing_facts.add(fact)
            self.store_fact(rel["s"], rel["p"], rel["o"])
            sem_added += 1

        return {
            "status": "ok",
            "episodic_added": added,
            "episodic_skipped_duplicates": skipped,
            "semantic_relations_added": sem_added,
            "episodic_total": len(existing) + added,
        }

    def backup(self) -> Dict[str, Any]:
        """Timestamped, restorable snapshot of the raw store (anti-data-loss)."""
        backups_dir = MEMORY_DIR / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dest_ep = backups_dir / f"episodic_memory.{stamp}.jsonl"
        dest_sem = backups_dir / f"semantic_memory.{stamp}.json"
        if EPISODIC_DB.exists():
            shutil.copy2(EPISODIC_DB, dest_ep)
        if SEMANTIC_DB.exists():
            shutil.copy2(SEMANTIC_DB, dest_sem)
        n_entries = 0
        if EPISODIC_DB.exists():
            try:
                n_entries = sum(1 for l in EPISODIC_DB.open() if l.strip())
            except OSError:
                n_entries = 0
        manifest = {
            "format": EXPORT_FORMAT,
            "type": "backup",
            "version": EXPORT_VERSION,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "episodic": dest_ep.name,
            "semantic": dest_sem.name,
            "episodic_entries": n_entries,
        }
        (backups_dir / f"manifest.{stamp}.json").write_text(
            json.dumps(manifest, indent=2)
        )
        return {
            "status": "ok",
            "backup_dir": str(backups_dir),
            "manifest": manifest,
        }

if __name__ == "__main__":
    # Quick test
    mc = MemoryController()
    mc.store_experience("Fix E0659", "Remove conflicting imports", "Success")
    print("Cognitive Packet for 'Fix E0659':")
    print(json.dumps(mc.generate_cognitive_packet("Fix E0659"), indent=2))

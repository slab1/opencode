import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Paths
BASE_DIR = Path.home() / ".config" / "opencode"
SIM_DIR = BASE_DIR / "simulations"

class ChangeReviewQueue:
    """
    Change review queue: stages a proposed diff for critic review.

    This is NOT a world model or a simulation. It records a proposed
    (old -> new) edit, applies a heuristic risk estimate, and persists the
    entry for `agents/critic.md` to review before the change is applied to
    the real codebase. The risk score is a rough heuristic, not a prediction
    of real-world impact.
    """

    def __init__(self):
        SIM_DIR.mkdir(parents=True, exist_ok=True)

    def queue_change(self, file_path: str, old_string: str, new_string: str,
                     history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Queue a proposed change for critic review.

        Persists a review entry to simulations/<id>.json containing the diff
        and a heuristic risk score, then returns the entry id so the critic
        can be dispatched to review it.

        Doom-loop guard: when ``history`` (list of prior {file,old,new} or
        {file,from,to} dicts) already contains this identical (file,old,new),
        the change is rejected without scoring. Never throws.
        """
        try:
            for prior in history or []:
                if not isinstance(prior, dict):
                    continue
                # Check file first (cheapest discriminator).
                if prior.get("file", prior.get("file_path")) != file_path:
                    continue
                prior_old = prior.get("old", prior.get("from", prior.get("old_string")))
                prior_new = prior.get("new", prior.get("to", prior.get("new_string")))
                if prior_old == old_string and prior_new == new_string:
                    sim_id = f"sim_{int(time.time())}"
                    virtual_diff = {
                        "file": file_path,
                        "change": {"from": old_string, "to": new_string},
                        "risk_score": 1.0,
                    }
                    return {
                        "sim_id": sim_id,
                        "virtual_diff": virtual_diff,
                        "risk_score": 1.0,
                        "verdict": "REJECT",
                        "reason": "identical repeat",
                        "status": "rejected_repeat",
                        "reviewer": "agents/critic.md",
                    }
        except Exception:
            pass
        print(f"Queueing change in {file_path} for review...")

        # 1. Build the review entry (a diff, not a simulation)
        review_entry = {
            "file": file_path,
            "change": {
                "from": old_string,
                "to": new_string
            },
            "risk_score": self._estimate_risk(old_string, new_string)
        }

        # 2. Persist for the Critic to review
        sim_id = f"sim_{int(time.time())}"
        sim_file = SIM_DIR / f"{sim_id}.json"
        sim_file.write_text(json.dumps(review_entry, indent=2))

        return {
            "sim_id": sim_id,
            "virtual_diff": review_entry,
            "status": "queued_for_review",
            "reviewer": "agents/critic.md"
        }

    def _estimate_risk(self, old: str, new: str) -> float:
        """Heuristic risk estimate for a proposed change (not a simulation)."""
        # Rough heuristic: changes to imports or type signatures are higher risk
        if "import " in old or "fn " in old or "struct " in old:
            return 0.9
        if len(new) > len(old) * 2:
            return 0.7
        return 0.3

    # Backward-compatible aliases (kept so agents/critic.md references stay valid)
    simulate_change = queue_change
    _estimate_impact = _estimate_risk


# Backward-compatible alias for the old class name
SimulationSandbox = ChangeReviewQueue


if __name__ == "__main__":
    queue = ChangeReviewQueue()
    res = queue.queue_change("shared/context.json", "version: 1.1", "version: 1.2")
    print(json.dumps(res, indent=2))
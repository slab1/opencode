import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

class TrajectoryLogger:
    """
    Records the full execution trajectory of an agent.
    Captures thoughts, tool calls, observations, and final outcomes to enable
    the Skill-Optimizer to identify patterns of success and failure.
    """
    def __init__(self, storage_dir: str = "~/.config/opencode/shared/trajectories"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_trajectory: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def start_trajectory(self, agent_id: str, task_id: str, goal: str, config: Optional[Dict] = None):
        """Initialize a new trajectory record."""
        self.current_trajectory = []
        self.metadata = {
            "agent_id": agent_id,
            "task_id": task_id,
            "goal": goal,
            "start_time": datetime.now().isoformat(),
            "config": config or {}
        }

    def log_step(self, step_type: str, content: Any, metadata: Optional[Dict] = None):
        """
        Log a single step in the agent's reasoning process.
        Step types: 'thought', 'tool_call', 'observation', 'reflection', 'final_answer'.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": step_type,
            "content": content,
            "metadata": metadata or {}
        }
        self.current_trajectory.append(entry)

    def end_trajectory(self, outcome: str, score: float = 0.0, final_answer: Optional[str] = None):
        """Finalize the trajectory and save it to disk."""
        self.metadata.update({
            "end_time": datetime.now().isoformat(),
            "outcome": outcome,
            "score": score,
            "final_answer": final_answer
        })
        
        # Save as JSON file named by agent_task_timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.metadata['agent_id']}_{self.metadata['task_id']}_{timestamp}.json"
        filepath = self.storage_dir / filename
        
        data = {
            "metadata": self.metadata,
            "trajectory": self.current_trajectory
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        return str(filepath)

    def get_recent_trajectories(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve the most recent trajectories for a specific agent for analysis."""
        files = sorted(
            self.storage_dir.glob(f"{agent_id}_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        trajectories = []
        for f in files[:limit]:
            with open(f, "r", encoding="utf-8") as file:
                trajectories.append(json.load(file))
        
        return trajectories

#!/usr/bin/env python3
"""
Auto-Track — Context manager / decorator for automatic task tracking.

Agents can use this to wrap any operation and have it automatically logged:

    from opencode_improvement.auto_track import track

    with track("build", "implement-login"):
        # ... do the work ...
        # If an exception is raised, outcome = "failure"
        # If no exception, outcome = "success"

Or as a decorator:
    @track("media-agent", "analyze-screenshot")
    def do_analysis():
        ...

Or with explicit outcome:
    tracker = track("web-browser", "navigate-and-scrape")
    tracker.start()
    # ... work ...
    tracker.finish("success")
"""
import time
import traceback
import functools
from typing import Optional, Callable
from opencode_improvement.track import log_entry


class TrackContext:
    """Context manager + decorator for automatic task tracking."""

    def __init__(self, agent: str, task_description: str, context: Optional[dict] = None):
        self.agent = agent
        self.task = task_description
        self.context = context or {}
        self._start = None

    def start(self):
        """Begin timing."""
        self._start = time.time()

    def finish(self, outcome: str = "success", error: Optional[str] = None, extra_context: Optional[dict] = None):
        """Record the outcome with elapsed time."""
        elapsed = (time.time() - self._start) if self._start else None
        ctx = {**self.context, **(extra_context or {})}
        return log_entry(
            agent=self.agent,
            outcome=outcome,
            task_description=self.task,
            duration_s=elapsed,
            error=error,
            context=ctx if ctx else None,
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred — track as failure
            error_msg = f"{exc_type.__name__}: {exc_val}"
            tb = "".join(traceback.format_tb(exc_tb)) if exc_tb else ""
            self.finish("failure", error=error_msg, extra_context={"traceback": tb[:500]})
        else:
            self.finish("success")
        return False  # Don't suppress exceptions

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


def track(agent: str, task_description: str, context: Optional[dict] = None) -> TrackContext:
    """Create a tracking context.

    Usage:
        with track("build", "implement-login"):
            # work here
    """
    return TrackContext(agent, task_description, context)


# ── Bash-friendly entry point ───────────────────────────────────────────

def bash_track():
    """CLI entry point that sources from env vars for easy shell use."""
    import os
    agent = os.environ.get("OC_AGENT") or os.environ.get("OC_TRACK_AGENT")
    task = os.environ.get("OC_TASK") or os.environ.get("OC_TRACK_TASK")
    outcome = os.environ.get("OC_OUTCOME") or os.environ.get("OC_TRACK_OUTCOME") or "success"
    error = os.environ.get("OC_ERROR") or os.environ.get("OC_TRACK_ERROR")

    if not agent or not task:
        print("Set OC_TRACK_AGENT and OC_TRACK_TASK env vars")
        return 1

    entry = log_entry(agent, outcome, task, error=error)
    print(f"[track] {agent}: {task} → {outcome}")
    return 0


if __name__ == "__main__":
    exit(bash_track())

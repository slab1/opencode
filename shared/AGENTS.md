# Shared Context System — AGENTS.md

This directory holds cross-agent shared state. Every agent should read `context.json`
before starting work and write back completed work before finishing.

## File Map

| File                | Purpose                                        | Format     |
| ------------------- | ---------------------------------------------- | ---------- |
| `AGENTS.md`         | THIS FILE                                      | markdown   |
| `context.json`      | Cross-agent shared context — READ FIRST        | JSON       |
| `checkpoint_manager.py` | Stage-based checkpoint system for state persistence | Python |
| `checkpoints/`      | Checkpoint files (agent workflows / stage snapshots) | JSON dir |
| `commitments.json`  | Track cross-agent commitments                  | JSON Array  |
| `performance.json`  | Performance tracking data                      | JSON Array  |
| `free-models-guide.md` | Guide to free AI image/video models        | markdown   |
| `helpers/`          | Helper scripts                                  | —          |

## Protocol

1. **Read** `context.json` at session start
2. **Write** completed tasks, new artifacts, and decisions to `context.json` before finishing
3. **Update** `performance.json` via the tracking tool for operations > 30s
4. **Respect** commitments in `commitments.json` — don't duplicate work
5. **Save checkpoints** for agent workflow stages via `checkpoint_manager.py` (see checkerboard CLI)

## Checkpoint System

The checkpoint system (`checkpoint_manager.py`) provides stage-based state persistence across
agent workflow stages. Key features:

- Stage-based checkpointing with canonical agent stages (orchestrator, video-creator, etc.)
- Run metadata tracking (status, duration, completed stages)
- Resume packets for interrupted workflow recovery
- Pruning of old checkpoint data

**CLI commands** (via `python3 -m opencode_improvement checkpoint <subcommand>`):
| Subcommand | Description |
|------------|-------------|
| `list` | List checkpoint runs for an agent |
| `inspect` | View checkpoint details for a specific run/stage |
| `save` | Save a checkpoint (programmatic or manual) |
| `resume` | Get a resume packet for interrupted runs |
| `prune` | Remove old checkpoint runs |
| `next-stage` | Show the next uncompleted stage |

**Python API:**
```python
from shared.checkpoint_manager import (
    save_checkpoint, load_checkpoint, get_latest_checkpoint,
    get_completed_stages, get_next_stage, list_runs, resume_run,
    prune_checkpoints, get_agent_stages,
    AgentStage, ORCHESTRATOR_STAGES, CUSTOM_STAGES,
)
```

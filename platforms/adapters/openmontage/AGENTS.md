# OpenMontage Adapter

Wraps OpenMontage's pipeline system for the OpenCode video-creator agent.

**OpenMontage:** /home/OpenMontage/ (AGPL-3.0)
**Adapter location:** `opencode_video.openmontage`

## Architecture

OpenMontage is a production video pipeline system:
- **13 pipeline manifests** in `pipeline_defs/`
- **52+ tools** (BaseTool subclasses) in `tools/` tree
- **Pipeline loader**: `lib/pipeline_loader.py` — `load_pipeline()`, `list_pipelines()`
- **Tool registry**: `tools/tool_registry.py` — `registry.discover()`, `registry.support_envelope()`
- **Cost tracker**: `tools/cost_tracker.py` — budget estimation and tracking
- **Scoring engine**: `lib/scoring.py` — multi-dimensional provider scoring

This adapter is a **wrapper only** — no OpenMontage files are modified.

## Available Pipelines (13)

| Pipeline | Category | Stability | Stages | Description |
|----------|----------|-----------|--------|-------------|
| animated-explainer | generated | production | 8 | Fully AI-produced explainer with research phase |
| animation | animation | production | 8 | Motion graphics, kinetic typography, math visuals |
| avatar-spokesperson | custom | production | 7 | Presenter-led avatar videos |
| character-animation | animation | beta | 10 | Local cartoon character animation |
| cinematic | cinematic | production | 8 | Mood-led film/trailer/brand film production |
| clip-factory | custom | beta | 7 | Multi-clip extraction from long-form content |
| documentary-montage | documentary | beta | 5 | Retrieval-first thematic montage |
| framework-smoke | custom | beta | 2 | Minimal framework testing (not for production) |
| hybrid | hybrid | production | 7 | Source footage + generated support assets |
| localization-dub | custom | beta | 7 | Translated subtitles and dubbed audio |
| podcast-repurpose | custom | beta | 7 | Podcast to short-form social clips |
| screen-demo | screen_recording | production | 9 | Screen capture or synthetic CLI demos |
| talking-head | talking_head | beta | 7 | Raw footage → polished talking-head output |

## Public API

| Function | Returns | Description |
|----------|---------|-------------|
| `discover_pipelines()` | `list[dict]` | Metadata for all pipelines |
| `get_pipeline(name)` | `dict` | Loaded and validated manifest |
| `list_available_pipelines()` | `list[str]` | Pipeline names only |
| `get_pipeline_stages(name)` | `list[str]` | Ordered stage names |
| `get_pipeline_required_skills(name)` | `list[str]` | Required skill paths |
| `get_tool_support_envelope()` | `dict` | All tools with availability status |
| `estimate_pipeline_cost(name, dur, style)` | `dict` | Ballpark cost estimate |
| `get_provider_catalog()` | `dict` | Tools grouped by provider |
| `get_capability_catalog()` | `dict` | Tools grouped by capability |
| `get_tool_tier_summary()` | `dict` | Tool counts by tier/status |
| `setup_openmontage()` | `dict` | Verification status |
| `get_pipeline_summary()` | `str` | Human-readable summary |

## Usage

```python
from opencode_video.openmontage import (
    discover_pipelines,
    get_pipeline,
    get_pipeline_stages,
    setup_openmontage,
)

# Check OpenMontage is available
status = setup_openmontage()
if not status["available"]:
    print("OpenMontage not available — install at /home/OpenMontage/")
    exit(1)

# Pick a pipeline
pipeline = get_pipeline("cinematic")
stages = get_pipeline_stages("cinematic")
print(f"Pipeline: {pipeline['name']} v{pipeline['version']}")
print(f"Stages: {stages}")

# Execute stages in order
for stage_name in stages:
    # agent_skill = get_pipeline_required_skills("cinematic")[i]
    # skill: <agent_skill>
    # execute stage logic
    pass
```

## Integration with OpenCode Agents

| Agent | Use Case |
|-------|----------|
| **video-creator** | Run full production pipelines: explainers, cinematic, talking-head, screen demos |
| **orchestrator** | Route video tasks to appropriate OpenMontage pipeline |
| **content-creator** | Generate pipeline-compatible assets (script, storyboard) |

## Dependencies

- OpenMontage repository at `/home/OpenMontage/`
- Python packages: `pyyaml`, `jsonschema` (OpenMontage requirements)
- FFmpeg (for video composition tools)
- Optional: API keys in `/home/OpenMontage/.env` for paid tools

## License Note

OpenMontage is **AGPL-3.0** licensed. Any project that distributes compositions
using OpenMontage code must also be AGPL-3.0 or have a commercial license.

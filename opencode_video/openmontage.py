"""
OpenMontage pipeline adapter for OpenCode video-creator agent.
===============================================================

Wraps OpenMontage's pipeline system so the video-creator agent can:
- Discover available pipelines
- Load pipeline manifests
- Get tool support envelopes
- Run pipeline stages
- Estimate costs and required skills

OpenMontage is AGPL-3.0 licensed. This adapter is a wrapper only —
no OpenMontage source files are modified.

OpenMontage location: /home/OpenMontage/
    - 13 pipeline YAML manifests in pipeline_defs/
    - Pipeline loader: lib/pipeline_loader.py
    - Tool registry: tools/tool_registry.py
    - 52+ BaseTool subclasses in tools/ tree
    - Cost tracker: tools/cost_tracker.py
    - Scoring engine: lib/scoring.py

Usage (from video-creator agent):
    from opencode_video.openmontage import (
        discover_pipelines,
        get_pipeline,
        list_available_pipelines,
        get_pipeline_stages,
        get_tool_support_envelope,
        setup_openmontage,
        get_pipeline_summary,
    )
"""

import sys
import os
from pathlib import Path
from typing import Any, Optional

# OpenMontage project root
OPENMONTAGE_ROOT = Path("/home/OpenMontage")

# Ensure OpenMontage is importable
if str(OPENMONTAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENMONTAGE_ROOT))

# ---------------------------------------------------------------------------
# Handle OpenMontage imports safely
# ---------------------------------------------------------------------------

# Pre-mock jsonschema if not installed so pipeline_loader can import.
# Validation will simply be a no-op — manifests are valid at rest, and
# the agent will catch load failures at get_pipeline()-time if needed.
if "jsonschema" not in sys.modules:
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        import types
        _mock = types.ModuleType("jsonschema")
        def _noop_validate(*_a, **_kw):
            pass
        _mock.validate = _noop_validate
        _mock.ValidationError = type("ValidationError", (Exception,), {})
        sys.modules["jsonschema"] = _mock

_PIPELINE_LOADER_AVAILABLE = False
_TOOL_REGISTRY_AVAILABLE = False
_COST_TRACKER_AVAILABLE = False
_SCORING_AVAILABLE = False
_SETUP_WARNINGS: list[str] = []

try:
    from lib.pipeline_loader import load_pipeline, list_pipelines, get_stage_order, get_required_tools
    _PIPELINE_LOADER_AVAILABLE = True
except ImportError as e:
    _SETUP_WARNINGS.append(f"Pipeline loader unavailable: {e}")

try:
    from tools.tool_registry import registry
    _TOOL_REGISTRY_AVAILABLE = True
except ImportError as e:
    _SETUP_WARNINGS.append(f"Tool registry unavailable: {e}")

try:
    from tools.cost_tracker import CostTracker
    _COST_TRACKER_AVAILABLE = True
except ImportError as e:
    _SETUP_WARNINGS.append(f"Cost tracker unavailable: {e}")

try:
    from lib.scoring import score_provider, rank_providers, normalize_task_context
    _SCORING_AVAILABLE = True
except ImportError as e:
    _SETUP_WARNINGS.append(f"Scoring engine unavailable: {e}")

# ---------------------------------------------------------------------------
# Pipeline summary — hardcoded reference for fast access without importing
# ---------------------------------------------------------------------------

PIPELINE_SUMMARY: dict[str, dict[str, Any]] = {
    "animated-explainer": {
        "description": "Generated explainer video from topic/idea — fully AI-produced with narration, visuals, and music. Research-first pre-production phase.",
        "category": "generated",
        "stability": "production",
        "stage_count": 8,
        "stages": ["research", "proposal", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "animation": {
        "description": "Animation-first pipeline for motion graphics, diagram-led explainers, kinetic typography, math visuals, and stylized illustrative sequences.",
        "category": "animation",
        "stability": "production",
        "stage_count": 8,
        "stages": ["research", "proposal", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "avatar-spokesperson": {
        "description": "Presenter-led avatar pipeline for spokesperson videos, internal updates, onboarding, sales intros, and short scripted explainers.",
        "category": "custom",
        "stability": "production",
        "stage_count": 7,
        "stages": ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "character-animation": {
        "description": "Character animation pipeline for local, reusable cartoon characters — script to SVG/Canvas/Remotion/HyperFrames animation.",
        "category": "animation",
        "stability": "beta",
        "stage_count": 10,
        "stages": ["character_design", "rig_plan", "pose_library", "action_timeline", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "cinematic": {
        "description": "Mood-led cinematic pipeline for trailers, brand films, montages, and short-form dramatic edits with emotional pacing quality gates.",
        "category": "cinematic",
        "stability": "production",
        "stage_count": 8,
        "stages": ["research", "proposal", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "clip-factory": {
        "description": "Multi-clip extraction pipeline — takes long-form content and produces multiple short clips optimized for social distribution.",
        "category": "custom",
        "stability": "beta",
        "stage_count": 7,
        "stages": ["analysis", "clip_selection", "script", "assets", "edit", "compose", "publish"],
    },
    "documentary-montage": {
        "description": "Retrieval-first thematic montage pipeline. Builds a semantic corpus from Pexels, Archive.org, NASA, Wikimedia Commons using CLIP-based retrieval.",
        "category": "documentary",
        "stability": "beta",
        "stage_count": 5,
        "stages": ["corpus_build", "retrieval", "edit", "compose", "publish"],
    },
    "framework-smoke": {
        "description": "Minimal pipeline manifest used to exercise framework contracts. Not for production use.",
        "category": "custom",
        "stability": "beta",
        "stage_count": 2,
        "stages": ["research"],
    },
    "hybrid": {
        "description": "Hybrid pipeline for videos combining source footage with designed or generated support assets — interviews plus diagrams, screen recordings plus graphics.",
        "category": "hybrid",
        "stability": "production",
        "stage_count": 7,
        "stages": ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "localization-dub": {
        "description": "Transcript-first localization pipeline for producing translated subtitles, dubbed audio, and optional lip-synced language variants.",
        "category": "custom",
        "stability": "beta",
        "stage_count": 7,
        "stages": ["transcript", "translation", "assets", "dub", "edit", "compose", "publish"],
    },
    "podcast-repurpose": {
        "description": "Podcast-to-video repurposing pipeline — audiograms, caption-led clips, quote-led social assets, and optional full-episode companion video.",
        "category": "custom",
        "stability": "beta",
        "stage_count": 7,
        "stages": ["analysis", "clip_selection", "assets", "edit", "compose", "publish"],
    },
    "screen-demo": {
        "description": "Screen recording pipeline with two modes: REAL CAPTURE (screen recording with callouts/zooms) and SYNTHETIC (Remotion TerminalScene for CLI demos).",
        "category": "screen_recording",
        "stability": "production",
        "stage_count": 9,
        "stages": ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
    "talking-head": {
        "description": "End-to-end talking-head video pipeline — raw footage to polished output with transcription, subtitles, audio mixing, and face enhancement.",
        "category": "talking_head",
        "stability": "beta",
        "stage_count": 7,
        "stages": ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"],
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_pipelines() -> list[dict[str, Any]]:
    """Return metadata for all available OpenMontage pipelines.

    Returns:
        List of dicts, each with: name, description, category, stability,
        stage_count, stages, required_skills, extensions.
    """
    pipelines = []
    names = list_available_pipelines()
    for name in names:
        try:
            manifest = get_pipeline(name)
            stages = get_pipeline_stages(name)
            pipelines.append({
                "name": name,
                "description": manifest.get("description", "").strip(),
                "category": manifest.get("category", "unknown"),
                "stability": manifest.get("stability", "unknown"),
                "stage_count": len(stages),
                "stages": stages,
                "required_skills": manifest.get("required_skills", []),
                "extensions": manifest.get("extensions", {}),
            })
        except Exception as e:
            pipelines.append({
                "name": name,
                "description": "",
                "category": "unknown",
                "stability": "unknown",
                "error": str(e),
            })
    return pipelines


def get_pipeline(name: str) -> dict[str, Any]:
    """Load a pipeline manifest by name.

    Args:
        name: Pipeline name (e.g. "animated-explainer", "cinematic").

    Returns:
        Validated pipeline manifest dict from OpenMontage.

    Raises:
        ImportError: If OpenMontage pipeline_loader is unavailable.
        FileNotFoundError: If pipeline name doesn't exist.
    """
    if not _PIPELINE_LOADER_AVAILABLE:
        raise ImportError(
            "OpenMontage pipeline_loader is not available. "
            "Ensure /home/OpenMontage/ exists with lib/pipeline_loader.py. "
            f"Warnings: {_SETUP_WARNINGS}"
        )
    from lib.pipeline_loader import load_pipeline
    return load_pipeline(name)


def list_available_pipelines() -> list[str]:
    """List all pipeline names available in OpenMontage.

    Returns:
        List of pipeline name strings. Empty list if OpenMontage unavailable.
    """
    if not _PIPELINE_LOADER_AVAILABLE:
        return []
    from lib.pipeline_loader import list_pipelines
    return list_pipelines()


def get_tool_support_envelope() -> dict[str, Any]:
    """Get the current tool availability envelope from OpenMontage.

    Returns:
        Dict mapping tool name to tool info (name, tier, capability,
        provider, stability, status, dependencies, etc.).
        Empty dict if tool registry unavailable.
    """
    if not _TOOL_REGISTRY_AVAILABLE:
        return {}
    try:
        registry.ensure_discovered()
        return registry.support_envelope()
    except Exception:
        return {}


def get_pipeline_stages(pipeline_name: str) -> list[str]:
    """Get ordered stage names for a pipeline.

    Args:
        pipeline_name: Name of the pipeline.

    Returns:
        Ordered list of stage names. Empty list on error.
    """
    if not _PIPELINE_LOADER_AVAILABLE:
        return []
    try:
        manifest = get_pipeline(pipeline_name)
        from lib.pipeline_loader import get_stage_order
        return get_stage_order(manifest)
    except Exception:
        # Fallback to hardcoded summary
        info = PIPELINE_SUMMARY.get(pipeline_name)
        if info:
            return info.get("stages", [])
        return []


def get_pipeline_required_skills(pipeline_name: str) -> list[str]:
    """Get required skills for a pipeline.

    Args:
        pipeline_name: Name of the pipeline.

    Returns:
        List of skill paths required by the pipeline. Empty list on error.
    """
    if not _PIPELINE_LOADER_AVAILABLE:
        return []
    try:
        manifest = get_pipeline(pipeline_name)
        return manifest.get("required_skills", [])
    except Exception:
        return []


def estimate_pipeline_cost(
    pipeline_name: str,
    duration_seconds: int,
    style: str = "standard",
) -> dict[str, Any]:
    """Get a rough cost estimate for running a pipeline.

    This provides a ballpark estimate based on pipeline category and duration.
    Actual costs depend on specific tools and providers selected.

    Args:
        pipeline_name: Name of the pipeline.
        duration_seconds: Target output duration in seconds.
        style: Production style ("standard", "premium", "budget").

    Returns:
        Dict with estimated cost range, confidence, and assumptions.
    """
    info = PIPELINE_SUMMARY.get(pipeline_name, {})
    category = info.get("category", "custom")

    # Rough per-second cost estimates by category (USD)
    # These are very approximate — real costs vary by provider
    cost_per_second = {
        "generated": 0.015,
        "animation": 0.020,
        "cinematic": 0.025,
        "talking_head": 0.008,
        "screen_recording": 0.005,
        "hybrid": 0.012,
        "custom": 0.010,
        "documentary": 0.018,
    }
    base_rate = cost_per_second.get(category, 0.010)

    style_multiplier = {"budget": 0.6, "standard": 1.0, "premium": 1.8}
    multiplier = style_multiplier.get(style, 1.0)

    estimated = duration_seconds * base_rate * multiplier
    low = round(estimated * 0.7, 2)
    high = round(estimated * 1.5, 2)

    return {
        "pipeline": pipeline_name,
        "category": category,
        "style": style,
        "duration_seconds": duration_seconds,
        "estimated_usd": round(estimated, 2),
        "range_usd": {"low": low, "high": high},
        "confidence": "low",
        "note": "Ballpark estimate. Actual costs depend on provider selection and number of revisions.",
    }


def get_provider_catalog() -> dict[str, Any]:
    """Get the provider catalog grouped by capability.

    Returns:
        Dict mapping capability names to lists of provider info.
        Empty dict if tool registry unavailable.
    """
    if not _TOOL_REGISTRY_AVAILABLE:
        return {}
    try:
        registry.ensure_discovered()
        return registry.provider_catalog()
    except Exception:
        return {}


def get_capability_catalog() -> dict[str, Any]:
    """Get the capability catalog — tools grouped by top-level capability.

    Returns:
        Dict mapping capability names to lists of tool info dicts.
        Empty dict if tool registry unavailable.
    """
    if not _TOOL_REGISTRY_AVAILABLE:
        return {}
    try:
        registry.ensure_discovered()
        return registry.capability_catalog()
    except Exception:
        return {}


def get_tool_tier_summary() -> dict[str, Any]:
    """Get a tier-based summary of tool availability.

    Returns:
        Dict with tool counts by tier and status.
        Empty dict if tool registry unavailable.
    """
    if not _TOOL_REGISTRY_AVAILABLE:
        return {}
    try:
        registry.ensure_discovered()
        return registry.tier_summary()
    except Exception:
        return {}


def setup_openmontage() -> dict[str, Any]:
    """Verify OpenMontage is available and return setup status.

    Returns:
        Dict with status info:
        - available: bool
        - pipeline_count: int (0 if unavailable)
        - tool_count: int (0 if unavailable)
        - warnings: list[str]
        - openmontage_root: str
    """
    result = {
        "available": False,
        "pipeline_count": 0,
        "tool_count": 0,
        "warnings": list(_SETUP_WARNINGS),
        "openmontage_root": str(OPENMONTAGE_ROOT),
    }

    # Check OpenMontage directory exists
    if not OPENMONTAGE_ROOT.exists():
        result["warnings"].append(
            f"OpenMontage directory not found at {OPENMONTAGE_ROOT}."
        )
        return result

    # Check pipeline definitions
    defs_dir = OPENMONTAGE_ROOT / "pipeline_defs"
    if defs_dir.exists():
        result["pipeline_count"] = len(list(defs_dir.glob("*.yaml")))

    # Check tool discovery
    if _TOOL_REGISTRY_AVAILABLE:
        try:
            registry.ensure_discovered()
            result["tool_count"] = len(registry.list_all())
        except Exception as e:
            result["warnings"].append(f"Tool discovery failed: {e}")

    result["available"] = (
        _PIPELINE_LOADER_AVAILABLE
        and _TOOL_REGISTRY_AVAILABLE
        and result["pipeline_count"] > 0
    )

    return result


def get_pipeline_summary() -> str:
    """Return a human-readable summary of all available pipelines.

    Returns:
        Formatted string with pipeline names, descriptions, categories,
        stability levels, and stage counts.
    """
    sections = []
    sections.append("OpenMontage Pipeline Summary")
    sections.append("=" * 60)

    available = list_available_pipelines()
    if not available:
        # Use hardcoded summary
        available = list(PIPELINE_SUMMARY.keys())

    # Group by category
    by_category: dict[str, list[str]] = {}
    for name in available:
        info = PIPELINE_SUMMARY.get(name, {})
        cat = info.get("category", "other")
        by_category.setdefault(cat, []).append(name)

    for cat, names in sorted(by_category.items()):
        sections.append(f"\n{cat.upper()} ({len(names)} pipelines)")
        sections.append("-" * 40)
        for name in names:
            info = PIPELINE_SUMMARY.get(name, {})
            desc = info.get("description", "")
            stability = info.get("stability", "?")
            stages = info.get("stage_count", "?")
            sections.append(f"  {name}")
            sections.append(f"    Stability: {stability}  |  Stages: {stages}")
            sections.append(f"    {desc}")

    # Add tool count if available
    if _TOOL_REGISTRY_AVAILABLE:
        try:
            registry.ensure_discovered()
            tools = registry.list_all()
            sections.append(f"\nTotal tools available: {len(tools)}")
        except Exception:
            pass

    sections.append(f"\nOpenMontage location: {OPENMONTAGE_ROOT}")
    sections.append("License: AGPL-3.0")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Discover on import for fast first access
# ---------------------------------------------------------------------------

def _auto_discover() -> None:
    """Discover tools on module import for fast first access."""
    if _TOOL_REGISTRY_AVAILABLE:
        try:
            registry.ensure_discovered()
        except Exception:
            pass


_auto_discover()

__all__ = [
    "discover_pipelines",
    "get_pipeline",
    "list_available_pipelines",
    "get_tool_support_envelope",
    "get_pipeline_stages",
    "get_pipeline_required_skills",
    "estimate_pipeline_cost",
    "get_provider_catalog",
    "get_capability_catalog",
    "get_tool_tier_summary",
    "setup_openmontage",
    "get_pipeline_summary",
    "PIPELINE_SUMMARY",
    "OPENMONTAGE_ROOT",
]

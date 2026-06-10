"""
Platform Adapter System — Hermes-inspired plugin architecture
=============================================================
Auto-discovers platform adapters in subdirectories.
Each adapter is a module with:
  - PLATFORM: str          — Platform name constant
  - post(text, media, ...) — Post content to platform
  - validate_credentials() — Test if credentials work
  - AGENTS.md              — Self-documentation

Usage:
    from adapters import discover_adapters, post_to_platform
    adapters = discover_adapters()
    result = post_to_platform("bluesky", text="Hello!")
"""

import importlib
import json
import os
import sys
import pkgutil
from pathlib import Path

ADAPTERS_DIR = Path(__file__).parent


def discover_adapters() -> dict:
    """Discover all available platform adapters.

    Returns:
        dict of {platform_name: module}
    """
    adapters = {}

    # Scan adapters directory for subdirectories with __init__.py
    for item in ADAPTERS_DIR.iterdir():
        if not item.is_dir() or item.name.startswith("_") or item.name.startswith("."):
            continue
        init_file = item / "__init__.py"
        if not init_file.exists():
            continue

        try:
            # Import the adapter module
            module_name = f"adapters.{item.name}"
            if module_name not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    module_name, init_file
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)
                else:
                    continue
            else:
                mod = sys.modules[module_name]

            # Validate adapter has required exports
            if not hasattr(mod, "PLATFORM"):
                continue

            platform = mod.PLATFORM
            adapters[platform] = mod

        except Exception as e:
            print(f"  ⚠ Adapter '{item.name}' failed to load: {e}", file=sys.stderr)

    return adapters


def post_to_platform(platform: str, text: str = "", media: str = "",
                     schedule: str = "", hashtags: list = None,
                     first_comment: str = "", dry_run: bool = False) -> dict:
    """Post content to a specific platform using its adapter.

    Args:
        platform: Platform name (e.g. 'bluesky', 'twitter')
        text: Post text content
        media: Path to media file
        schedule: ISO datetime for scheduling
        hashtags: List of hashtag strings
        first_comment: First comment to post after main content
        dry_run: If True, simulate without actually posting

    Returns:
        dict with keys: success (bool), message (str), data (dict)
    """
    adapters = discover_adapters()
    if platform not in adapters:
        return {
            "success": False,
            "message": f"No adapter found for '{platform}'. Available: {', '.join(adapters.keys())}",
            "data": None,
        }

    mod = adapters[platform]

    # Check if adapter has post function
    if not hasattr(mod, "post"):
        return {
            "success": False,
            "message": f"Adapter '{platform}' has no post() function",
            "data": None,
        }

    try:
        result = mod.post(
            text=text,
            media=media,
            schedule=schedule,
            hashtags=hashtags or [],
            first_comment=first_comment,
            dry_run=dry_run,
        )
        return {"success": True, "message": f"Posted to {platform}", "data": result}
    except Exception as e:
        return {"success": False, "message": f"Adapter '{platform}' error: {e}", "data": None}


def list_adapters() -> list:
    """List all available adapters with metadata."""
    adapters = discover_adapters()
    result = []
    for name, mod in sorted(adapters.items()):
        info = {
            "platform": name,
            "description": getattr(mod, "__doc__", "").strip() or "",
            "has_post": hasattr(mod, "post"),
            "has_validate": hasattr(mod, "validate_credentials"),
        }
        result.append(info)
    return result

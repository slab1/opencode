# Platform Adapters — AGENTS.md

This directory contains pluggable platform adapter modules. Each adapter
encapsulates the logic for posting to a specific social media platform
using its native API (not through a backend like BulkPublish).

**Inspired by:** Hermes Agent gateway/platform adapter architecture.

---

## How It Works

1. Each subdirectory is a self-contained adapter module
2. Modules are auto-discovered at runtime by `__init__.py` (no registration needed)
3. Each adapter must export: `PLATFORM`, `post()`, and optionally `validate_credentials()`
4. `post.sh --adapter <name>` invokes the adapter directly (bypassing backends)

---

## Creating a New Adapter

Create `adapters/<name>/` directory with:

### Required exports in `__init__.py`:

```python
"""My Platform adapter — posts text and media."""
from pathlib import Path

PLATFORM = "myplatform"  # Must match the directory name

def post(text: str = "", media: str = "", schedule: str = "",
         hashtags: list = None, first_comment: str = "",
         dry_run: bool = False) -> dict:
    \"\"\"Post content to MyPlatform.

    Args:
        text: Post text content
        media: Path to media file
        schedule: ISO datetime for scheduling
        hashtags: List of hashtags
        first_comment: First comment text
        dry_run: If True, simulate only

    Returns:
        dict with keys: success, post_url, post_id, error
    \"\"\"
    if dry_run:
        return {"success": True, "post_url": None, "post_id": None, "error": None}
    # ... actual API call
    pass

def validate_credentials() -> bool:
    \"\"\"Test if stored credentials work.\"\"\"
    pass
```

### Optional:
- `AGENTS.md` — Self-documentation for the adapter

---

## Available Adapters

| Adapter | Status | Type | Auth Method |
|---------|--------|------|-------------|
| voicebox | ✅ Active | Local API (REST + MCP) | Local app check (no API key) |
| bluesky | ✅ Active | AT Protocol API | App password |

## Testing

```bash
# List all adapters
python3 -c "from adapters import list_adapters; print(list_adapters())"

# Test an adapter
python3 -c "from adapters import post_to_platform; print(post_to_platform('bluesky', text='test', dry_run=True))"
```

"""
Bluesky Adapter — posts via the AT Protocol (com.apple.bsky.Feed)
==================================================================
Uses Bluesky's native API for posting text and images.
No backend required — works with just a handle + app password.

Credentials:  stored in tokens/bluesky_handle.token, tokens/bluesky_password.token

Limitations:
  - 300 character limit per post
  - No native scheduling (post.sh handles scheduling)
  - Image upload supported via blob.bsky.social

Requires: pip install atproto
"""

import json
import os
import sys
from pathlib import Path

PLATFORM = "bluesky"

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"
TOKENS_DIR = PLATFORMS_DIR / "tokens"


def _get_credentials() -> tuple:
    """Get Bluesky handle and app password from token files."""
    handle_file = TOKENS_DIR / "bluesky_handle.token"
    pass_file = TOKENS_DIR / "bluesky_password.token"

    handle = handle_file.read_text().strip() if handle_file.exists() else ""
    password = pass_file.read_text().strip() if pass_file.exists() else ""

    return handle, password


def validate_credentials() -> bool:
    """Test if Bluesky credentials work by attempting to connect."""
    handle, password = _get_credentials()
    if not handle or not password:
        return False

    try:
        from atproto import Client
        client = Client()
        client.login(handle, password)
        return True
    except Exception:
        return False


def post(text: str = "", media: str = "", schedule: str = "",
         hashtags: list = None, first_comment: str = "",
         dry_run: bool = False) -> dict:
    """Post content to Bluesky.

    Args:
        text: Post text (max 300 chars)
        media: Path to image file (optional)
        schedule: Not supported by Bluesky API — use post.sh scheduling
        hashtags: List of hashtags (appended inline)
        first_comment: Not supported by Bluesky API directly
        dry_run: If True, simulate without actual posting

    Returns:
        dict with keys: success, post_url, post_id, error
    """
    handle, password = _get_credentials()
    if not handle or not password:
        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": "Bluesky not configured. Run setup-wizard.sh or create tokens/bluesky_handle.token and tokens/bluesky_password.token",
        }

    # Build post text
    post_text = text
    if hashtags:
        hashtag_str = " ".join(f"#{h}" if not h.startswith("#") else h for h in hashtags)
        post_text = f"{post_text}\n\n{hashtag_str}" if post_text else hashtag_str

    # Truncate to 300 chars
    if len(post_text) > 300:
        post_text = post_text[:297] + "..."

    if dry_run:
        return {
            "success": True,
            "post_url": None,
            "post_id": None,
            "error": None,
            "preview": {
                "text": post_text,
                "media": media or None,
                "handle": handle,
            }
        }

    try:
        from atproto import Client, models

        client = Client()
        client.login(handle, password)

        embed = None
        if media and Path(media).exists():
            # Upload image
            with open(media, "rb") as f:
                img_data = f.read()
            upload = client.upload_blob(img_data)
            embed = models.AppBskyEmbedImages.Main(
                images=[models.AppBskyEmbedImages.Image(alt="", image=upload.blob)]
            )

        result = client.send_post(text=post_text, embed=embed)

        return {
            "success": True,
            "post_url": f"https://bsky.app/profile/{handle}/post/{result.uri.split('/')[-1]}",
            "post_id": result.uri,
            "error": None,
        }

    except ImportError:
        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": "atproto not installed. Run: pip install atproto",
        }
    except Exception as e:
        return {
            "success": False,
            "post_url": None,
            "post_id": None,
            "error": str(e),
        }

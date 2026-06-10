#!/bin/bash
# ============================================================
# pre-post.sh — Pre-posting hook
# ============================================================
# Runs BEFORE posting to each platform.
# Return non-zero to ABORT the post.
#
# Environment variables available:
#   PLATFORM    — target platform (e.g., twitter, linkedin)
#   TEXT        — post text content
#   MEDIA       — media file path (may be empty)
#   SCHEDULE    — ISO datetime or "now"
#   URL         — link to attach
#   HASHTAGS    — comma-separated hashtags
#   DRY_RUN     — "true" or "false"
#   BACKEND     — configured backend
#
# Example: validate text isn't empty or too short
# ============================================================
set -e

# Example: Abort if text is too short for a meaningful post
if [ "${#TEXT}" -lt 10 ] && [ "$DRY_RUN" = "false" ]; then
    echo "[pre-post] ✗ Text too short (${#TEXT} chars), aborting"
    exit 1
fi

# Example: Warn about missing media for Instagram
if [ "$PLATFORM" = "instagram" ] && [ -z "$MEDIA" ] && [ "$DRY_RUN" = "false" ]; then
    echo "[pre-post] ⚠ Instagram post without media — continuing anyway"
fi

echo "[pre-post] ✓ Pre-flight passed for $PLATFORM"
exit 0

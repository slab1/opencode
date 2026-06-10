#!/bin/bash
# ============================================================
# post-post.sh — Post-publishing hook
# ============================================================
# Runs AFTER posting to each platform.
#
# Environment variables available:
#   PLATFORM    — target platform (e.g., twitter, linkedin)
#   TEXT        — post text content
#   MEDIA       — media file path (may be empty)
#   SCHEDULE    — ISO datetime or "now"
#   URL         — link to attach
#   HASHTAGS    — comma-separated hashtags
#   POST_ID     — unique post ID from post.sh
#   SUCCESS     — "true" or "false"
#   RESPONSE    — API response (first 200 chars)
#
# Example: log to a custom tracker, send notification, update dashboard
# ============================================================

# Example: Log to a custom notifications file
if [ "$SUCCESS" = "true" ]; then
    echo "[post-post] ✓ $PLATFORM post $POST_ID published successfully"
    # You could add: notify-send, webhook, Slack notification, etc.
else
    echo "[post-post] ✗ $PLATFORM post $POST_ID failed"
fi

exit 0

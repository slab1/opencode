#!/bin/sh
# ── Aether Core Pulse ──────────────────────────────────────────────
# Project Aether: Autonomic Nervous System.
# Runs the cognitive evolution loop periodically via cron.
# Triggers memory consolidation + logic evolution + capability audit.
# ───────────────────────────────────────────────────────────────────

CONFIG_DIR="${HOME:-/root}/.config/opencode"
LOG_FILE="$CONFIG_DIR/aether_pulse.log"
LOCK_FILE="/tmp/opencode-aether.lock"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"; }

# Single-instance guard
if [ -f "$LOCK_FILE" ]; then
    read -r pid < "$LOCK_FILE" 2>/dev/null
    if kill -0 "$pid" 2>/dev/null; then
        log "Aether pulse already running (pid $pid); skipping."
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi
echo $$ > "$LOCK_FILE"

log "Aether pulse started"

# 1. Run the Aether Core cognitive pulse (memory consolidation + evolution)
python3 "$CONFIG_DIR/shared/aether_core.py" >> "$LOG_FILE" 2>&1

# 2. Periodic handoff record for cross-session memory
python3 -m opencode_improvement memory --handoff >> "$LOG_FILE" 2>&1

rm -f "$LOCK_FILE"
log "Aether pulse complete"
exit 0

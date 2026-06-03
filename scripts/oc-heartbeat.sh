#!/bin/sh
# ── OpenCode Heartbeat ─────────────────────────────────────────────
# Periodic system health + context collector.
# Runs via cron every ~30 minutes. Writes status into shared context.
# Agents read heartbeat data when they start sessions.
# ───────────────────────────────────────────────────────────────────

CONFIG_DIR="${HOME:-/root}/.config/opencode"
SHARED_DIR="$CONFIG_DIR/shared"
CONTEXT_JSON="$SHARED_DIR/context.json"
MEMORY_DIR="$CONFIG_DIR/memory"
LOCK_FILE="/tmp/opencode-heartbeat.lock"
LOG_FILE="$CONFIG_DIR/heartbeat.log"
WORKSPACE="/home/Codes"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"; }

# Single-instance guard
if [ -f "$LOCK_FILE" ]; then
    read -r pid < "$LOCK_FILE" 2>/dev/null
    if kill -0 "$pid" 2>/dev/null; then
        log "Already running (pid $pid). Skipping."
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

log "=== Heartbeat started ==="

# ── 1. Workspace state ──
WORKSPACE_STATE="unknown"
GIT_BRANCH=""
GIT_DIRTY=0
GIT_AHEAD=0

if [ -d "$WORKSPACE/.git" ]; then
    WORKSPACE_STATE="git"
    GIT_BRANCH=$(cd "$WORKSPACE" && git rev-parse --abbrev-ref HEAD 2>/dev/null)
    GIT_DIRTY=$(cd "$WORKSPACE" && git status --porcelain 2>/dev/null | wc -l)
    GIT_AHEAD=$(cd "$WORKSPACE" && git log --oneline @{u}.. 2>/dev/null | wc -l)
fi

log "Workspace: $WORKSPACE_STATE | branch=$GIT_BRANCH dirty=$GIT_DIRTY ahead=$GIT_AHEAD"

# ── 2. System health ──
CPU_LOAD=$(cat /proc/loadavg 2>/dev/null | awk '{print $1","$2","$3}')
MEM_PCT=$(free 2>/dev/null | awk '/Mem:/{printf "%.0f", ($3/$2)*100}')
DISK_PCT=$(df / 2>/dev/null | awk 'NR>1{print $5}' | tr -d '%')

log "System: cpu=$CPU_LOAD mem=${MEM_PCT}% disk=${DISK_PCT}%"

# ── 3. OpenCode agents status ──
AGENT_COUNT=$(ls "$CONFIG_DIR/agents/"*.md 2>/dev/null | wc -l)
PLUGIN_COUNT=$(ls /home/.cache/opencode/packages/ 2>/dev/null | wc -l)
MEMORY_NOTES=$(ls "$MEMORY_DIR/"*.md 2>/dev/null | wc -l)

log "OpenCode: agents=$AGENT_COUNT plugins=$PLUGIN_COUNT memory_notes=$MEMORY_NOTES"

# ── 4. Write to shared context via Python (avoids shell quoting issues) ──
python3 << PYEOF 2>&1
import json, os, subprocess, datetime, time

config_dir = "${CONFIG_DIR}"
context_path = "${CONTEXT_JSON}"
workspace = "${WORKSPACE}"

# Build heartbeat data programmatically
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# Workspace
git_branch = "${GIT_BRANCH}"
workspace_state = "${WORKSPACE_STATE}"
git_dirty = int("${GIT_DIRTY}" or 0)
git_ahead = int("${GIT_AHEAD}" or 0)

# System
cpu_load = "${CPU_LOAD}"
mem_pct = int("${MEM_PCT}" or 0)
disk_pct = int("${DISK_PCT}" or 0)

# OpenCode
agent_count = int("${AGENT_COUNT}" or 0)
plugin_count = int("${PLUGIN_COUNT}" or 0)
memory_notes = int("${MEMORY_NOTES}" or 0)

entry = {
    "timestamp": now,
    "workspace": {
        "state": workspace_state,
        "branch": git_branch,
        "dirty_files": git_dirty,
        "commits_ahead": git_ahead
    },
    "system": {
        "cpu_load": [float(x) for x in cpu_load.split(",") if x.strip()] or [0.0],
        "memory_percent": mem_pct,
        "disk_percent": disk_pct
    },
    "opencode": {
        "agents": agent_count,
        "plugins": plugin_count,
        "memory_notes": memory_notes
    }
}

# Read existing context
try:
    with open(context_path) as f:
        ctx = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    ctx = {}

if 'heartbeat' not in ctx:
    ctx['heartbeat'] = []
ctx['heartbeat'].append(entry)
# Keep last 24 heartbeats
if len(ctx['heartbeat']) > 24:
    ctx['heartbeat'] = ctx['heartbeat'][-24:]

with open(context_path, 'w') as f:
    json.dump(ctx, f, indent=2)

print("Context updated successfully")
PYEOF

if [ $? -eq 0 ]; then
    log "Context updated"
else
    log "WARN: Failed to update context"
fi

log "=== Heartbeat complete ==="
echo "Heartbeat complete: $(date)"

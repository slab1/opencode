# OpenCode Session State Tracker

This file tracks session state for auto-resume functionality.

## Current State

| Field | Value |
|-------|-------|
| **Last Session ID** | (auto-updated) |
| **Last Active Agent** | (auto-updated) |
| **Last Activity** | (auto-updated) |
| **Session Title** | (auto-updated) |
| **Offline Time** | (auto-updated) |
| **Resume Point** | (auto-updated) |

## Shared Context Integration

The session state is now integrated with the shared context system:

| Session Field | Shared Context Location (context.json) |
|---------------|----------------------------------------|
| Session ID | `session.current_id` |
| Session Title | `session.current_title` |
| Active Agents | `session.active_agents` |
| Workflow Pattern | `session.workflow_pattern` |
| Start Time | `session.started_at` |
| Last Updated | `state.last_updated_at` |
| Last Agent | `state.last_updated_by` |

**On session resume**, the orchestrator should:
1. Read `context.json` to find the previous session's context
2. Check if there's an incomplete workflow (non-empty `active_agents`)
3. Offer to continue the workflow or start fresh

**On session clear/reset**, the context should be reset to initial state (see `oc-context clear`).

## Auto-Resume Logic

### When Going Offline
1. System detects disconnection
2. Current session ID is saved
3. Last active agent is recorded
4. Timestamp is stored

### When Coming Back Online
1. System detects reconnection
2. Checks for saved session state
3. Prompts: "Continue session '[Title]' with @[agent]? [Y/n]"
4. If yes: `opencode --continue --session <ID>`
5. If no: Start fresh session

## Implementation

### Shell Script: `~/.local/share/opencode/auto-resume.sh`

```bash
#!/bin/bash
# OpenCode Auto-Resume Script

STATE_FILE="$HOME/.config/opencode/SESSION_STATE.md"
DB_FILE="$HOME/.local/share/opencode/opencode.db"

# Function to get last session
get_last_session() {
  sqlite3 "$DB_FILE" "SELECT id, title, updated FROM sessions ORDER BY updated DESC LIMIT 1;" 2>/dev/null
}

# Function to save state
save_state() {
  local session_id="$1"
  local agent="$2"
  local timestamp=$(date -Iseconds)
  
  # Update SESSION_STATE.md
  cat > "$STATE_FILE" << EOF
# OpenCode Session State Tracker

## Current State

| Field | Value |
|-------|-------|
| **Last Session ID** | $session_id |
| **Last Active Agent** | $agent |
| **Last Activity** | $timestamp |
| **Session Title** | (see database) |
| **Offline Time** | $timestamp |
| **Resume Point** | Auto-detected |

## Resume Command

\`\`\`bash
opencode --continue --session $session_id
\`\`\`
EOF
}

# Function to check and resume
check_resume() {
  if [ -f "$STATE_FILE" ]; then
    local last_session=$(grep "Last Session ID" "$STATE_FILE" | cut -d'|' -f3 | tr -d ' ')
    
    if [ -n "$last_session" ]; then
      echo "Found previous session: $last_session"
      echo "Resume? [Y/n]"
      read -r response
      
      if [[ "$response" =~ ^[Yy]$ ]] || [[ -z "$response" ]]; then
        echo "Resuming session..."
        opencode --continue --session "$last_session"
        return 0
      fi
    fi
  fi
  
  echo "Starting new session..."
  opencode
}

# Main
case "$1" in
  save)
    save_state "$2" "$3"
    ;;
  resume)
    check_resume
    ;;
  *)
    echo "Usage: $0 {save|resume}"
    exit 1
    ;;
esac
```

## Usage

### Manual Resume
```bash
# Check for previous session
bash ~/.local/share/opencode/auto-resume.sh resume

# Or use opencode directly
opencode --continue
```

### Automatic Resume (Future Enhancement)
Add to shell profile (`~/.bashrc` or `~/.zshrc`):
```bash
# Auto-resume OpenCode on terminal start
if command -v opencode &> /dev/null; then
  opencode --continue 2>/dev/null || opencode
fi
```

## Notes

- OpenCode's `--continue` flag automatically resumes the last session
- The `-s/--session` flag allows resuming a specific session
- Session state is stored in SQLite database at `~/.local/share/opencode/opencode.db`
- This is a lightweight wrapper to provide better UX around existing functionality

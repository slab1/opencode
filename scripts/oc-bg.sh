#!/bin/sh
# oc-bg - Run an OpenCode agent in the background
# Usage: oc-bg <agent> <message>
#        oc-bg list                 # list running background agents
#        oc-bg status <pid>         # check if a background agent is still running
#        oc-bg log <pid>            # tail the output of a background agent
#        oc-bg kill <pid>           # kill a running background agent
#        oc-bg clean                # remove completed background agent logs
#        oc-bg attach <pid>         # attach to a running agent's output (tail -f)
#
# Each background agent gets:
#   - A log file at /tmp/oc-bg/<pid>.log
#   - A pid file at /tmp/oc-bg/<pid>.pid
#   - A meta file at /tmp/oc-bg/<pid>.meta (agent name, message, start time)

set -e

BG_DIR="/tmp/oc-bg"
mkdir -p "$BG_DIR"

run_bg() {
    agent="$1"
    shift
    message="$*"
    if [ -z "$agent" ] || [ -z "$message" ]; then
        echo "Usage: oc-bg <agent> <message>"
        echo "       oc-bg list | status <pid> | log <pid> | kill <pid> | clean | attach <pid>"
        exit 1
    fi
    pid=$$
    # We need a unique ID - use a timestamp
    bg_id="$(date +%s)-$$"
    log_file="$BG_DIR/$bg_id.log"
    meta_file="$BG_DIR/$bg_id.meta"
    
    # Write meta
    cat > "$meta_file" << EOF
agent=$agent
message=$message
started=$(date -Iseconds 2>/dev/null || date)
EOF
    
    # Spawn background opencode run
    # Use --dangerously-skip-permissions to avoid permission prompts in non-interactive mode
    cd "${OPENCODE_DIR:-/home}"
    nohup opencode run --agent "$agent" --dangerously-skip-permissions "$message" > "$log_file" 2>&1 &
    bg_pid=$!
    echo "$bg_pid" > "$BG_DIR/$bg_id.pid"
    
    echo "Background agent started:"
    echo "  ID:    $bg_id"
    echo "  PID:   $bg_pid"
    echo "  Agent: $agent"
    echo "  Log:   $log_file"
    echo ""
    echo "Check status: oc-bg status $bg_id"
    echo "Tail log:     oc-bg log $bg_id"
    echo "Attach:       oc-bg attach $bg_id"
}

list_bg() {
    echo "=== Running background agents ==="
    found=0
    for pid_file in "$BG_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        bg_id=$(basename "$pid_file" .pid)
        pid=$(cat "$pid_file")
        meta_file="$BG_DIR/$bg_id.meta"
        if [ -f "$meta_file" ]; then
            agent=$(grep '^agent=' "$meta_file" | cut -d= -f2-)
            message=$(grep '^message=' "$meta_file" | cut -d= -f2-)
        else
            agent="?"
            message="?"
        fi
        if kill -0 "$pid" 2>/dev/null; then
            status="RUNNING"
            found=$((found + 1))
        else
            status="DONE   "
        fi
        printf "  %s  %-20s  pid=%-7s  agent=%-12s  %s\n" "$status" "$bg_id" "$pid" "$agent" "${message:0:40}"
    done
    if [ $found -eq 0 ]; then
        echo "  (no running agents)"
    fi
}

status_bg() {
    bg_id="$1"
    pid_file="$BG_DIR/$bg_id.pid"
    if [ ! -f "$pid_file" ]; then
        echo "No background agent with ID: $bg_id"
        exit 1
    fi
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Background agent $bg_id is RUNNING (pid=$pid)"
        echo "Started:"
        cat "$BG_DIR/$bg_id.meta" 2>/dev/null
    else
        echo "Background agent $bg_id is DONE (was pid=$pid)"
        echo "Final log tail:"
        tail -20 "$BG_DIR/$bg_id.log" 2>/dev/null
    fi
}

log_bg() {
    bg_id="$1"
    log_file="$BG_DIR/$bg_id.log"
    if [ ! -f "$log_file" ]; then
        echo "No log file for: $bg_id"
        exit 1
    fi
    tail -f "$log_file"
}

attach_bg() {
    log_bg "$@"
}

kill_bg() {
    bg_id="$1"
    pid_file="$BG_DIR/$bg_id.pid"
    if [ ! -f "$pid_file" ]; then
        echo "No background agent with ID: $bg_id"
        exit 1
    fi
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        echo "Killed background agent $bg_id (pid=$pid)"
    else
        echo "Background agent $bg_id was not running"
    fi
}

clean_bg() {
    removed=0
    for pid_file in "$BG_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        bg_id=$(basename "$pid_file" .pid)
        pid=$(cat "$pid_file")
        # If not running, remove all 3 files
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$pid_file" "$BG_DIR/$bg_id.log" "$BG_DIR/$bg_id.meta"
            removed=$((removed + 1))
        fi
    done
    echo "Cleaned up $removed completed background agents"
}

case "${1:-}" in
    list|ls|"")
        list_bg
        ;;
    status)
        shift
        status_bg "$@"
        ;;
    log|attach)
        shift
        log_bg "$@"
        ;;
    kill)
        shift
        kill_bg "$@"
        ;;
    clean)
        clean_bg
        ;;
    *)
        # Treat first arg as agent, rest as message
        agent="$1"
        shift
        run_bg "$agent" "$@"
        ;;
esac

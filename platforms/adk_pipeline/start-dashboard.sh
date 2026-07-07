#!/bin/bash
# Start content dashboard
DIR="/root/.config/opencode/platforms/adk_pipeline"
PID_FILE="$DIR/dashboard.pid"

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Dashboard already running (PID $OLD_PID) at http://localhost:8081"
        exit 0
    fi
fi

nohup "$DIR/dashboard/dashboard" > "$DIR/dashboard.log" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
echo "Dashboard started (PID $PID) at http://localhost:8081"

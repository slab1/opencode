#!/bin/bash
# Stop the ADK pipeline web service.
DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/pipeline.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No pipeline PID file found at $PID_FILE"
    echo "Check running processes: ps aux | grep pipeline"
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill "$PID" 2>/dev/null; then
    echo "Pipeline (PID $PID) stopped."
else
    echo "Process $PID not found (already stopped)."
fi
rm -f "$PID_FILE"

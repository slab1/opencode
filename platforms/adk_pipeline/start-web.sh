#!/bin/bash
# Start the ADK pipeline as a background web service.
# Usage: ./start-web.sh [port]
set -e

PORT="${1:-8080}"
DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/pipeline.pid"
LOG_FILE="$DIR/pipeline-web.log"

cd "$DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Pipeline already running (PID $OLD_PID) on port $PORT"
        echo "Stop with: kill $OLD_PID && rm -f $PID_FILE"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Build if needed
if [ ! -f "$DIR/pipeline" ]; then
    echo "Building pipeline..."
    go build -o pipeline . 2>&1
fi

echo "Starting pipeline web service on port $PORT..."
echo "Logs: $LOG_FILE"
nohup "$DIR/pipeline" web --port "$PORT" api webui >> "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

sleep 2
if kill -0 "$PID" 2>/dev/null; then
    echo "Pipeline started (PID $PID)."
    echo "  Web UI:   http://localhost:$PORT"
    echo "  API:      http://localhost:$PORT/api"
    echo "  Stop:     kill $PID && rm -f $PID_FILE"
    echo "  Logs:     tail -f $LOG_FILE"
else
    echo "Pipeline failed to start. Check logs:"
    tail -5 "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

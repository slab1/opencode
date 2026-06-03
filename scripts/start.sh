#!/bin/sh
# ═══════════════════════════════════════════════════════
#  OpenCode Server + CORS Proxy — Quick Start
#  Starts BOTH the OpenCode server AND the CORS proxy.
#
#  Architecture:
#    Plugin (port 9878) → CORS Proxy → OpenCode Server (port 4096)
#
#  The proxy adds `Access-Control-Allow-Origin: *` headers
#  so the Android WebView plugin can connect from file:// URLs.
#
#  Usage:
#    sh scripts/start.sh [server_port] [proxy_port]
#    sh scripts/start.sh 4096 9878
#
#  Then in Acode, press Ctrl+Shift+S to check status,
#  or open the OpenCode AI sidebar panel.
# ═══════════════════════════════════════════════════════

SERVER_PORT="${1:-4096}"
PROXY_PORT="${2:-9878}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROXY_SCRIPT="$SCRIPT_DIR/cors-proxy.js"

echo "=== OpenCode Quick Start ==="
echo "  Server port: $SERVER_PORT"
echo "  Proxy port:  $PROXY_PORT"
echo ""

# ── Cleanup on exit ──────────────────────────────
SERVER_PID=""
PROXY_PID=""
cleanup() {
  echo ""
  echo "Shutting down..."
  if [ -n "$PROXY_PID" ] && kill -0 "$PROXY_PID" 2>/dev/null; then
    echo "  Stopping proxy (PID $PROXY_PID)..."
    kill "$PROXY_PID" 2>/dev/null
  fi
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "  Stopping server (PID $SERVER_PID)..."
    kill "$SERVER_PID" 2>/dev/null
  fi
  echo "Done."
  exit 0
}
trap cleanup INT TERM

# 1. Check what's using the ports
echo "[1] Checking ports..."
for PORT in "$SERVER_PORT" "$PROXY_PORT"; do
  BUSY=""
  if command -v fuser >/dev/null 2>&1; then
    BUSY=$(fuser "$PORT/tcp" 2>/dev/null)
  elif command -v ss >/dev/null 2>&1; then
    BUSY=$(ss -tlnp "sport = :$PORT" 2>/dev/null | grep -v State)
  fi
  if [ -n "$BUSY" ]; then
    echo "  Port $PORT is in use. Killing old process..."
    fuser -k "$PORT/tcp" 2>/dev/null || true
    sleep 1
  else
    echo "  Port $PORT is free."
  fi
done

# 2. Check if opencode is installed
echo ""
echo "[2] Checking opencode..."
if ! command -v opencode >/dev/null 2>&1; then
  echo "  NOT FOUND. Installing..."
  npm install -g opencode-ai
fi
echo "  opencode: $(opencode --version 2>/dev/null || echo 'installed')"

# 3. Start the OpenCode server (background)
echo ""
echo "[3] Starting opencode serve on port $SERVER_PORT..."
OPENCODE_SERVER_PASSWORD="" opencode serve --port "$SERVER_PORT" &
SERVER_PID=$!
echo "  Server PID: $SERVER_PID"

# Give the server a moment to start
sleep 2

# 4. Check if server is running
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "  ERROR: Server failed to start!"
  exit 1
fi
echo "  Server is running."

# 5. Start the CORS proxy (background)
echo ""
echo "[4] Starting CORS proxy on port $PROXY_PORT..."
echo "  (forwards to server on port $SERVER_PORT with CORS headers)"
if [ -f "$PROXY_SCRIPT" ]; then
  node "$PROXY_SCRIPT" \
    --target-port "$SERVER_PORT" \
    --proxy-port "$PROXY_PORT" &
  PROXY_PID=$!
  echo "  Proxy PID: $PROXY_PID"
  sleep 1
else
  echo "  ERROR: $PROXY_SCRIPT not found!"
  cleanup
fi

# 6. Done
echo ""
echo "=== OpenCode is running ==="
echo "  Server: http://127.0.0.1:$SERVER_PORT"
echo "  Proxy:  http://127.0.0.1:$PROXY_PORT"
echo ""
echo "  In Acode plugin:"
echo "    - Default port is $PROXY_PORT (proxy, recommended)"
echo "    - Direct port is $SERVER_PORT (if proxy unavailable)"
echo "    - Press Ctrl+Shift+S to check connection status"
echo "    - Press Ctrl+Shift+D for diagnostics"
echo ""
echo "  Press Ctrl+C to stop everything."
echo ""

# Wait for either process to finish
wait

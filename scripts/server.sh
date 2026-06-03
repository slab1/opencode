#!/bin/sh
# ═══════════════════════════════════════════════════════
#  OpenCode Server Bootstrap
#  Run this in a terminal/shell (Termux, Alpine, etc.)
#  to start the OpenCode server that the Acode plugin
#  connects to.
#
#  Usage:
#    sh opencode-server.sh [start|stop|restart|status]
# ═══════════════════════════════════════════════════════

set -e

PORT="${OPENCODE_PORT:-9876}"
HOST="127.0.0.1"
CORS_PROXY_PORT="${OPENCODE_CORS_PROXY_PORT:-9878}"
OPENCODE_DIR="${HOME:-/root}/.opencode"
mkdir -p "$OPENCODE_DIR"
PID_FILE="$OPENCODE_DIR/opencode-server.pid"
PROXY_PID_FILE="$OPENCODE_DIR/opencode-cors-proxy.pid"
LOG_FILE="$OPENCODE_DIR/opencode-server.log"
PROXY_LOG_FILE="$OPENCODE_DIR/opencode-cors-proxy.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CORS_PROXY_JS="$SCRIPT_DIR/cors-proxy.js"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[OpenCode]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }

# ─── Detect package manager ────────────────────────

detect_pm() {
  if command -v apk >/dev/null 2>&1; then
    echo "apk"
  elif command -v pkg >/dev/null 2>&1; then
    echo "pkg"
  elif command -v apt >/dev/null 2>&1; then
    echo "apt"
  elif command -v apt-get >/dev/null 2>&1; then
    echo "apt-get"
  else
    echo "unknown"
  fi
}

# ─── Pre-flight checks ──────────────────────────────

check_deps() {
  if ! command -v opencode >/dev/null 2>&1; then
    err "opencode is not installed."
    echo "  Install it:"
    echo "    npm install -g opencode-ai"
    PM=$(detect_pm)
    if [ "$PM" = "apk" ]; then
      echo "  Or: apk add nodejs npm && npm install -g opencode-ai"
    elif [ "$PM" = "pkg" ]; then
      echo "  Or: pkg install nodejs && npm install -g opencode-ai"
    elif [ "$PM" = "apt" ] || [ "$PM" = "apt-get" ]; then
      echo "  Or: apt update && apt install -y nodejs npm && npm install -g opencode-ai"
    fi
    exit 1
  fi

  if command -v node >/dev/null 2>&1; then
    ok "Node.js $(node --version 2>/dev/null) detected"
  fi

  local oc_version
  oc_version=$(opencode --version 2>/dev/null || echo "unknown")
  ok "OpenCode v$oc_version detected"
}

# ─── Server management ──────────────────────────────

start_server() {
  check_deps

  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null)
    if kill -0 "$pid" 2>/dev/null; then
      warn "OpenCode server is already running (PID: $pid)"
      echo "  Port: $PORT"
      echo "  URL:  http://$HOST:$PORT"
      start_cors_proxy
      return 0
    else
      warn "Stale PID file found. Removing..."
      rm -f "$PID_FILE"
    fi
  fi

  info "Starting OpenCode server on http://$HOST:$PORT ..."

  nohup opencode serve \
    --hostname "$HOST" \
    --port "$PORT" \
    --print-logs \
    >> "$LOG_FILE" 2>&1 &

  local pid=$!
  echo "$pid" > "$PID_FILE"

  local timeout=15
  local elapsed=0
  while [ $elapsed -lt $timeout ]; do
    if curl -s "http://$HOST:$PORT/session/status" >/dev/null 2>&1; then
      ok "OpenCode server is running (PID: $pid)"
      echo "  URL:  http://$HOST:$PORT"
      echo "  Logs: $LOG_FILE"
      start_cors_proxy
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  err "Server failed to start within ${timeout}s. Check logs:"
  tail -20 "$LOG_FILE" 2>/dev/null || true
  rm -f "$PID_FILE"
  return 1
}

# ─── CORS Proxy ───────────────────────────────────

start_cors_proxy() {
  if [ ! -f "$CORS_PROXY_JS" ]; then
    warn "CORS proxy script not found at $CORS_PROXY_JS"
    warn "The Acode plugin may not connect due to CORS restrictions."
    warn "Install the proxy script alongside server.sh or remove this warning."
    return 0
  fi

  if ! command -v node >/dev/null 2>&1; then
    warn "node not found; cannot start CORS proxy."
    warn "Install Node.js to enable the CORS proxy."
    return 0
  fi

  if [ -f "$PROXY_PID_FILE" ]; then
    local ppid
    ppid=$(cat "$PROXY_PID_FILE" 2>/dev/null)
    if kill -0 "$ppid" 2>/dev/null; then
      ok "CORS proxy already running (PID: $ppid)"
      return 0
    else
      warn "Stale proxy PID file found. Removing..."
      rm -f "$PROXY_PID_FILE"
    fi
  fi

  info "Starting CORS proxy on http://$HOST:$CORS_PROXY_PORT ..."

  nohup node "$CORS_PROXY_JS" \
    --target-port "$PORT" \
    --proxy-port "$CORS_PROXY_PORT" \
    --host "$HOST" \
    >> "$PROXY_LOG_FILE" 2>&1 &

  local ppid=$!
  echo "$ppid" > "$PROXY_PID_FILE"

  sleep 1
  if kill -0 "$ppid" 2>/dev/null; then
    ok "CORS proxy is running (PID: $ppid)"
    echo "  Proxy: http://$HOST:$CORS_PROXY_PORT (adds CORS headers)"
    echo "  Target: http://$HOST:$PORT (OpenCode server)"
  else
    err "CORS proxy failed to start."
    tail -5 "$PROXY_LOG_FILE" 2>/dev/null || true
    rm -f "$PROXY_PID_FILE"
  fi
}

stop_cors_proxy() {
  if [ ! -f "$PROXY_PID_FILE" ]; then
    return 0
  fi

  local ppid
  ppid=$(cat "$PROXY_PID_FILE" 2>/dev/null)
  if [ -n "$ppid" ] && kill -0 "$ppid" 2>/dev/null; then
    info "Stopping CORS proxy (PID: $ppid)..."
    kill "$ppid" 2>/dev/null
    sleep 1
    if kill -0 "$ppid" 2>/dev/null; then
      warn "Force stopping CORS proxy..."
      kill -9 "$ppid" 2>/dev/null || true
    fi
    ok "CORS proxy stopped"
  fi

  rm -f "$PROXY_PID_FILE"
}

stop_server() {
  # Always stop the CORS proxy first
  stop_cors_proxy

  if [ ! -f "$PID_FILE" ]; then
    warn "No PID file found. Server may not be running."
    local pids
    pids=$(pgrep -f "opencode serve" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      warn "Found opencode process(es): $pids"
      kill $pids 2>/dev/null || true
      ok "Stopped all opencode serve processes"
    fi
    return 0
  fi

  local pid
  pid=$(cat "$PID_FILE" 2>/dev/null)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    info "Stopping OpenCode server (PID: $pid)..."
    kill "$pid" 2>/dev/null
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
      warn "Force stopping..."
      kill -9 "$pid" 2>/dev/null || true
    fi
    ok "Server stopped"
  else
    warn "No running process found for PID: $pid"
  fi

  rm -f "$PID_FILE"
}

status_server() {
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════${NC}"
  echo -e "${BLUE}  OpenCode Server Status${NC}"
  echo -e "${BLUE}═══════════════════════════════════════${NC}"

  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      ok "Server is running"
      echo "  PID:     $pid"
      echo "  Port:    $PORT"
      echo "  URL:     http://$HOST:$PORT"
      echo "  Logs:    $LOG_FILE"
      local etime
      etime=$(ps -o etime= -p "$pid" 2>/dev/null | xargs)
      [ -n "$etime" ] && echo "  Uptime:  $etime"
    else
      warn "PID file exists but process is not running"
      echo "  PID file: $PID_FILE"
      echo "  Run: $0 restart"
    fi
  else
    warn "Server is not running"
    echo "  Start it: $0 start"
  fi

  if curl -s "http://$HOST:$PORT/session/status" >/dev/null 2>&1; then
    ok "API is reachable at http://$HOST:$PORT"
    local agents
    agents=$(curl -s "http://$HOST:$PORT/agent" 2>/dev/null | head -c 200)
    if [ -n "$agents" ]; then
      echo "  Available agents: $agents"
    fi
  else
    err "API is NOT reachable at http://$HOST:$PORT"
  fi

  # CORS proxy status
  echo ""
  if [ -f "$PROXY_PID_FILE" ]; then
    local ppid
    ppid=$(cat "$PROXY_PID_FILE" 2>/dev/null)
    if [ -n "$ppid" ] && kill -0 "$ppid" 2>/dev/null; then
      ok "CORS proxy is running (PID: $ppid)"
      echo "  URL:  http://$HOST:$CORS_PROXY_PORT"
      if curl -s -H "Origin: file://" "http://$HOST:$CORS_PROXY_PORT/session/status" >/dev/null 2>&1; then
        ok "CORS proxy is reachable (CORS headers verified)"
      else
        err "CORS proxy is NOT reachable"
      fi
    else
      warn "CORS proxy PID file exists but process is not running"
    fi
  else
    warn "CORS proxy is not running"
    echo "  (restart the server to start the proxy)"
  fi

  echo -e "${BLUE}═══════════════════════════════════════${NC}"
  echo ""
}

# ─── Auto-start on shell launch ───────────────────

auto_start() {
  if [ ! -f "$PID_FILE" ] || ! kill -0 "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null; then
    start_server
  fi
}

# ─── Main ──────────────────────────────────────────

case "${1:-help}" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    sleep 1
    start_server
    ;;
  status)
    status_server
    ;;
  auto-start)
    auto_start
    ;;
  *)
    echo "OpenCode Server Manager"
    echo ""
    echo "Usage:"
    echo "  $0 start        Start the server"
    echo "  $0 stop         Stop the server"
    echo "  $0 restart      Restart the server"
    echo "  $0 status       Check server status"
    echo "  $0 auto-start   Auto-start (for .bashrc/.profile)"
    echo ""
    echo "Environment:"
    echo "  OPENCODE_PORT           OpenCode server port (default: 9876)"
    echo "  OPENCODE_CORS_PROXY_PORT  CORS proxy port (default: 9878)"
    echo ""
    echo "Quick start:"
    echo "  $0 start"
    echo ""
    echo "Then in Acode: Ctrl+Shift+A to ask OpenCode"
    echo ""
    echo "Acode plugin port setting:"
    echo "  If you use this script, set the plugin port to $CORS_PROXY_PORT"
    echo "  (the CORS proxy handles browser security restrictions)"
    echo "  If you run opencode serve manually, use port $PORT"
    ;;
esac

#!/usr/bin/env bash
#
# chrome-cdp.sh — Launch a headless Chrome/Chromium with the Chrome DevTools
# Protocol (CDP) remote-debugging endpoint enabled.
#
# Purpose: provide a single, Termux/proot-safe command to start a browser that
# the `faster-chrome-devtools-skill` and `cdp-skill` OpenCode skills (and
# `opencode_web`) can attach to.
#
# On this environment `--headless=old` + `--use-gl=swiftshader` is required:
# `--headless=new` triggers a `Page.captureScreenshot` timeout (no GPU).
#
# Usage:
#   chrome-cdp.sh [--port 9222] [--headless old|new] [--user-data-dir DIR]
#                 [--url URL] [--no-detach] [--dry-run]
#
# Examples:
#   chrome-cdp.sh                                  # headless on :9222
#   chrome-cdp.sh --port 9333 --url https://example.com
#   CDP_HTTP_ENDPOINT=http://127.0.0.1:9222 \
#     node ~/.config/opencode/skills/skills/faster-chrome-devtools-skill/scripts/cdp.mjs list

set -euo pipefail

# --- color constants -------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[chrome-cdp]${NC} $*"; }
ok()    { echo -e "${GREEN}[chrome-cdp]${NC} $*"; }
warn()  { echo -e "${YELLOW}[chrome-cdp]${NC} $*"; }
err()   { echo -e "${RED}[chrome-cdp] ERROR:${NC} $*" >&2; }

# --- defaults --------------------------------------------------------------
PORT=9222
HEADLESS_MODE="old"          # old | new  (old is reliable for screenshots here)
USER_DATA_DIR="/tmp/cdp-chrome-profile"
START_URL="about:blank"
NO_DETACH=0
DRY_RUN=0

# --- arg parsing -----------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)          PORT="${2:-$PORT}"; shift 2 ;;
    --headless)      HEADLESS_MODE="${2:-old}"; shift 2 ;;
    --user-data-dir) USER_DATA_DIR="${2:-$USER_DATA_DIR}"; shift 2 ;;
    --url)           START_URL="${2:-about:blank}"; shift 2 ;;
    --no-detach)     NO_DETACH=1; shift ;;
    --dry-run)       DRY_RUN=1; shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) err "unknown argument: $1"; exit 1 ;;
  esac
done

# --- chromium auto-detection (Termux / proot / Alpine / standard Linux) -----
# Returns success only for a *real* Chromium binary. The Ubuntu
# `chromium-browser` is a snap transitional stub (executable, but errors at
# runtime) — skip it.
is_real_chromium() {
  local p="$1"
  [[ -x "$p" ]] || return 1
  # snap-stub guard: the stub is a shell script that refuses to run
  if head -c 400 "$p" 2>/dev/null | grep -q "requires the chromium snap"; then
    return 1
  fi
  return 0
}

detect_chromium() {
  local cand
  # 1. explicit overrides
  if [[ -n "${OPCODE_WEB_CHROMIUM:-}" ]] && is_real_chromium "${OPCODE_WEB_CHROMIUM}"; then
    echo "$OPCODE_WEB_CHROMIUM"; return 0
  fi
  if [[ -n "${CHROME_PATH:-}" ]] && is_real_chromium "${CHROME_PATH}"; then
    echo "$CHROME_PATH"; return 0
  fi
  # 2. Termux prefix
  if [[ -n "${PREFIX:-}" ]] && is_real_chromium "${PREFIX}/bin/chromium"; then
    echo "${PREFIX}/bin/chromium"; return 0
  fi
  # 3. Playwright-managed chromium (installed via: playwright install chromium)
  local home="${HOME:-/root}"
  for base in "$home/.cache/ms-playwright" /root/.cache/ms-playwright /home/.cache/ms-playwright; do
    [[ -d "$base" ]] || continue
    for d in "$base"/chromium-*; do
      [[ -d "$d" ]] || continue
      case "$d" in *headless_shell*) continue ;; esac
      cand="$d/chrome-linux/chrome"
      is_real_chromium "$cand" && { echo "$cand"; return 0; }
    done
  done
  # 4. common absolute paths (skip snap stubs)
  for p in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome /usr/bin/google-chrome-stable; do
    is_real_chromium "$p" && { echo "$p"; return 0; }
  done
  # 5. PATH
  for n in chromium chromium-browser google-chrome google-chrome-stable; do
    if command -v "$n" >/dev/null 2>&1; then
      cand="$(command -v "$n")"
      is_real_chromium "$cand" && { echo "$cand"; return 0; }
    fi
  done
  return 1
}

CHROME="$(detect_chromium)" || { err "No Chromium/Chrome found. Install one (pkg install chromium | apt-get install chromium | playwright install chromium) or set OPCODE_WEB_CHROMIUM."; exit 1; }

# --- build command --------------------------------------------------------
ARGS=(
  "--headless=$HEADLESS_MODE"
  "--no-sandbox"
  "--disable-gpu"
  "--disable-dev-shm-usage"
  "--use-gl=swiftshader"
  "--remote-debugging-port=$PORT"
  "--user-data-dir=$USER_DATA_DIR"
  "$START_URL"
)

CMD=("$CHROME" "${ARGS[@]}")

if [[ $DRY_RUN -eq 1 ]]; then
  info "would run: ${CMD[*]}"
  exit 0
fi

# stop any chrome already bound to this port
if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:"$PORT" 2>/dev/null | xargs -r kill 2>/dev/null || true
fi

rm -rf "$USER_DATA_DIR"

info "Chromium: $CHROME"
info "Launching headless=$HEADLESS_MODE on port $PORT (user-data-dir=$USER_DATA_DIR)..."

if [[ $NO_DETACH -eq 1 ]]; then
  exec "${CMD[@]}"
else
  nohup "${CMD[@]}" > "/tmp/chrome-cdp-$PORT.log" 2>&1 &
  PID=$!
  # wait briefly for the CDP endpoint to come up
  for _ in $(seq 1 20); do
    if curl -s --max-time 1 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
      ok "Chrome is up. CDP endpoint: http://127.0.0.1:$PORT"
      ok "Set CDP_HTTP_ENDPOINT=http://127.0.0.1:$PORT (or CDP_WS_ENDPOINT from /json/version)"
      ok "PID=$PID  |  log: /tmp/chrome-cdp-$PORT.log"
      echo "CDP_HTTP_ENDPOINT=http://127.0.0.1:$PORT"
      exit 0
    fi
    sleep 0.5
  done
  warn "Chrome started (PID=$PID) but CDP endpoint not detected within 10s. Check /tmp/chrome-cdp-$PORT.log"
  exit 0
fi

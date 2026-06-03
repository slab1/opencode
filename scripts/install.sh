#!/bin/sh
# ═══════════════════════════════════════════════════════
#  OpenCode for Acode — One-Command Installer
#
#  Installs OpenCode and sets up the server in your
#  terminal environment (Termux, Alpine Linux, etc.).
#
#  Run:
#    curl -sL https://raw.githubusercontent.com/opencode/acode-plugin/main/scripts/install.sh | sh
# ═══════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[OpenCode]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  OpenCode for Acode — Installer${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""

# ─── Step 1: Detect environment ────────────────────

info "Detecting environment..."

PM="unknown"
if command -v apk >/dev/null 2>&1; then
  PM="apk"
  ok "Alpine Linux (apk) detected"
elif command -v pkg >/dev/null 2>&1; then
  PM="pkg"
  ok "Termux (pkg) detected"
elif command -v apt-get >/dev/null 2>&1; then
  PM="apt-get"
  ok "Debian/Ubuntu (apt) detected"
elif command -v dnf >/dev/null 2>&1; then
  PM="dnf"
  ok "Fedora (dnf) detected"
else
  warn "Unknown package manager. You may need to install nodejs manually."
fi

# ─── Step 2: Install dependencies ─────────────────

info "Checking dependencies..."

if ! command -v node >/dev/null 2>&1; then
  info "Node.js not found. Installing..."
  case "$PM" in
    apk)
      apk add --no-cache nodejs npm
      ;;
    pkg)
      pkg update -y -q 2>/dev/null || true
      pkg install -y nodejs curl -q 2>/dev/null
      ;;
    apt-get)
      apt-get update -qq
      apt-get install -y -qq nodejs npm curl
      ;;
    dnf)
      dnf install -y nodejs npm curl
      ;;
    *)
      err "Please install Node.js manually: https://nodejs.org"
      exit 1
      ;;
  esac
fi

ok "Node.js: $(node --version 2>/dev/null || echo 'installed')"

# ─── Step 3: Install OpenCode ─────────────────────

if command -v opencode >/dev/null 2>&1; then
  OC_VER=$(opencode --version 2>/dev/null || echo "?")
  ok "OpenCode already installed (v$OC_VER)"
else
  info "Installing OpenCode via npm..."
  npm install -g opencode-ai
  ok "OpenCode installed: $(opencode --version 2>/dev/null || echo 'done')"
fi

# ─── Step 4: Install the Acode plugin ──────────────

info "To install the Acode plugin:"
echo ""
echo "  1. Download the plugin ZIP:"
echo "     ${YELLOW}https://github.com/opencode/acode-plugin/releases/latest/download/acode-oc.zip${NC}"
echo ""
echo "  2. Open Acode → Settings → Plugins → Install from ZIP"
echo "     (or Local if you downloaded the file)"
echo ""
echo "  3. Select the downloaded ZIP file"
echo ""

# ─── Step 5: Auto-start setup ────────────────────

OPENCODE_DIR="${HOME:-/root}/.opencode"
SERVER_SCRIPT="$OPENCODE_DIR/opencode-server.sh"

if [ ! -f "$SERVER_SCRIPT" ]; then
  info "Setting up auto-start..."
  mkdir -p "$OPENCODE_DIR"

  SCRIPT_DIR="$(dirname "$0")"
  if [ -f "$SCRIPT_DIR/server.sh" ]; then
    cp "$SCRIPT_DIR/server.sh" "$SERVER_SCRIPT"
  else
    curl -sL \
      https://raw.githubusercontent.com/opencode/acode-plugin/main/scripts/server.sh \
      -o "$SERVER_SCRIPT"
  fi
  chmod +x "$SERVER_SCRIPT"

  # Also install the CORS proxy script alongside server.sh
  PROXY_SCRIPT="$OPENCODE_DIR/cors-proxy.js"
  if [ ! -f "$PROXY_SCRIPT" ]; then
    if [ -f "$SCRIPT_DIR/cors-proxy.js" ]; then
      cp "$SCRIPT_DIR/cors-proxy.js" "$PROXY_SCRIPT"
      ok "CORS proxy script installed"
    else
      curl -sL \
        https://raw.githubusercontent.com/opencode/acode-plugin/main/scripts/cors-proxy.js \
        -o "$PROXY_SCRIPT" && ok "CORS proxy script installed" || warn "Could not download CORS proxy"
    fi
  fi

  RC_FILE=""
  if [ -n "$BASH" ] || [ -f "$HOME/.bashrc" ]; then
    RC_FILE="$HOME/.bashrc"
  elif [ -f "$HOME/.profile" ]; then
    RC_FILE="$HOME/.profile"
  elif [ -f "$HOME/.shrc" ]; then
    RC_FILE="$HOME/.shrc"
  fi

  if [ -n "$RC_FILE" ]; then
    if ! grep -q "opencode-server.sh" "$RC_FILE" 2>/dev/null; then
      echo "" >> "$RC_FILE"
      echo "# OpenCode auto-start" >> "$RC_FILE"
      echo "if [ -f $SERVER_SCRIPT ]; then" >> "$RC_FILE"
      echo "  sh $SERVER_SCRIPT auto-start" >> "$RC_FILE"
      echo "fi" >> "$RC_FILE"
      ok "Auto-start added to $RC_FILE"
    else
      ok "Auto-start already configured in $RC_FILE"
    fi
  else
    warn "Could not detect shell rc file."
    echo "  To enable auto-start, add to your shell profile:"
    echo "  sh $SERVER_SCRIPT auto-start"
  fi
else
  ok "Server script already installed at $SERVER_SCRIPT"
fi

# ─── Done ─────────────────────────────────────────

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. ${YELLOW}Start the server${NC}:"
echo "     sh $SERVER_SCRIPT start"
echo ""
echo "  2. ${YELLOW}Install the Acode plugin${NC}:"
echo "     Download the ZIP from GitHub and install in Acode"
echo ""
echo "  3. ${YELLOW}Open Acode${NC} and press Ctrl+Shift+A"
echo ""
echo "Quick commands in Acode:"
echo "  Ctrl+Shift+A   Ask OpenCode"
echo "  Ctrl+Shift+F   Fix selected code"
echo "  Ctrl+Shift+E   Explain selected code"
echo "  Ctrl+Shift+G   Generate code"
echo "  Ctrl+Shift+M   Multi-file ask"
echo "  Ctrl+Shift+H   Chat history"
echo ""
echo "Need help? https://github.com/opencode/acode-plugin/issues"
echo ""

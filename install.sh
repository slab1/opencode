#!/bin/sh
# ============================================================================
# OpenCode Configuration Toolkit — Bootstrap Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/slab1/opencode/main/install.sh | sh
#
# Or if already cloned:
#   ./install.sh
#
# What it does:
#   1. Installs system packages (apk) — Xvfb, x11vnc, fluxbox, ffmpeg, poppler
#   2. Installs Python packages — Pillow, pytesseract, moviepy, whisper
#   3. Installs npm/MCP dependencies via bun
#   4. Verifies everything works
# ============================================================================

set -e

# ── Colors ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; }

# ── Detect OS ────────────────────────────────────────────────────────────
OS=""
if [ -f /etc/alpine-release ]; then
    OS="alpine"
elif command -v apt-get >/dev/null 2>&1; then
    OS="debian"
elif command -v yum >/dev/null 2>&1; then
    OS="rhel"
elif command -v brew >/dev/null 2>&1; then
    OS="macos"
else
    warn "Unknown OS — skipping system package installation."
    warn "Install deps manually (see README.md)."
fi

OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
PYTHON="${PYTHON:-python3}"
PIP="${PIP:-pip3}"

# ── Section: System Packages ────────────────────────────────────────────
install_system_packages() {
    info "Installing system packages..."

    case "$OS" in
        alpine)
            apk update
            # Core tools
            apk add --no-cache \
                xvfb xvfb-run \
                x11vnc \
                fluxbox \
                ffmpeg \
                poppler-utils \
                imagemagick \
                xdpyinfo xwd \
                chromium \
                font-dejavu \
                xauth
            ok "Alpine system packages installed."
            ;;
        debian)
            sudo apt-get update
            sudo apt-get install -y \
                xvfb x11vnc fluxbox \
                ffmpeg poppler-utils \
                imagemagick x11-utils xwd \
                chromium-browser  \
                fonts-noto fonts-noto-cjk fonts-noto-color-emoji \
                fonts-dejavu
            ok "Debian system packages installed."
            ;;
        rhel)
            sudo yum install -y \
                xorg-x11-server-Xvfb \
                x11vnc \
                fluxbox \
                ffmpeg \
                poppler-utils \
                ImageMagick \
                xdpyinfo xwd \
                chromium
            ok "RHEL system packages installed."
            ;;
        macos)
            brew install --cask xquartz
            brew install \
                ffmpeg poppler \
                imagemagick \
                chromium --no-sandbox
            warn "macOS: Install x11vnc manually if needed: brew install x11vnc"
            warn "macOS: fluxbox requires XQuartz. Install via MacPorts or manually."
            ;;
        *)
            warn "Skipping system packages (unsupported OS: $OS)."
            warn "Required: xvfb, x11vnc, fluxbox, ffmpeg, poppler-utils, chromium"
            ;;
    esac
}

# ── Section: Python Packages ────────────────────────────────────────────
install_python_packages() {
    info "Installing Python packages..."

    $PIP install --upgrade pip

    # Core media processing
    $PIP install \
        Pillow \
        pytesseract \
        moviepy \
        openai-whisper

    # Web automation support
    $PIP install \
        playwright \
        selenium

    ok "Python packages installed."
}

# ── Section: npm / Bun Dependencies ─────────────────────────────────────
install_npm_deps() {
    info "Installing npm/MCP dependencies via bun..."

    if command -v bun >/dev/null 2>&1; then
        cd "$OPENCODE_CONFIG_DIR"
        bun install --no-save 2>/dev/null || warn "bun install had warnings (non-critical)"
        ok "npm dependencies resolved via bun."

        # Install Playwright browsers (for web automation)
        if command -v npx >/dev/null 2>&1; then
            info "Installing Playwright Chromium browser..."
            npx playwright install chromium 2>/dev/null || \
                warn "Playwright browser install skipped (run manually: npx playwright install chromium)"
        fi
    elif command -v npm >/dev/null 2>&1; then
        cd "$OPENCODE_CONFIG_DIR"
        npm install
        npx playwright install chromium 2>/dev/null || \
            warn "Playwright browser install skipped"
        ok "npm dependencies installed."
    else
        warn "Neither bun nor npm found. Install Node.js first, then run:"
        warn "  cd ~/.config/opencode && npm install"
5        warn "  npx playwright install chromium"
    fi
}

# ── Section: Verify Installation ───────────────────────────────────────
verify_installation() {
    info "Verifying installation..."
    errors=0

    # Check Python modules
    info "  Python modules..."
    for mod in PIL opencode_media; do
        if $PYTHON -c "import $mod" 2>/dev/null; then
            ok "    $mod — OK"
        else
            warn "    $mod — not found (optional, some features limited)"
        fi
    done

    # Check system tools
    info "  System tools..."
    for tool in Xvfb x11vnc fluxbox ffmpeg ffprobe pdftotext pdfinfo convert xdpyinfo chromium; do
        if command -v $tool >/dev/null 2>&1; then
            ok "    $tool — OK"
        else
            warn "    $tool — not found (optional, some features limited)"
        fi
    done

    # Check MCP servers (dry-run the npx calls to see if they resolve)
    info "  MCP servers (npx)..."
    for pkg in @modelcontextprotocol/server-filesystem firecrawl-mcp; do
        if npx --yes "$pkg" --version 2>/dev/null; then
            ok "    $pkg — available via npx"
        else
            warn "    $pkg — check connection or install manually"
        fi
    done

    # Verify config file
    if [ -f "$OPENCODE_CONFIG_DIR/opencode.jsonc" ]; then
        ok "  opencode.jsonc — found"
    else
        fail "  opencode.jsonc — MISSING"
        errors=$((errors + 1))
    fi

    # Verify agent files
    agent_count=$(ls "$OPENCODE_CONFIG_DIR"/agents/*.md 2>/dev/null | wc -l)
    if [ "$agent_count" -ge 18 ]; then
        ok "  Agents — $agent_count agent files found"
    else
        warn "  Agents — found $agent_count (expected 18+)"
    fi

    # Verify knowledge graph
    if [ -f "$OPENCODE_CONFIG_DIR/knowledge-graph/graph.json" ]; then
        ok "  knowledge-graph/graph.json — found"
    else
        warn "  knowledge-graph/graph.json — missing (optional)"
    fi

    if [ "$errors" -gt 0 ]; then
        fail "$errors critical check(s) failed. Review warnings above."
        return 1
    fi

    echo ""
    ok "============================================"
    ok "  OpenCode Toolkit installed successfully!"
    ok "============================================"
    echo ""
    info "Next steps:"
    info "  1. Restart OpenCode to pick up the new configuration"
    info "  2. Set SUPABASE_ACCESS_TOKEN env var if using Supabase MCP"
    info "  3. Set FIRECRAWL_API_KEY env var if using Firecrawl MCP"
    info "  4. Try: python3 -m opencode_media --help"
    echo ""
}

# ── Main ─────────────────────────────────────────────────────────────────
main() {
    echo ""
    info "============================================"
    info "  OpenCode Configuration Toolkit Installer"
    info "============================================"
    echo ""

    # Ensure we're in the right directory
    if [ ! -f "$OPENCODE_CONFIG_DIR/opencode.jsonc" ]; then
        # Maybe the script is being run from the repo
        if [ -f "./opencode.jsonc" ]; then
            OPENCODE_CONFIG_DIR="$PWD"
        else
            fail "opencode.jsonc not found in $OPENCODE_CONFIG_DIR or current directory."
            fail "Clone the repo first:"
            fail "  git clone https://github.com/slab1/opencode.git ~/.config/opencode"
            exit 1
        fi
    fi

    install_system_packages
    install_python_packages
    install_npm_deps
    verify_installation
}

main "$@"

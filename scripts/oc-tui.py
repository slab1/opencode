#!/usr/bin/env python3
"""
oc-tui — OpenCode Terminal UI
================================
Keyboard-driven dashboard + Chat interface for OpenCode.
Runs in any ANSI terminal (Acode, Alpine Linux, xterm, etc.).
Zero external dependencies — uses only Python stdlib + ANSI codes.

Usage:
    oc-tui                    Launch the TUI dashboard
    oc-tui --dump             Print one-shot status snapshot (no TUI)

Dashboard Keys:
    ↑/↓        Scroll panels
    1-9        Quick actions
    r          Refresh all panels
    s / 2      Show recent sessions
    c / 3      Show context summary
    f / 4      Show findings
    w / 5      Show workflow trace
    m / 7      Show monitor dashboard
    g / 6      Git push
    Tab / t    Switch to Chat mode
    h / ?      Help
    q / Ctrl+C Quit

Chat Keys:
    Tab        Switch to Dashboard
    Ctrl+S     Send message
    Ctrl+N     New conversation
    ↑/↓        Scroll messages / Navigate input
    PgUp/Dn    Scroll page
    q          Quit
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

# ── Chat module (oc_chat.py in same directory) ─────────────────────
_CHAT_DIR = os.path.dirname(os.path.abspath(__file__))
_CHAT_MODULE = os.path.join(_CHAT_DIR, "oc_chat.py")

def _import_chat():
    """Dynamically import oc_chat module from the scripts directory."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("oc_chat", _CHAT_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Lazy import — the chat module is loaded only when entering chat mode
_chat_module = None
def get_chat():
    global _chat_module
    if _chat_module is None:
        _chat_module = _import_chat()
    return _chat_module

# ── Paths ──────────────────────────────────────────────────────────
CONFIG_DIR = os.path.expanduser("~/.config/opencode")
CONTEXT_FILE = os.path.join(CONFIG_DIR, "shared", "context.json")
HELPER = os.path.join(CONFIG_DIR, "shared", "helpers", "context.py")
SESSIONS_OUTCOMES = os.path.join(CONFIG_DIR, "knowledge-graph", "outcomes", "sessions.json")

# ── ANSI helpers ───────────────────────────────────────────────────
class Style:
    """ANSI escape code builder."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"

    # Foreground 256-color
    @staticmethod
    def fg(code): return f"\033[38;5;{code}m"

    # Background 256-color
    @staticmethod
    def bg(code): return f"\033[48;5;{code}m"

    # TrueColor
    @staticmethod
    def rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg_rgb(r, g, b): return f"\033[48;2;{r};{g};{b}m"

    # Positioning
    @staticmethod
    def goto(x, y): return f"\033[{y};{x}H"

    @staticmethod
    def save(): return "\033[s"

    @staticmethod
    def restore(): return "\033[u"

    # Clear
    @staticmethod
    def clear_screen(): return "\033[2J"

    @staticmethod
    def clear_line(): return "\033[K"

    @staticmethod
    def clear_to_eol(): return "\033[K"

    @staticmethod
    def erase_display(): return "\033[3J\033[2J\033[H"

    # Cursor
    @staticmethod
    def hide_cursor(): return "\033[?25l"

    @staticmethod
    def show_cursor(): return "\033[?25h"

    @staticmethod
    def cursor_up(n=1): return f"\033[{n}A"

    @staticmethod
    def cursor_down(n=1): return f"\033[{n}B"

    @staticmethod
    def cursor_right(n=1): return f"\033[{n}C"

    @staticmethod
    def cursor_left(n=1): return f"\033[{n}D"

    # Screen
    @staticmethod
    def scroll_up(n=1): return f"\033[{n}S"

    @staticmethod
    def scroll_down(n=1): return f"\033[{n}T"

    # Box drawing
    H_LINE = "─"
    V_LINE = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"
    TM = "┬"
    BM = "┴"
    LM = "├"
    RM = "┤"
    CROSS = "┼"
    H_DOUBLE = "═"
    V_DOUBLE = "║"
    TL_D = "╔"
    TR_D = "╗"
    BL_D = "╚"
    BR_D = "╝"

    # Unicode symbols
    DOT = "●"
    CIRCLE = "○"
    CHEVRON = "›"
    ARROW_R = "→"
    ARROW_U = "↑"
    ARROW_D = "↓"
    CHECK = "✓"
    CROSS_M = "✗"
    STAR = "★"
    GEAR = "⚙"
    LOCK = "🔒"
    CLOCK = "🕐"
    WARN = "⚠"


# ── Color palette (256-color) ──────────────────────────────────────
# Empire / synthwave inspired dark theme
C = {
    "bg": 16,           # near-black
    "bg2": 233,         # slightly lighter
    "fg": 255,          # white
    "fg2": 250,         # light gray
    "fg3": 240,         # dim gray
    "accent": 75,       # soft blue
    "accent2": 39,      # bright cyan
    "green": 83,        # green
    "yellow": 221,      # warm yellow
    "orange": 208,      # orange
    "red": 196,         # red
    "purple": 141,      # purple
    "pink": 212,        # pink
    "teal": 43,         # teal
    "border": 237,      # dark border
    "border2": 240,     # lighter border
    "header_bg": 17,    # dark blue
    "status_ok": 83,    # green
    "status_warn": 221, # yellow
    "status_err": 196,  # red
    "status_run": 75,   # blue
    "panel_bg": 232,    # slightly off bg
}

SEV_COLORS = {
    "critical": C["red"],
    "high": C["orange"],
    "medium": C["yellow"],
    "low": C["fg2"],
    "info": C["teal"],
}


# ── Terminal helpers ───────────────────────────────────────────────
term_size = (80, 24)

def get_term_size():
    """Get terminal size safely."""
    try:
        return shutil.get_terminal_size((80, 24))
    except (ValueError, OSError):
        return (80, 24)


def read_key(timeout=0.3):
    """Read a single keypress without blocking. Returns None if timeout.
    Terminal must already be in raw mode (set by OpenCodeTUI.setup())."""
    import select

    try:
        if select.select([sys.stdin], [], [], timeout)[0]:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # Read up to 3 trailing bytes (CSI sequence) with 50ms per byte
                rest = ""
                for _ in range(3):
                    if select.select([sys.stdin], [], [], 0.05)[0]:
                        rest += sys.stdin.read(1)
                    else:
                        break

                if rest == "[A":      return "UP"
                if rest == "[B":      return "DOWN"
                if rest == "[C":      return "RIGHT"
                if rest == "[D":      return "LEFT"
                if rest == "[H":      return "HOME"
                if rest == "[F":      return "END"
                if rest == "[5~":     return "PAGE_UP"
                if rest == "[6~":     return "PAGE_DOWN"
                if rest == "[3~":     return "DEL"
                if rest == "[1~":     return "HOME"
                if rest == "[4~":     return "END"
                return "ESC"
            elif ch == "\r" or ch == "\n":
                return "ENTER"
            elif ch == "\x7f" or ch == "\b":
                return "BACK"
            elif ch == "\t":
                return "TAB"
            elif ch == "\x03":  # Ctrl+C — handled by main loop
                raise KeyboardInterrupt()
            return ch
        return None
    except (ValueError, OSError):
        return None


# ── Data loaders ───────────────────────────────────────────────────
def load_context():
    """Load shared context, returning default dict on failure."""
    try:
        with open(CONTEXT_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "meta": {"version": "2.0.0"},
            "session": {},
            "state": {},
            "findings": {},
            "decisions": {},
            "artifacts": {},
            "cross_references": [],
            "workflow_trace": [],
        }


def run_cmd(cmd: list, timeout=8) -> str:
    """Run a command and return stdout or empty string."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_sessions() -> list:
    """Get recent sessions from outcomes file."""
    try:
        with open(SESSIONS_OUTCOMES) as f:
            data = json.load(f)
        return data.get("sessions", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_opencode_version() -> str:
    """Get opencode version."""
    v = run_cmd(["opencode", "--version"])
    return v.split("\n")[0] if v else "—"


# ── Drawing primitives ─────────────────────────────────────────────
def styled(text, *styles):
    """Apply ANSI styles and reset."""
    return f"{''.join(styles)}{text}{Style.RESET}"


def draw_box(top, left, width, height, title="", style=C["border"]):
    """Draw a bordered box region. Returns nothing — just writes ANSI."""
    b = Style.fg(style)
    lines = []
    # Top border
    top_line = f"{b}{Style.TL}{Style.H_LINE * (width - 2)}{Style.TR}{Style.RESET}"
    if title:
        insert_at = 3
        title_str = f" {styled(title, Style.BOLD, Style.fg(C['accent']))} "
        top_line = (
            f"{b}{Style.TL}{Style.RESET}"
            f"{top_line[3:3+insert_at-1]}"
            f"{title_str}"
            f"{top_line[3+insert_at+len(title_str)-2:]}"
        )
        # simpler: just overlay manually
        top_line = (f"{Style.goto(left, top)}"
                    f"{b}{Style.TL}{Style.RESET}"
                    f"{Style.fg(style)}{Style.H_LINE * 2}{Style.RESET}"
                    f" {styled(title, Style.BOLD, Style.fg(C['accent']))} "
                    f"{Style.fg(style)}{Style.H_LINE * (width - 6 - len(title))}{Style.TR}{Style.RESET}")
    else:
        top_line = f"{Style.goto(left, top)}{b}{Style.TL}{Style.H_LINE * (width - 2)}{Style.TR}{Style.RESET}"
    sys.stdout.write(top_line)

    # Bottom border
    bottom = top + height - 1
    bot_line = f"{Style.goto(left, bottom)}{b}{Style.BL}{Style.H_LINE * (width - 2)}{Style.BR}{Style.RESET}"
    sys.stdout.write(bot_line)

    # Side borders
    for y in range(top + 1, bottom):
        sys.stdout.write(f"{Style.goto(left, y)}{b}{Style.V_LINE}{Style.RESET}")
        sys.stdout.write(f"{Style.goto(left + width - 1, y)}{b}{Style.V_LINE}{Style.RESET}")


def write_at(x, y, text, *styles):
    """Write text at a specific position with optional styles."""
    sys.stdout.write(f"{Style.goto(x+1, y+1)}{styled(text, *styles)}")


def write_region(x, y, width, text, style=C["fg"]):
    """Write text into a region, wrapping at width."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line:
            display = line[:width].ljust(width)
            sys.stdout.write(f"{Style.goto(x+1, y+1+i)}{styled(display, Style.fg(style))}")


def progress_bar(width, fraction, color=C["green"]):
    """Draw a progress bar."""
    filled = int(width * fraction)
    bar = "█" * filled + "░" * (width - filled)
    return styled(bar, Style.fg(color))


def time_ago(timestamp_str: str) -> str:
    """Convert ISO timestamp to relative time string."""
    if not timestamp_str:
        return "—"
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        diff = datetime.now().astimezone() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        else:
            return f"{seconds // 86400}d ago"
    except (ValueError, TypeError):
        return "—"


# ── TUI Application ────────────────────────────────────────────────
class OpenCodeTUI:
    """Main TUI application."""

    def __init__(self):
        self.cols, self.rows = get_term_size()
        self.ctx = load_context()
        self.sessions = []
        self.opencode_ver = "—"
        self.running = True
        self.last_refresh = 0
        self.refresh_interval = 2  # seconds
        self.message = ""
        self.message_time = 0
        self.panel_scroll = {"ctx": 0, "wf": 0, "help": 0}
        self.show_help = False
        self.mode = "dashboard"  # dashboard, sessions, findings, chat, help
        self.chat = None
        self._old_term = None  # saved terminal attrs for raw mode

    def refresh(self, force=False):
        """Refresh data if interval has passed."""
        now = time.time()
        if force or (now - self.last_refresh) > self.refresh_interval:
            self.ctx = load_context()
            if self.mode == "sessions":
                self.sessions = get_sessions()
            self.opencode_ver = get_opencode_version()
            self.cols, self.rows = get_term_size()
            self.last_refresh = now

    def set_message(self, msg: str):
        self.message = msg
        self.message_time = time.time()

    def clear_message(self):
        if self.message and (time.time() - self.message_time) > 3:
            self.message = ""

    # ── Panel renderers ─────────────────────────────────────────

    def render_header(self):
        """Top status bar."""
        session = self.ctx.get("session", {})
        sid = session.get("current_id", "—")
        pattern = session.get("workflow_pattern", "—")
        active = session.get("active_agents", [])
        status = "● running" if active else "○ idle"

        # Background bar
        full = f"{' ' * self.cols}"
        sys.stdout.write(f"{Style.goto(1, 1)}{Style.bg(C['header_bg'])}{full}{Style.RESET}")

        # Left: logo + session
        sid_display = (sid or "—")[:20]
        left = f" {Style.GEAR} {styled('oc-tui', Style.BOLD, Style.fg(C['accent']))}  {styled(sid_display, Style.fg(C['fg2']))}"
        sys.stdout.write(f"{Style.goto(1, 1)}{Style.bg(C['header_bg'])}{left}{Style.RESET}")

        # Center: pattern
        mid = f"  {styled(pattern, Style.fg(C['teal']))}  "
        mid_x = (self.cols - len(mid)) // 2
        sys.stdout.write(f"{Style.goto(mid_x, 1)}{Style.bg(C['header_bg'])}{mid}{Style.RESET}")

        # Right: version + status
        status_color = C["status_ok"] if not active else C["status_run"]
        right = f"v{self.opencode_ver[:15]:16}  {styled(status, Style.fg(status_color))}  "
        right_x = self.cols - len(right) + 1
        sys.stdout.write(f"{Style.goto(right_x, 1)}{Style.bg(C['header_bg'])}{right}{Style.RESET}")

    def render_footer(self):
        """Bottom action bar."""
        y = self.rows
        full = f"{' ' * self.cols}"
        sys.stdout.write(f"{Style.goto(1, y)}{Style.bg(C['bg2'])}{full}{Style.RESET}")

        items = [
            ("1", "Resume", C["accent"]),
            ("2", "Sessions", C["accent"]),
            ("3", "Context", C["accent"]),
            ("4", "Findings", C["accent"]),
            ("5", "Workflow", C["accent"]),
            ("6", "GitPush", C["accent"]),
            ("7", "Monitor", C["accent"]),
            ("Tab", "Chat", C["green"]),
            ("q", "Quit", C["red"]),
        ]

        x = 2
        for key, label, color in items:
            item = f" {styled(f'[{key}]', Style.BOLD, Style.fg(color))} {styled(label, Style.fg(C['fg2']))} "
            sys.stdout.write(f"{Style.goto(x, y)}{Style.bg(C['bg2'])}{item}{Style.RESET}")
            x += len(item)

        # Right side: help hint
        hint = styled(" [h] Help ", Style.fg(C["fg3"]))
        sys.stdout.write(f"{Style.goto(self.cols - 10, y)}{Style.bg(C['bg2'])}{hint}{Style.RESET}")

    def render_session_panel(self, x, y, width, height):
        """Session info panel (top-left)."""
        session = self.ctx.get("session", {})
        state = self.ctx.get("state", {})
        sid = session.get("current_id") or styled("—", Style.DIM, Style.fg(C["fg3"]))
        pattern = session.get("workflow_pattern") or styled("—", Style.DIM, Style.fg(C["fg3"]))
        title = session.get("current_title") or styled("—", Style.DIM, Style.fg(C["fg3"]))
        active = session.get("active_agents", [])
        started = session.get("started_at", "")

        lines = [
            f" {Style.CHEVRON} {styled('Session:', Style.BOLD)}  {sid}",
            f" {Style.CHEVRON} {styled('Title:', Style.BOLD)}   {title}",
            f" {Style.CHEVRON} {styled('Pattern:', Style.BOLD)} {pattern}",
            f" {Style.CHEVRON} {styled('Agents:', Style.BOLD)}  {', '.join(active) if active else styled('none', Style.DIM)}",
            f" {Style.CHEVRON} {styled('Started:', Style.BOLD)} {time_ago(started) if started else '—'}",
            "",
            f" {Style.CLOCK} {styled('Last update:', Style.DIM)} {time_ago(state.get('last_updated_at', ''))}",
            f" {Style.CHEVRON} {styled('Updated by:', Style.DIM)} {state.get('last_updated_by') or '—'}",
        ]

        # Clear panel area first to prevent scroll doubling
        for cy in range(height):
            sys.stdout.write(f"{Style.goto(x + 1, y + cy + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")

        for i, line in enumerate(lines):
            if y + i < y + height - 1:
                write_at(x, y + i, line[:width - 3], Style.fg(C["fg"]))

    def render_context_panel(self, x, y, width, height):
        """Shared context summary panel (top-right)."""
        # Clear panel area first
        for cy in range(height):
            sys.stdout.write(f"{Style.goto(x + 1, y + cy + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")

        findings = self.ctx.get("findings", {})
        artifacts = self.ctx.get("artifacts", {})
        line = 0
        # Findings summary
        finding_counts = {a: len(fs) for a, fs in findings.items() if fs}
        if finding_counts:
            write_at(x, y + line, f" {Style.CHEVRON} {styled('Findings:', Style.BOLD)}", Style.fg(C["fg"]))
            line += 1
            for agent, count in sorted(finding_counts.items()):
                sevs = {}
                for f in findings[agent]:
                    sevs[f.get("severity", "info")] = sevs.get(f.get("severity", "info"), 0) + 1
                sev_str = ", ".join(
                    f"{styled(f'{k}={v}', Style.fg(SEV_COLORS.get(k, C['fg2'])))}"
                    for k, v in sorted(sevs.items())
                )
                text = f"   {agent:14} {count:3}  [{sev_str}]"
                if y + line < y + height - 1:
                    write_at(x, y + line, text[:width - 3], Style.fg(C["fg2"]))
                    line += 1

        # Artifacts
        artifact_counts = {k: len(v) for k, v in artifacts.items() if v}
        if artifact_counts and y + line + 1 < y + height - 1:
            line += 1
            write_at(x, y + line, f" {Style.CHEVRON} {styled('Artifacts:', Style.BOLD)}", Style.fg(C["fg"]))
            line += 1
            for k, v in sorted(artifact_counts.items()):
                text = f"   {k:25} {v}"
                if y + line < y + height - 1:
                    write_at(x, y + line, text[:width - 3], Style.fg(C["fg2"]))
                    line += 1

        # State
        state = self.ctx.get("state", {})
        if y + line + 1 < y + height - 1:
            line += 1
            updated = state.get("last_updated_at", "")
            mu = state.get("last_updated_by", "—")
            text = f" {Style.CLOCK} {time_ago(updated)} by {mu}"
            write_at(x, y + line, text[:width - 3], Style.fg(C["fg3"]))

    def render_workflow_panel(self, x, y, width, height):
        """Workflow trace panel (bottom area)."""
        trace = self.ctx.get("workflow_trace", [])

        # Clear panel area first — essential to prevent scroll doubling
        for cy in range(height):
            sys.stdout.write(f"{Style.goto(x + 1, y + cy + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")

        if not trace:
            write_at(x, y, f" {Style.CIRCLE} {styled('No active workflow trace.', Style.DIM)}", Style.fg(C["fg3"]))
            write_at(x, y + 1, f"   Start a workflow via OpenCode to see steps here.", Style.fg(C["fg3"]))
            return

        scroll = self.panel_scroll["wf"]
        max_visible = height - 1
        total = len(trace)

        for i in range(max_visible):
            idx = scroll + i
            if idx >= total:
                # Clear remaining lines when scrolled near end
                sys.stdout.write(f"{Style.goto(x + 1, y + i + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")
                continue
            step = trace[idx]
            agent = step.get("agent", "?")
            status = step.get("status", "?")
            summary = step.get("summary", "")[:width - 20]

            status_str = {
                "completed": styled("✓", Style.fg(C["green"])),
                "running": styled("●", Style.fg(C["status_run"])),
                "failed": styled("✗", Style.fg(C["red"])),
                "pending": styled("○", Style.fg(C["fg3"])),
            }.get(status, styled("?", Style.fg(C["fg3"])))

            agent_color = C["purple"] if agent == "orchestrator" else C["teal"]

            text = f" {status_str} {styled(agent, Style.BOLD, Style.fg(agent_color)):12} {summary[:width - 30]}"
            write_at(x, y + i, text[:width - 2], Style.fg(C["fg"]))

        # Scroll indicator
        if total > max_visible:
            pct = scroll / max(1, total - max_visible)
            bar = progress_bar(width - 5, pct, C["border2"])
            write_at(x, y + height - 2, f" {bar}  ", Style.fg(C["fg3"]))

    def render_sessions_panel(self, x, y, width, height):
        """Sessions list panel (overlay)."""
        # Clear panel area first
        for cy in range(height):
            sys.stdout.write(f"{Style.goto(x + 1, y + cy + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")
        sessions = self.sessions or []
        if not sessions:
            write_at(x, y, f" {Style.CIRCLE} {styled('No sessions recorded yet.', Style.DIM)}", Style.fg(C["fg3"]))
            return

        header = f" {'ID':24} {'Pattern':16} {'Agents':20} {'Outcome':12}"
        write_at(x, y, header[:width - 2], Style.BOLD, Style.fg(C["accent"]))
        write_at(x, y + 1, f" {'─' * (width - 3)}", Style.fg(C["border"]))

        for i, s in enumerate(sessions[:height - 3]):
            sid = s.get("id", "—")[:22]
            pat = s.get("pattern_matched", "—")[:14]
            agents = ", ".join(s.get("agents_used", []))[:18]
            outcome = s.get("outcome", "—")[:10]
            line = f" {sid:24} {pat:16} {agents:20} {outcome:12}"
            write_at(x, y + 2 + i, line[:width - 2], Style.fg(C["fg2"]))

    def render_findings_panel(self, x, y, width, height):
        """Findings detail panel (overlay)."""
        # Clear panel area first
        for cy in range(height):
            sys.stdout.write(f"{Style.goto(x + 1, y + cy + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")

        findings = self.ctx.get("findings", {})
        all_findings = []
        for agent, fs in findings.items():
            for f in fs:
                f["_agent"] = agent
                all_findings.append(f)
        all_findings.sort(key=lambda f: f.get("timestamp", ""), reverse=True)

        if not all_findings:
            write_at(x, y, f" {Style.CIRCLE} {styled('No findings recorded yet.', Style.DIM)}", Style.fg(C["fg3"]))
            return

        header = f" {'Agent':12} {'Severity':10} {'Summary':50}"
        write_at(x, y, header[:width - 2], Style.BOLD, Style.fg(C["accent"]))
        write_at(x, y + 1, f" {'─' * (width - 3)}", Style.fg(C["border"]))

        for i, f in enumerate(all_findings[:height - 3]):
            agent = f.get("_agent", "?")[:10]
            sev = f.get("severity", "info")[:8]
            sev_color = SEV_COLORS.get(sev, C["fg2"])
            summary = f.get("summary", "")[:48]
            line = f" {agent:12} {styled(sev.upper(), Style.fg(sev_color)):10} {summary[:width-30]}"
            write_at(x, y + 2 + i, line[:width - 2], Style.fg(C["fg"]))

    def render_help(self, x, y, width, height):
        """Help overlay panel."""
        # Clear panel area first
        for cy in range(height):
            sys.stdout.write(f"{Style.goto(x + 1, y + cy + 1)}{' ' * (width - 2)}{Style.clear_to_eol()}")

        help_lines = [
            f"  {Style.GEAR} {styled('OpenCode TUI Help', Style.BOLD, Style.fg(C['accent']))}",
            f"  {Style.H_LINE * (width - 6)}",
            "",
            f"  {styled('Dashboard Keys', Style.BOLD)}",
            f"    1     {styled('Resume', Style.fg(C['accent2']))}        Resume last OpenCode session",
            f"    2     {styled('Sessions', Style.fg(C['accent2']))}      Show session history",
            f"    3     {styled('Context', Style.fg(C['accent2']))}       Show full context dump",
            f"    4     {styled('Findings', Style.fg(C['accent2']))}      Show all agent findings",
            f"    5     {styled('Workflow', Style.fg(C['accent2']))}      Show workflow trace",
            f"    6     {styled('GitPush', Style.fg(C['accent2']))}       Push to GitHub",
            f"    7     {styled('Monitor', Style.fg(C['accent2']))}       Launch live monitor",
            f"    r     {styled('Refresh', Style.fg(C['accent2']))}       Force refresh all panels",
            f"    s     {styled('Sessions', Style.fg(C['accent2']))}      Browse session history",
            f"    c     {styled('Context', Style.fg(C['accent2']))}       Dump context JSON",
            f"    f     {styled('Findings', Style.fg(C['accent2']))}      Browse findings",
            f"    w     {styled('Workflow', Style.fg(C['accent2']))}      View workflow trace",
            f"    g     {styled('Git Push', Style.fg(C['accent2']))}      Push repo to GitHub",
            f"    ↑/↓   {styled('Scroll', Style.fg(C['accent2']))}        Scroll active panel",
            f"    q/ESC {styled('Quit', Style.fg(C['red']))}         Exit TUI",
            "",
            f"  {styled('Context Sharing System', Style.BOLD)}",
            f"    All findings from agents are automatically shared via",
            f"    ~/.config/opencode/shared/context.json",
            f"    Use 'oc-context' or this TUI to inspect the shared state.",
            "",
            f"  {styled('Press any key to close help', Style.DIM, Style.fg(C['fg3']))}",
        ]

        for i, line in enumerate(help_lines):
            if y + i < y + height - 1:
                write_at(x, y + i, line[:width - 3], Style.fg(C["fg"]))

    def render_message(self):
        """Flash message at top."""
        if self.message:
            msg = f"  {self.message}  "
            msg_x = (self.cols - len(msg)) // 2
            sys.stdout.write(f"{Style.goto(msg_x, 2)}{Style.bg(C['bg2'])}{Style.fg(C['accent'])}{msg}{Style.RESET}")
            self.clear_message()

    # ── Layout ─────────────────────────────────────────────────

    def layout_dashboard(self):
        """Render the default dashboard layout."""
        cols = self.cols
        rows = self.rows

        # Full clear before any drawing — eliminates scroll doubling
        sys.stdout.write(Style.erase_display())

        # Divide into panels
        header_h = 1
        footer_h = 1
        margin = 1
        content_top = header_h + 1
        content_bot = rows - footer_h

        # Top-left: Session info
        panel1_w = cols // 2 - 1
        panel1_h = 8
        panel1_x = 1
        panel1_y = content_top

        # Top-right: Context summary
        panel2_w = cols - panel1_w - 3
        panel2_x = panel1_x + panel1_w + 1
        panel2_y = content_top
        panel2_h = panel1_h

        # Bottom: Workflow trace
        panel3_y = panel1_y + panel1_h + 1
        panel3_h = content_bot - panel3_y

        # Render panels
        self.render_header()

        # Session panel (top-left)
        draw_box(panel1_y, panel1_x, panel1_w, panel1_h, " Session ", C["border"])
        self.render_session_panel(panel1_x, panel1_y + 1, panel1_w - 2, panel1_h - 2)

        # Context panel (top-right)
        draw_box(panel2_y, panel2_x, panel2_w, panel2_h, " Context ", C["border"])
        self.render_context_panel(panel2_x, panel2_y + 1, panel2_w - 2, panel2_h - 2)

        # Workflow panel (bottom)
        draw_box(panel3_y, 1, cols - 2, panel3_h, " Workflow ", C["border"])
        self.render_workflow_panel(1, panel3_y + 1, cols - 4, panel3_h - 2)

        self.render_footer()
        self.render_message()

    # ── Chat mode ───────────────────────────────────────────────

    def enter_chat(self):
        """Switch to chat mode, initializing if needed."""
        chat_mod = get_chat()
        if self.chat is None:
            self.chat = chat_mod.ChatUI(parent=self)
        self.mode = "chat"
        self.refresh(force=True)

    def render_chat(self):
        """Render the chat interface."""
        if self.chat is None:
            return
        # Poll for agent activity
        self.chat.poll_activity()
        self.chat.render(self.cols, self.rows)

    def handle_chat_key(self, key):
        """Handle keyboard input in chat mode."""
        if self.chat is None:
            return

        action = self.chat.handle_key(key)

        if action == "quit":
            self.running = False
        elif action == "dashboard":
            self.mode = "dashboard"
            self.refresh(force=True)

        # Refresh after send/new
        if action in ("send", "new"):
            self.refresh(force=True)

    # ── Actions ─────────────────────────────────────────────────

    def action_quit(self):
        self.running = False

    def action_resume(self):
        self.set_message("Resuming last session...")
        subprocess.Popen(["ocr"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def action_gitpush(self):
        self.set_message("Pushing to GitHub...")
        subprocess.Popen(["oc-gitpush"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def action_monitor(self):
        self.set_message("Launching monitor...")
        subprocess.Popen(["oc-monitor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def action_context_dump(self):
        """Full context dump to stdout (temporarily exits TUI)."""
        self.cleanup()
        ctx = load_context()
        print(json.dumps(ctx, indent=2))
        print("\nPress Enter to return to TUI...")
        input()
        self.setup()
        self.refresh(force=True)

    def action_sessions(self):
        self.sessions = get_sessions()
        self.mode = "sessions"

    def action_findings(self):
        self.mode = "findings"

    def action_back(self):
        self.mode = "dashboard"

    # ── Main loop ───────────────────────────────────────────────

    def setup(self):
        """Initialize terminal for TUI mode — enter raw mode once."""
        import termios
        import tty
        fd = sys.stdin.fileno()
        self._old_term = termios.tcgetattr(fd)
        tty.setraw(fd)
        sys.stdout.write(Style.erase_display())
        sys.stdout.write(Style.hide_cursor())
        sys.stdout.flush()

    def cleanup(self):
        """Restore terminal after TUI mode — restore original attrs."""
        import termios
        sys.stdout.write(Style.show_cursor())
        sys.stdout.write(f"{Style.goto(1, self.rows)}\n")
        if self._old_term is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_term)
            except (ValueError, OSError):
                pass
            self._old_term = None
        sys.stdout.flush()

    def run(self):
        """Main event loop."""
        self.setup()
        try:
            while self.running:
                self.refresh()
                self.render_dashboard()

                key = read_key(0.5)
                if key is None:
                    continue

                self.handle_key(key)

        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def render_dashboard(self):
        """Route to current mode renderer."""
        if self.mode == "chat":
            self.render_chat()
            return

        if self.show_help:
            # Help overlay
            self.layout_dashboard()
            # Overlay help
            overlay_x = max(2, (self.cols - 60) // 2)
            overlay_y = max(2, (self.rows - 24) // 2)
            overlay_w = min(60, self.cols - 4)
            overlay_h = min(24, self.rows - 4)
            draw_box(overlay_y, overlay_x, overlay_w, overlay_h, " Help ", C["accent"])
            self.render_help(overlay_x, overlay_y + 1, overlay_w - 2, overlay_h - 2)
            sys.stdout.flush()
            return

        if self.mode == "dashboard":
            self.layout_dashboard()
            sys.stdout.flush()
        elif self.mode == "sessions":
            self.layout_dashboard()
            # Overlay sessions panel
            overlay_x = max(4, (self.cols - 70) // 2)
            overlay_y = max(3, (self.rows - 18) // 2)
            overlay_w = min(70, self.cols - 8)
            overlay_h = min(18, self.rows - 6)
            draw_box(overlay_y, overlay_x, overlay_w, overlay_h, " Sessions ", C["teal"])
            self.render_sessions_panel(overlay_x, overlay_y + 1, overlay_w - 2, overlay_h - 2)
            write_at(overlay_x, overlay_y + overlay_h - 2, f"  {Style.DIM}{Style.fg(C['fg3'])}Press any key to close{Style.RESET}")
            sys.stdout.flush()
        elif self.mode == "findings":
            self.layout_dashboard()
            overlay_x = max(4, (self.cols - 70) // 2)
            overlay_y = max(3, (self.rows - 18) // 2)
            overlay_w = min(70, self.cols - 8)
            overlay_h = min(18, self.rows - 6)
            draw_box(overlay_y, overlay_x, overlay_w, overlay_h, " Findings ", C["purple"])
            self.render_findings_panel(overlay_x, overlay_y + 1, overlay_w - 2, overlay_h - 2)
            write_at(overlay_x, overlay_y + overlay_h - 2, f"  {Style.DIM}{Style.fg(C['fg3'])}Press any key to close{Style.RESET}")
            sys.stdout.flush()

    def handle_key(self, key):
        """Dispatch keyboard input."""
        if self.mode == "chat":
            self.handle_chat_key(key)
            return

        if self.show_help:
            self.show_help = False
            self.refresh(force=True)
            return

        if self.mode in ("sessions", "findings"):
            if key in ("ESC", "q", "Q", "ENTER"):
                self.mode = "dashboard"
                self.refresh(force=True)
            return

        if key == "q" or key == "Q":
            self.action_quit()
        elif key == "h" or key == "?" or key == "H":
            self.show_help = True
        elif key == "r" or key == "R":
            self.refresh(force=True)
        elif key == "1":
            self.action_resume()
        elif key == "2":
            self.action_sessions()
        elif key == "3":
            self.action_context_dump()
        elif key == "4":
            self.action_findings()
        elif key == "5":
            self.mode = "dashboard"
            self.refresh(force=True)
        elif key == "6":
            self.action_gitpush()
        elif key == "7":
            self.action_monitor()
        elif key == "TAB" or key == "t" or key == "T":  # Tab or t → Chat
            self.enter_chat()
        elif key == "s" or key == "S":
            self.action_sessions()
        elif key == "c" or key == "C":
            self.action_context_dump()
        elif key == "f" or key == "F":
            self.action_findings()
        elif key == "w" or key == "W":
            self.set_message("Workflow trace shown in dashboard.")
        elif key == "g" or key == "G":
            self.action_gitpush()
        elif key == "m" or key == "M":
            self.action_monitor()
        elif key == "UP":
            self.panel_scroll["wf"] = max(0, self.panel_scroll["wf"] - 1)
        elif key == "DOWN":
            trace_len = len(self.ctx.get("workflow_trace", []))
            # Visible lines in workflow panel = inner_height - 1
            # inner_height = panel3_h - 2; panel3_h = (rows-1) - (2+8+1)
            wf_inner = self.rows - 1 - 11 - 2   # (rows-1) - panel3_y - 2
            max_visible = max(1, wf_inner - 1)
            max_scroll = max(0, trace_len - max_visible)
            self.panel_scroll["wf"] = min(max_scroll, self.panel_scroll["wf"] + 1)


def dump_snapshot():
    """One-shot status snapshot (no interactive TUI)."""
    ctx = load_context()
    session = ctx.get("session", {})
    state = ctx.get("state", {})
    findings = ctx.get("findings", {})
    trace = ctx.get("workflow_trace", [])

    print("=" * 50)
    print("  OpenCode Status Snapshot")
    print("=" * 50)
    print(f"  Session:    {session.get('current_id', '—')}")
    print(f"  Pattern:    {session.get('workflow_pattern', '—')}")
    print(f"  Agents:     {', '.join(session.get('active_agents', [])) or 'none'}")
    print(f"  Updated:    {time_ago(state.get('last_updated_at', ''))} by {state.get('last_updated_by', '—')}")
    print()

    finding_counts = {a: len(fs) for a, fs in findings.items() if fs}
    if finding_counts:
        print(f"  Findings ({sum(finding_counts.values())}):")
        for a, c in sorted(finding_counts.items()):
            sevs = {}
            for f in findings[a]:
                sevs[f.get("severity", "info")] = sevs.get(f.get("severity", "info"), 0) + 1
            sev_str = ", ".join(f"{k}={v}" for k, v in sorted(sevs.items()))
            print(f"    {a:16} {c:3}  [{sev_str}]")

    if trace:
        print(f"\n  Workflow ({len(trace)} steps):")
        for step in trace[-5:]:
            agent = step.get("agent", "?")
            status = step.get("status", "?")
            summary = step.get("summary", "")[:60]
            print(f"    [{status:10}] {agent:12} {summary}")

    print()
    print(f"  Context: {CONTEXT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    if "--dump" in sys.argv:
        dump_snapshot()
    else:
        app = OpenCodeTUI()
        app.run()

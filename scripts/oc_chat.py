"""
oc_chat — Terminal-based chat interface for OpenCode TUI
=========================================================
Multi-line input, markdown rendering, agent activity feed,
message persistence, and full keyboard navigation.

Integrates with oc-tui.py via ChatUI class.
Zero external dependencies — pure Python stdlib + ANSI codes.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────
CONFIG_DIR = os.path.expanduser("~/.config/opencode")
CHAT_HISTORY_FILE = os.path.join(CONFIG_DIR, "shared", "chat_history.json")
CONTEXT_FILE = os.path.join(CONFIG_DIR, "shared", "context.json")

# ── ANSI helpers (same as oc-tui for consistency) ──────────────────
class S:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    REVERSE = "\033[7m"

    @staticmethod
    def fg(c): return f"\033[38;5;{c}m"

    @staticmethod
    def bg(c): return f"\033[48;5;{c}m"

    @staticmethod
    def goto(x, y): return f"\033[{y};{x}H"

    @staticmethod
    def save(): return "\033[s"

    @staticmethod
    def restore(): return "\033[u"

    @staticmethod
    def clear_line(): return "\033[K"

    @staticmethod
    def erase_display(): return "\033[2J\033[H"

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

    H_LINE = "─"
    V_LINE = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"


# ── Color palette ──────────────────────────────────────────────────
C = {
    "bg": 16, "bg2": 233, "fg": 255, "fg2": 250, "fg3": 240,
    "accent": 75, "accent2": 39, "green": 83, "yellow": 221,
    "orange": 208, "red": 196, "purple": 141, "pink": 212,
    "teal": 43, "border": 237,
    "user_msg": 39,      # bright cyan for user messages
    "ai_msg": 83,        # green for AI responses
    "agent_run": 75,     # blue for running agents
    "agent_done": 83,    # green for completed agents
    "agent_err": 196,    # red for failed agents
    "code_bg": 234,      # dark gray for code blocks
    "code_fg": 187,      # light yellow for code text
    "timestamp": 240,    # dim for timestamps
    "input_bg": 232,     # input area background
    "input_fg": 255,     # input text
    "header_bg": 17,     # dark blue header
}

# ── Data models ────────────────────────────────────────────────────
def styled(text, *styles):
    return f"{''.join(styles)}{text}{S.RESET}"


def timestamp_now():
    return datetime.now().isoformat()


def time_short(iso_str):
    """Convert ISO timestamp to HH:MM."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def load_chat_history():
    """Load chat history from JSON file."""
    try:
        with open(CHAT_HISTORY_FILE) as f:
            data = json.load(f)
        return data.get("conversations", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_conversation(conversation):
    """Save a single conversation to chat history."""
    history = []
    try:
        with open(CHAT_HISTORY_FILE) as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = {"meta": {"version": "1.0"}, "conversations": []}

    # Update or append
    convs = history.setdefault("conversations", [])
    found = False
    for i, c in enumerate(convs):
        if c.get("id") == conversation.get("id"):
            convs[i] = conversation
            found = True
            break
    if not found:
        convs.append(conversation)

    # Keep max 50 conversations
    history["conversations"] = convs[-50:]

    os.makedirs(os.path.dirname(CHAT_HISTORY_FILE), exist_ok=True)
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ── Markdown to ANSI renderer ─────────────────────────────────────
def markdown_to_ansi(text, width=60):
    """
    Convert simple markdown to ANSI-colored terminal text.
    Supports: bold, italic, inline code, code blocks, lists, headers.
    Returns list of (x, y_offset, ansi_text) for rendering.
    """
    lines = text.split("\n")
    output = []
    in_code_block = False
    code_buf = []
    line_num = 0

    i = 0
    while i < len(lines):
        raw = lines[i]

        # Code blocks
        if raw.startswith("```"):
            if in_code_block:
                # End code block — render buffer
                for code_line in code_buf:
                    display = code_line[:width]
                    output.append((2, line_num, styled(display, S.fg(C["code_fg"]), S.bg(C["code_bg"]))))
                    line_num += 1
                code_buf = []
                in_code_block = False
                i += 1
                continue
            else:
                in_code_block = True
                lang = raw[3:].strip()
                if lang:
                    output.append((2, line_num, styled(f" {lang}", S.DIM, S.fg(C["fg3"]), S.bg(C["code_bg"]))))
                    line_num += 1
                i += 1
                continue

        if in_code_block:
            code_buf.append(raw)
            i += 1
            continue

        # Headers
        if raw.startswith("# "):
            display = raw[2:].strip()[:width]
            output.append((2, line_num, styled(display, S.BOLD, S.fg(C["accent"]))))
            line_num += 1
            i += 1
            continue
        elif raw.startswith("## "):
            display = raw[3:].strip()[:width]
            output.append((2, line_num, styled(display, S.BOLD, S.fg(C["teal"]))))
            line_num += 1
            i += 1
            continue
        elif raw.startswith("### "):
            display = raw[4:].strip()[:width]
            output.append((2, line_num, styled(display, S.BOLD, S.fg(C["fg2"]))))
            line_num += 1
            i += 1
            continue

        # Horizontal rules
        if raw.strip().startswith("---") or raw.strip().startswith("___"):
            hr = styled(f" {'─' * (width - 4)} ", S.DIM, S.fg(C["border"]))
            output.append((2, line_num, hr))
            line_num += 1
            i += 1
            continue

        # Blockquotes
        if raw.startswith("> "):
            content = raw[2:].strip()[:width - 4]
            display = f" ▎{content}"
            output.append((2, line_num, styled(display, S.ITALIC, S.fg(C["fg2"]))))
            line_num += 1
            i += 1
            continue

        # Lists
        is_list = False
        if raw.strip().startswith("- ") or raw.strip().startswith("* "):
            content = raw.strip()[2:].strip()[:width - 6]
            display = f" {S.fg(C['accent'])}●{S.RESET} {content}"
            output.append((2, line_num, display))
            line_num += 1
            is_list = True
        elif re.match(r"^\d+[.)]\s", raw.strip()):
            content = re.sub(r"^\d+[.)]\s", "", raw.strip())[:width - 8]
            num = raw.strip().split(".")[0] if "." in raw.strip() else raw.strip().split(")")[0]
            display = f" {S.fg(C['accent'])}{num}.{S.RESET} {content}"
            output.append((2, line_num, display))
            line_num += 1
            is_list = True

        if is_list:
            i += 1
            continue

        # Inline formatting
        formatted = raw[:width]

        # Inline code `code`
        formatted = re.sub(
            r"`([^`]+)`",
            lambda m: styled(m.group(1), S.bg(C["code_bg"]), S.fg(C["code_fg"])),
            formatted,
        )

        # Bold **text**
        formatted = re.sub(
            r"\*\*(.+?)\*\*",
            lambda m: styled(m.group(1), S.BOLD),
            formatted,
        )

        # Italic *text*
        formatted = re.sub(
            r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
            lambda m: styled(m.group(1), S.ITALIC),
            formatted,
        )

        # Empty lines
        if not raw.strip():
            output.append((2, line_num, ""))
            line_num += 1
            i += 1
            continue

        # Regular paragraph text — word wrap
        words = formatted.split()
        line_buf = ""
        for word in words:
            test = f"{line_buf} {word}".strip()
            # Strip ANSI codes for width calculation
            clean = re.sub(r"\033\[[0-9;]*m", "", test)
            if len(clean) > width - 4:
                if line_buf:
                    output.append((2, line_num, line_buf))
                    line_num += 1
                line_buf = word
            else:
                line_buf = test
        if line_buf:
            output.append((2, line_num, line_buf))
            line_num += 1

        i += 1

    return output


# ── Agent activity tracker ────────────────────────────────────────
class AgentActivity:
    """Polls shared context for agent workflow activity."""

    def __init__(self):
        self.last_trace_len = 0
        self.last_findings = {}
        self.active = []

    def poll(self):
        """Check for new agent activity. Returns list of activity strings."""
        activities = []
        try:
            with open(CONTEXT_FILE) as f:
                ctx = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return activities

        # Check workflow trace for new steps
        trace = ctx.get("workflow_trace", [])
        if len(trace) > self.last_trace_len:
            for step in trace[self.last_trace_len:]:
                agent = step.get("agent", "?")
                status = step.get("status", "?")
                summary = step.get("summary", "")
                icon = {
                    "completed": styled("✓", S.fg(C["agent_done"])),
                    "running": styled("●", S.fg(C["agent_run"])),
                    "failed": styled("✗", S.fg(C["agent_err"])),
                    "pending": styled("○", S.fg(C["fg3"])),
                }.get(status, "?")
                activities.append(f" {icon} {styled(agent, S.BOLD)} {summary}")
            self.last_trace_len = len(trace)

        # Check for new findings
        findings = ctx.get("findings", {})
        for agent, fs in findings.items():
            prev_len = self.last_findings.get(agent, 0)
            if len(fs) > prev_len:
                for f in fs[prev_len:]:
                    sev = f.get("severity", "info")
                    sev_color = {"critical": C["red"], "high": C["orange"], "medium": C["yellow"],
                                 "low": C["fg2"], "info": C["teal"]}.get(sev, C["fg2"])
                    summary = f.get("summary", "")
                    activities.append(
                        f" {styled('◈', S.fg(sev_color))} {styled(agent, S.BOLD)} "
                        f"[{styled(sev.upper(), S.fg(sev_color))}] {summary}"
                    )
            self.last_findings[agent] = len(fs)

        return activities


# ── Chat UI ────────────────────────────────────────────────────────
class ChatUI:
    """
    Full-featured terminal chat interface.

    Layout:
      ┌─ Header ───────────────────────────────────────┐
      │ Message area (scrollable)                       │
      │                                                 │
      │ user: Hello                                     │
      │                                                 │
      │ ai:   Hi there!                                 │
      │                                                 │
      │ ● agent running...                              │
      │                                                 │
      ├─ Input area ────────────────────────────────────┤
      │ > Type your message here...                     │
      ├─ Status bar ────────────────────────────────────┤
      │ [F1]Help [Ctrl+S]Send [Tab]Dashboard [q]Quit    │
      └─────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.cols, self.rows = shutil.get_terminal_size((80, 24))

        # Layout dimensions
        self.header_h = 1
        self.input_h = 4       # 3 visible lines + border
        self.status_h = 1
        self.msg_top = self.header_h
        self.msg_bot = self.rows - self.input_h - self.status_h
        self.msg_height = self.msg_bot - self.msg_top

        # Chat state
        self.messages = []
        self.input_lines = [""]
        self.input_cursor = (0, 0)  # (line, col)
        self.scroll_offset = 0
        self.conversation_id = None
        self.conversation_title = "Untitled"
        self.agent_activity = AgentActivity()
        self.activity_log = []
        self.send_callback = None

        # Load existing or start new
        self._load_latest()

    def _load_latest(self):
        """Load the most recent conversation."""
        convs = load_chat_history()
        if convs:
            latest = convs[-1]
            self.messages = latest.get("messages", [])
            self.conversation_id = latest.get("id")
            self.conversation_title = latest.get("title", "Untitled")
            self.scroll_offset = max(0, len(self._render_messages()) - self.msg_height + 1)

    @property
    def title(self):
        return self.conversation_title or "Untitled"

    # ── Message management ───────────────────────────────

    def add_user_message(self, text):
        msg = {
            "role": "user",
            "content": text,
            "timestamp": timestamp_now(),
        }
        self.messages.append(msg)
        self._scroll_to_bottom()
        self._save()
        return msg

    def add_ai_message(self, text):
        msg = {
            "role": "assistant",
            "content": text,
            "timestamp": timestamp_now(),
        }
        self.messages.append(msg)
        self._scroll_to_bottom()
        self._save()
        return msg

    def add_activity(self, activity_text):
        self.activity_log.append({
            "text": activity_text,
            "timestamp": timestamp_now(),
        })
        # Keep last 100
        self.activity_log = self.activity_log[-100:]

    def _scroll_to_bottom(self):
        rendered = self._render_messages()
        self.scroll_offset = max(0, len(rendered) - self.msg_height + 1)

    def _save(self):
        """Save current conversation."""
        if not self.conversation_id:
            self.conversation_id = f"chat-{int(time.time())}"
        conv = {
            "id": self.conversation_id,
            "title": self.conversation_title,
            "messages": self.messages,
            "updated_at": timestamp_now(),
            "message_count": len(self.messages),
        }
        save_conversation(conv)

    # ── Send message ─────────────────────────────────────

    def send_message(self):
        """Send the current input as a message."""
        text = "\n".join(self.input_lines).strip()
        if not text:
            return

        # Auto-title from first message
        if not self.messages:
            self.conversation_title = text[:50] + ("..." if len(text) > 50 else "")

        self.add_user_message(text)
        self.input_lines = [""]
        self.input_cursor = (0, 0)

        # Execute via callback or subprocess
        if self.send_callback:
            self.send_callback(text)
        else:
            self._default_send(text)

    def _default_send(self, text):
        """Default: run via opencode CLI in background."""
        try:
            subprocess.Popen(
                ["opencode", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.add_ai_message(f"⏳ Sent to OpenCode. Check the main session for response.")
        except FileNotFoundError:
            self.add_ai_message("⚠ OpenCode CLI not found. Install it to send messages.")

    def set_send_callback(self, callback):
        """Set a custom handler for sending messages."""
        self.send_callback = callback

    # ── Render ────────────────────────────────────────────

    def _render_messages(self):
        """Render all messages into a list of display lines."""
        display_lines = []
        for msg in self.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            ts = msg.get("timestamp", "")

            # Role label
            if role == "user":
                label = styled(" you ", S.BOLD, S.bg(C["user_msg"]), S.fg(C["bg"]))
            elif role == "assistant":
                label = styled(" oc  ", S.BOLD, S.bg(C["ai_msg"]), S.fg(C["bg"]))
            else:
                label = styled(f" {role[:4]} ", S.DIM, S.fg(C["fg3"]))

            # Timestamp
            tstr = time_short(ts)
            ts_tag = styled(f" {tstr} ", S.DIM, S.fg(C["timestamp"]))

            # Render content as markdown
            rendered = markdown_to_ansi(content, self.cols - 6)

            # First line gets the label
            if rendered:
                first_line = rendered[0]
                first_line = (first_line[0], first_line[1],
                              f"{label}{ts_tag}{first_line[2]}")
                display_lines.append(first_line)
                display_lines.extend(rendered[1:])
            else:
                display_lines.append((2, len(display_lines), label))

            # Spacer between messages
            display_lines.append((0, len(display_lines), ""))

        # Activity log
        for act in self.activity_log[-10:]:
            display_lines.append((2, len(display_lines), act["text"]))
        if self.activity_log:
            display_lines.append((0, len(display_lines), ""))

        return display_lines

    def render(self, cols, rows):
        """Render the full chat interface."""
        self.cols = cols
        self.rows = rows
        self.msg_top = self.header_h
        self.msg_bot = rows - self.input_h - self.status_h
        self.msg_height = self.msg_bot - self.msg_top

        # Clear
        sys.stdout.write(S.erase_display())

        # ── Header ──
        self._render_header()

        # ── Message area ──
        self._render_messages_area()

        # ── Input area ──
        self._render_input()

        # ── Status bar ──
        self._render_status()

        sys.stdout.flush()

    def _render_header(self):
        """Render top header bar."""
        full = f"{' ' * self.cols}"
        sys.stdout.write(f"{S.goto(1, 1)}{S.bg(C['header_bg'])}{full}{S.RESET}")

        title = f" 💬 {self.title[:40]}"
        sys.stdout.write(f"{S.goto(1, 1)}{S.bg(C['header_bg'])}"
                         f"{styled(title, S.BOLD, S.fg(C['accent']))}"
                         f"{S.RESET}")

        mid = f" {len(self.messages)} msgs "
        mid_x = (self.cols - len(mid)) // 2
        sys.stdout.write(f"{S.goto(mid_x, 1)}{S.bg(C['header_bg'])}"
                         f"{styled(mid, S.DIM, S.fg(C['fg2']))}"
                         f"{S.RESET}")

        right = f" {styled('Tab Dashboard', S.fg(C['fg3']))}  {styled('[q] Quit', S.fg(C['red']))}  "
        right_x = self.cols - len(right) + 1
        sys.stdout.write(f"{S.goto(right_x, 1)}{S.bg(C['header_bg'])}"
                         f"{right}"
                         f"{S.RESET}")

    def _render_messages_area(self):
        """Render the scrollable message history."""
        msg_lines = self._render_messages()
        total = len(msg_lines)
        scroll = self.scroll_offset

        # Ensure scroll is in bounds
        if scroll > max(0, total - self.msg_height):
            scroll = max(0, total - self.msg_height)
        if scroll < 0:
            scroll = 0
        self.scroll_offset = scroll

        # Clear message area
        for y in range(self.msg_top, self.msg_bot):
            sys.stdout.write(f"{S.goto(1, y + 1)}{S.clear_line()}")

        # Render visible lines
        for i in range(self.msg_height):
            idx = scroll + i
            if idx < total:
                x_offset, _, text = msg_lines[idx]
                y = self.msg_top + i
                sys.stdout.write(f"{S.goto(x_offset + 1, y + 1)}{text}{S.clear_line()}")
            else:
                break

        # Scroll indicator
        if total > self.msg_height:
            pct = scroll / max(1, total - self.msg_height)
            bar_w = self.cols - 2
            filled = int(bar_w * pct)
            bar_chars = "░" * filled + "▒" + "░" * (bar_w - filled - 1)
            sys.stdout.write(f"{S.goto(1, self.msg_bot + 1)}"
                             f"{styled(bar_chars, S.DIM, S.fg(C['border']))}"
                             f"{S.clear_line()}")

    def _render_input(self):
        """Render the multi-line input area at bottom."""
        input_top = self.rows - self.input_h - self.status_h
        input_bot = self.rows - self.status_h
        input_width = self.cols - 4

        # Draw input box borders
        border_y = input_top
        sys.stdout.write(f"{S.goto(1, border_y + 1)}"
                         f"{S.fg(C['border'])}│{S.RESET}"
                         f"{' ' * (self.cols - 2)}"
                         f"{S.fg(C['border'])}│{S.RESET}")

        # Input area background
        for y in range(input_top + 1, input_bot):
            sys.stdout.write(f"{S.goto(1, y + 1)}"
                             f"{S.bg(C['input_bg'])}{' ' * self.cols}{S.RESET}")

        # Prompt prefix
        prompt = f"{S.fg(C['accent'])}>S.RESET "
        prompt_len = 2

        # Render input lines
        cursor_line, cursor_col = self.input_cursor
        display_lines = self.input_lines[:input_bot - input_top - 1]  # Leave room for cursor
        if not display_lines:
            display_lines = [""]

        for i, line in enumerate(display_lines):
            y = input_top + 1 + i
            if y >= input_bot:
                break
            prefix = prompt if i == 0 else "  "
            clean = re.sub(r"\033\[[0-9;]*m", "", line)
            display = f"{S.bg(C['input_bg'])}{prefix}{clean[:input_width]}{' ' * (input_width - len(clean[:input_width]))}{S.RESET}"
            sys.stdout.write(f"{S.goto(1, y + 1)}{display}")

        # Place cursor
        cursor_y = input_top + 1 + cursor_line
        cursor_x = prompt_len + cursor_col + 1
        if cursor_y < input_bot and cursor_y >= input_top + 1:
            sys.stdout.write(f"{S.goto(cursor_x, cursor_y + 1)}")

    def _render_status(self):
        """Render bottom status bar with key hints."""
        y = self.rows
        full = f"{' ' * self.cols}"
        sys.stdout.write(f"{S.goto(1, y)}{S.bg(C['bg2'])}{full}{S.RESET}")

        hints = [
            ("Ctrl+S", "Send", C["green"]),
            ("Ctrl+N", "New", C["accent"]),
            ("Tab", "Dash", C["accent"]),
            ("↑↓", "Nav", C["fg3"]),
            ("PgUp/Dn", "Scroll", C["fg3"]),
            ("q", "Quit", C["red"]),
        ]

        x = 2
        for key, label, color in hints:
            item = f" {styled(f'[{key}]', S.BOLD, S.fg(color))} {styled(label, S.fg(C['fg2']))} "
            sys.stdout.write(f"{S.goto(x, y)}{S.bg(C['bg2'])}{item}{S.RESET}")
            x += len(item)

    # ── Input handling ────────────────────────────────────

    def handle_key(self, key):
        """
        Handle keyboard input for chat mode.
        Returns action string for the main loop:
          None  → continue
          "quit" → exit TUI
          "dashboard" → switch to dashboard
          "send" → message was sent
          "new" → new conversation
        """
        if key == "q" or key == "Q":
            return "quit"
        elif key == "\t":  # Tab
            return "dashboard"

        # Ctrl+S — send
        if key == "\x13":  # Ctrl+S
            self.send_message()
            return "send"

        # Ctrl+N — new conversation
        if key == "\x0e":  # Ctrl+N
            self._new_conversation()
            return "new"

        # Ctrl+W — delete word backward
        if key == "\x17":
            self._delete_word_backward()
            return None

        # Ctrl+U — delete line
        if key == "\x15":
            self._delete_line()
            return None

        # Ctrl+L — clear
        if key == "\x0c":
            return None

        if key == "UP":
            self._scroll_up()
            return None
        elif key == "DOWN":
            self._scroll_down()
            return None
        elif key == "PAGE_UP":
            self.scroll_offset = max(0, self.scroll_offset - self.msg_height)
            return None
        elif key == "PAGE_DOWN":
            self.scroll_offset += self.msg_height
            return None
        elif key == "HOME":
            self.scroll_offset = 0
            return None
        elif key == "END":
            self._scroll_to_bottom()
            return None

        # Input editing
        elif key == "ENTER" or key == "\r" or key == "\n":
            self._input_newline()
            return None
        elif key == "BACK" or key == "\x7f":
            self._input_backspace()
            return None
        elif key == "DEL":
            self._input_delete()
            return None
        elif key == "LEFT":
            self._input_left()
            return None
        elif key == "RIGHT":
            self._input_right()
            return None

        # Regular character
        elif key and len(key) == 1 and ord(key) >= 32:
            self._input_char(key)
            return None

        return None

    def _new_conversation(self):
        """Start a new conversation."""
        self.messages = []
        self.input_lines = [""]
        self.input_cursor = (0, 0)
        self.scroll_offset = 0
        self.activity_log = []
        self.conversation_id = f"chat-{int(time.time())}"
        self.conversation_title = "Untitled"
        self.agent_activity = AgentActivity()

    # ── Input editing ────────────────────────────────────

    def _input_char(self, ch):
        line, col = self.input_cursor
        if line < len(self.input_lines):
            current = self.input_lines[line]
            self.input_lines[line] = current[:col] + ch + current[col:]
            self.input_cursor = (line, col + 1)

    def _input_backspace(self):
        line, col = self.input_cursor
        if col > 0:
            current = self.input_lines[line]
            self.input_lines[line] = current[:col - 1] + current[col:]
            self.input_cursor = (line, col - 1)
        elif line > 0:
            # Join with previous line
            prev = self.input_lines[line - 1]
            self.input_lines[line - 1] = prev + self.input_lines[line]
            self.input_lines.pop(line)
            self.input_cursor = (line - 1, len(prev))

    def _input_delete(self):
        line, col = self.input_cursor
        if line < len(self.input_lines):
            current = self.input_lines[line]
            if col < len(current):
                self.input_lines[line] = current[:col] + current[col + 1:]
            elif line + 1 < len(self.input_lines):
                self.input_lines[line] = current + self.input_lines[line + 1]
                self.input_lines.pop(line + 1)

    def _input_newline(self):
        line, col = self.input_cursor
        current = self.input_lines[line]
        self.input_lines[line] = current[:col]
        self.input_lines.insert(line + 1, current[col:])
        self.input_cursor = (line + 1, 0)

    def _input_left(self):
        line, col = self.input_cursor
        if col > 0:
            self.input_cursor = (line, col - 1)
        elif line > 0:
            self.input_cursor = (line - 1, len(self.input_lines[line - 1]))

    def _input_right(self):
        line, col = self.input_cursor
        if line < len(self.input_lines):
            current = self.input_lines[line]
            if col < len(current):
                self.input_cursor = (line, col + 1)
            elif line + 1 < len(self.input_lines):
                self.input_cursor = (line + 1, 0)

    def _delete_word_backward(self):
        line, col = self.input_cursor
        current = self.input_lines[line]
        if col > 0:
            # Delete until start of word or whitespace
            new_col = col
            while new_col > 0 and current[new_col - 1] == " ":
                new_col -= 1
            while new_col > 0 and current[new_col - 1] != " ":
                new_col -= 1
            self.input_lines[line] = current[:new_col] + current[col:]
            self.input_cursor = (line, new_col)

    def _delete_line(self):
        line, _ = self.input_cursor
        self.input_lines[line] = ""
        self.input_cursor = (line, 0)

    def _scroll_up(self):
        self.scroll_offset = max(0, self.scroll_offset - 1)

    def _scroll_down(self):
        total = len(self._render_messages())
        self.scroll_offset = min(max(0, total - self.msg_height), self.scroll_offset + 1)

    # ── Polling ──────────────────────────────────────────

    def poll_activity(self):
        """Check for new agent activity and update feed."""
        activities = self.agent_activity.poll()
        for act in activities:
            self.add_activity(act)


# ── Quick test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    # Run in test mode — just dump markdown rendering
    test_md = """# Hello World

This is a **bold** and *italic* test.

```
code block here
print("hello")
```

- List item 1
- List item 2

> A blockquote for testing

And a regular paragraph with some `inline code` to show off.
"""
    result = markdown_to_ansi(test_md, 60)
    for _, _, text in result:
        clean = re.sub(r"\033\[[0-9;]*m", "", text)
        print(f"  {clean}")

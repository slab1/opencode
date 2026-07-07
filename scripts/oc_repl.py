#!/usr/bin/env python3
"""
oc_repl — OpenCode REPL engine
================================
Interactive Read-Eval-Print Loop that manages a persistent opencode server,
sends messages via --attach, and streams responses via DB polling.

Two modes:
  - Standalone REPL:  python3 oc_repl.py
  - Library import:   from oc_repl import OpenCodeREPL

Zero external dependencies — pure Python stdlib.
"""

import json
import os
import select
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

# ── Paths ──────────────────────────────────────────────────────────
DEFAULT_PORT = 4099
OPENCODE_DB = os.path.expanduser(
    "/public/.local/share/opencode/opencode.db"
)
OPCODE_BIN = shutil.which("opencode") or "/usr/local/bin/opencode"
CONFIG_DIR = os.path.expanduser("~/.config/opencode")
CONTEXT_FILE = os.path.join(CONFIG_DIR, "shared", "context.json")


# ── Exceptions ─────────────────────────────────────────────────────
class REPLError(Exception):
    """Base exception for REPL errors."""


class ServerStartError(REPLError):
    """Server failed to start."""


class SendError(REPLError):
    """Failed to send message."""


# ── ANSI helpers (standalone REPL) ─────────────────────────────────
class S:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    @staticmethod
    def fg(c): return f"\033[38;5;{c}m"

    @staticmethod
    def bg(c): return f"\033[48;5;{c}m"

    ACCENT = "\033[38;5;75m"
    GREEN = "\033[38;5;83m"
    YELLOW = "\033[38;5;221m"
    RED = "\033[38;5;196m"
    ORANGE = "\033[38;5;208m"
    PURPLE = "\033[38;5;141m"
    TEAL = "\033[38;5;43m"
    GRAY = "\033[38;5;240m"
    PINK = "\033[38;5;212m"
    CODE_BG = "\033[48;5;235m"

    CLEAR_LINE = "\033[K"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

def styled(text, *styles):
    return f"{''.join(styles)}{text}{S.RESET}"

# Code syntax highlighting map
CODE_LANG_COLORS = {
    "python": S.ACCENT,
    "javascript": S.YELLOW,
    "typescript": S.TEAL,
    "js": S.YELLOW,
    "ts": S.TEAL,
    "bash": S.GREEN,
    "sh": S.GREEN,
    "shell": S.GREEN,
    "json": S.ORANGE,
    "yaml": S.PURPLE,
    "yml": S.PURPLE,
    "html": S.ORANGE,
    "css": S.PINK,
    "sql": S.TEAL,
    "go": S.ACCENT,
    "rust": S.ORANGE,
    "ruby": S.RED,
    "c": S.ACCENT,
    "cpp": S.PURPLE,
}


# ── REPL Engine ────────────────────────────────────────────────────
class OpenCodeREPL:
    """
    OpenCode REPL engine.

    Manages a persistent opencode server, sends messages via --attach,
    and streams response parts via DB polling.

    Usage:
        repl = OpenCodeREPL()
        repl.ensure_server()
        for ptype, data in repl.send("hello"):
            print(ptype, data)
        repl.close()
    """

    def __init__(self, port=None, db_path=None, bin_path=None):
        self.port = port or DEFAULT_PORT
        self.server_url = f"http://127.0.0.1:{self.port}"
        self.db_path = db_path or OPENCODE_DB
        self.bin_path = bin_path or OPCODE_BIN
        self.server_process = None
        self._server_pid = None

    # ── Server management ─────────────────────────────────

    COMMON_PORTS = [4096, 4097, 4098, 4099, 4100]

    def ensure_server(self, timeout=30):
        """Start the opencode server if not already running.

        First checks if our port is serving, then checks common ports
        (in case another server like opencode web is already running).
        Returns True if server is ready, raises ServerStartError on failure.
        """
        # Check our configured port first
        if self._is_server_running():
            return True

        # Check common ports for an existing server
        for port in self.COMMON_PORTS:
            if port == self.port:
                continue
            test_url = f"http://127.0.0.1:{port}"
            try:
                resp = urllib.request.urlopen(
                    f"{test_url}/api/session", timeout=1
                )
                if resp.status == 200:
                    self.port = port
                    self.server_url = test_url
                    return True
            except (urllib.error.URLError, urllib.error.HTTPError,
                    OSError, ValueError):
                continue

        if not os.path.exists(self.bin_path):
            raise ServerStartError(
                f"opencode binary not found at {self.bin_path}"
            )

        try:
            self.server_process = subprocess.Popen(
                [self.bin_path, "serve",
                 "--port", str(self.port),
                 "--hostname", "127.0.0.1",
                 "--print-logs"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._server_pid = self.server_process.pid
        except FileNotFoundError:
            raise ServerStartError("opencode binary not found")
        except OSError as e:
            raise ServerStartError(f"Failed to start server: {e}")

        # Wait for server to be ready
        for _ in range(timeout):
            time.sleep(1)
            if self._is_server_running():
                # Extra wait for full initialization
                time.sleep(2)
                return True

        # Server didn't start — clean up
        self._kill_server()
        raise ServerStartError(
            f"Server did not start within {timeout}s. "
            f"Check logs for details."
        )

    def _is_server_running(self):
        """Check if the server HTTP endpoint is responding."""
        endpoints = ["/api/session", "/api/health", "/health", "/"]
        for ep in endpoints:
            try:
                resp = urllib.request.urlopen(
                    f"{self.server_url}{ep}", timeout=2)
                if resp.status < 500:
                    return True
            except (urllib.error.URLError, urllib.error.HTTPError,
                    OSError, ValueError):
                continue
        return False

    def _kill_server(self):
        """Kill the server process."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except Exception:
                self.server_process.kill()
            self.server_process = None
            self._server_pid = None

    # ── Message sending ────────────────────────────────────

    def send(self, message, timeout=300):
        """
        Send a message to OpenCode. Returns generator yielding
        (type, data) tuples as the response streams in.

        Types:
          "session"   → data = session_id (str)
          "reasoning" → data = thinking text (str)
          "text"      → data = response text chunk (str)
          "done"      → data = final accumulated text (str)
          "error"     → data = error message (str)

        This method is thread-safe — the subprocess runs in a thread
        while parts are polled from the main generator.
        """
        if not self._is_server_running():
            raise SendError("Server not running. Call ensure_server() first.")

        # Record the current latest session to detect which one is ours
        before_sid = self._get_latest_session_id()
        before_time = time.time()

        # Launch the run --attach subprocess
        try:
            proc = subprocess.Popen(
                [self.bin_path, "run",
                 "--attach", self.server_url,
                 message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise SendError(f"Failed to launch opencode run: {e}")

        # Poll for a new session + parts while subprocess runs
        session_id = None
        seen_parts = set()
        accumulated = []
        done_yielded = False
        poll_interval = 0.2
        deadline = time.time() + timeout

        try:
            while time.time() < deadline:
                # Check if subprocess is still alive
                proc_alive = proc.poll() is None

                # Detect session
                if not session_id:
                    sid = self._get_latest_session_id()
                    if sid and sid != before_sid:
                        session_id = sid
                        yield ("session", session_id)

                # Poll for parts
                if session_id:
                    parts = self._get_new_parts(session_id, seen_parts)
                    for ptype, pdata in parts:
                        seen_parts.add(pdata.get("_part_id"))
                        if ptype == "text":
                            text = pdata.get("text", "")
                            if text:
                                accumulated.append(text)
                                yield ("text", text)
                        elif ptype == "reasoning":
                            reason = pdata.get("text", "")
                            if reason:
                                yield ("reasoning", reason)
                        elif ptype == "step-finish":
                            if not done_yielded:
                                done_yielded = True
                                yield ("done", "".join(accumulated))

                # If subprocess finished and we have a session, we're done
                if not proc_alive and session_id:
                    # One more poll to catch any final parts
                    parts = self._get_new_parts(session_id, seen_parts)
                    for ptype, pdata in parts:
                        if ptype == "text":
                            text = pdata.get("text", "")
                            if text:
                                accumulated.append(text)
                                yield ("text", text)
                        elif ptype in ("step-finish",):
                            pass

                    if not done_yielded:
                        yield ("done", "".join(accumulated))
                    return

                # If subprocess finished but no session — wait a bit for it
                if not proc_alive and not session_id:
                    time.sleep(1)
                    sid = self._get_latest_session_id()
                    if sid and sid != before_sid:
                        session_id = sid
                        yield ("session", session_id)
                        continue
                    yield ("error", "No session created")
                    return

                time.sleep(poll_interval)

        except GeneratorExit:
            pass
        finally:
            # Ensure subprocess is cleaned up
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

    def send_sync(self, message, timeout=300):
        """
        Synchronous convenience method — sends a message and returns
        the full response text. Blocks until complete.
        """
        full_text = ""
        for ptype, data in self.send(message, timeout=timeout):
            if ptype == "text":
                full_text += data
            elif ptype == "error":
                raise SendError(data)
        return full_text

    # ── DB polling ────────────────────────────────────────

    def _get_latest_session_id(self):
        """Get the ID of the most recent session from the DB."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "SELECT id FROM session ORDER BY time_created DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
            return row[0] if row else None
        except (sqlite3.OperationalError, OSError) as e:
            return None

    def _get_new_parts(self, session_id, seen_ids):
        """
        Get new parts for a session that haven't been seen yet.
        Returns list of (type, data_dict) tuples.
        Only returns parts from assistant messages (not user echo).
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=1)
            cur = conn.execute(
                """SELECT p.id, p.data, json_extract(m.data, '$.role') as role
                   FROM part p
                   JOIN message m ON p.message_id = m.id
                   WHERE m.session_id = ?
                   ORDER BY p.time_created""",
                (session_id,),
            )
            results = []
            for part_id, data_json, role in cur.fetchall():
                if part_id not in seen_ids:
                    data = json.loads(data_json)
                    data["_part_id"] = part_id
                    ptype = data.get("type", "")
                    if ptype in ("text", "reasoning", "step-start",
                                 "step-finish", "error"):
                        # Skip user message echo — only show assistant parts
                        if ptype == "text" and role == "user":
                            continue
                        results.append((ptype, data))
            conn.close()
            return results
        except (sqlite3.OperationalError, OSError,
                json.JSONDecodeError) as e:
            return []

    # ── Cleanup ───────────────────────────────────────────

    def close(self):
        """Stop the server and clean up."""
        self._kill_server()


# ── Background polling thread ──────────────────────────────────────
class REPLPoller:
    """
    Background thread that polls for REPL responses and feeds
    them to a callback. Used for integrating with the TUI chat.

    Usage:
        poller = REPLPoller(repl)
        poller.start_send(message, on_part=lambda type, data: ...)
        # ... main loop continues ...
        poller.tick()  # Call periodically from main loop
    """

    def __init__(self, repl=None):
        self.repl = repl or OpenCodeREPL()
        self._thread = None
        self._running = False
        self._lock = threading.Lock()

        # Queue of (type, data) tuples from background thread
        self._queue = []

        # Current state
        self.status = "idle"  # idle, sending, done, error
        self.session_id = None
        self.accumulated_text = ""
        self.status_message = ""

    def ensure_server(self):
        """Ensure the REPL server is running."""
        return self.repl.ensure_server()

    def start_send(self, message, on_part=None):
        """
        Start sending a message in the background.
        Parts will be queued and available via tick().
        """
        self._queue = []
        self.status = "sending"
        self.session_id = None
        self.accumulated_text = ""
        self._on_part = on_part

        def _run():
            try:
                for ptype, data in self.repl.send(message):
                    with self._lock:
                        self._queue.append((ptype, data))
                    if ptype == "session":
                        self.session_id = data
                    elif ptype == "text":
                        self.accumulated_text += data
                    elif ptype == "done":
                        self.status = "done"
                    elif ptype == "error":
                        self.status = "error"
                        self.status_message = data
            except Exception as e:
                with self._lock:
                    self._queue.append(("error", str(e)))
                    self.status = "error"
                    self.status_message = str(e)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def tick(self):
        """
        Process queued parts. Call periodically from the main loop.
        Returns list of (type, data) tuples processed.
        """
        processed = []
        with self._lock:
            while self._queue:
                item = self._queue.pop(0)
                processed.append(item)
        for item in processed:
            if self._on_part:
                self._on_part(*item)
        return processed

    def is_active(self):
        return self.status == "sending"

    def close(self):
        self.repl.close()


# ── Syntax highlighting for code blocks ────────────────────────────
def highlight_code_blocks(text):
    """
    Highlight ```code blocks``` in text with ANSI colors.
    Returns list of (styled_text, is_code_block) segments.
    """
    import re
    pattern = r'(```(\w*)\n?)(.*?)```'
    segments = []
    last_end = 0

    for m in re.finditer(pattern, text, re.DOTALL):
        # Text before this code block
        if m.start() > last_end:
            segments.append((text[last_end:m.start()], False))

        lang = m.group(2).lower() or ""
        code = m.group(3)
        lang_color = CODE_LANG_COLORS.get(lang, S.TEAL)

        # Build code block header with language tag
        if lang:
            header = styled(f" ┌─ {lang} ", S.BOLD, lang_color, S.bg(235))
        else:
            header = styled(" ┌─ code ", S.BOLD, S.TEAL, S.bg(235))

        # Color each line of code
        code_lines = code.rstrip('\n').split('\n')
        colored_code = ""
        for cl in code_lines:
            colored_code += styled(f" │ {cl}", S.fg(252), S.bg(235)) + "\n"

        footer = styled(" └──", S.bg(235))
        segments.append((header + "\n" + colored_code + footer, True))
        last_end = m.end()

    # Remaining text after last code block
    if last_end < len(text):
        segments.append((text[last_end:], False))

    return segments if segments else [(text, False)]


# ── Tab completion for standalone REPL ─────────────────────────────
REPL_COMMANDS = [
    "/help", "/exit", "/quit", "/clear", "/cls",
    "/models", "/stats", "/context", "/session", "/note",
]

class REPLCompleter:
    """Tab completer for REPL commands."""
    def __init__(self):
        self.commands = REPL_COMMANDS

    def complete(self, text, state):
        if text.startswith("/"):
            candidates = [c for c in self.commands if c.startswith(text)]
            if state < len(candidates):
                return candidates[state]
        return None


def setup_readline():
    """Configure readline with history and tab completion."""
    import readline
    histfile = os.path.join(CONFIG_DIR, ".repl_history")
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)

    # Set up tab completion
    completer = REPLCompleter()
    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer.complete)

    def save_history():
        try:
            readline.write_history_file(histfile)
        except Exception:
            pass
    return save_history


# ── Standalone REPL UI ─────────────────────────────────────────────
def run_standalone_repl(port=None):
    """
    Run the REPL in standalone interactive mode.
    """
    repl = OpenCodeREPL(port=port)
    print(f"Starting OpenCode server on port {repl.port}...")
    try:
        repl.ensure_server()
    except ServerStartError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"✓ Server ready at {repl.server_url}")
    print(f"  Type your messages. Ctrl+D or /exit to quit.")
    print(f"  /help for commands.")
    print()

    save_history = setup_readline()

    try:
        while True:
            try:
                # Multi-line input: lines ending with \ continue on next line
                lines = []
                while True:
                    prompt = f"{S.BOLD}{S.ACCENT}oc{S.RESET} {S.fg(250)}>{S.RESET} " if not lines else f"{S.GRAY}...{S.RESET} "
                    try:
                        line = input(prompt)
                    except EOFError:
                        print()
                        break

                    if line.rstrip().endswith("\\"):
                        lines.append(line.rstrip()[:-1])
                        continue
                    lines.append(line)
                    break

                if not lines:
                    continue
                text = "\n".join(lines).strip()
                if not text:
                    continue

            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                if lines:
                    print()
                    lines = []
                    continue
                print()
                break

            # Commands
            if text == "/exit" or text == "/quit":
                break
            elif text == "/help":
                _show_help()
                continue
            elif text == "/clear" or text == "/cls":
                os.system("clear" if os.name == "posix" else "cls")
                continue
            elif text == "/models":
                _show_models(repl)
                continue
            elif text == "/stats":
                _show_repl_stats(repl)
                continue
            elif text == "/context":
                _show_repl_context()
                continue
            elif text.startswith("/"):
                print(f"  {styled('Unknown command:', S.RED)} {text}")
                print(f"  Type {styled('/help', S.TEAL)} for available commands")
                continue

            # Send message with timing
            start_time = time.time()
            print(f"  {styled('──', S.GRAY)} {styled('sending...', S.DIM)}")

            reasoning_text = ""
            response_text = ""
            in_reasoning = False

            for ptype, data in repl.send(text):
                if ptype == "session":
                    print(f"  {styled('session:', S.GRAY)} {data[:20]}")
                elif ptype == "reasoning":
                    if not in_reasoning:
                        print(f"  {styled('── thinking ──', S.ITALIC, S.GRAY)}")
                        in_reasoning = True
                    r_lines = data.split("\n")
                    for rl in r_lines[:3]:
                        if rl.strip():
                            print(f"  {styled(rl.strip()[:80], S.ITALIC, S.GRAY)}")
                    reasoning_text += data
                elif ptype == "text":
                    if in_reasoning:
                        print(f"  {styled('── response ──', S.ITALIC, S.GRAY)}")
                        in_reasoning = False
                    # Highlight code blocks in the response
                    segments = highlight_code_blocks(data)
                    for seg_text, is_code in segments:
                        sys.stdout.write(seg_text)
                        sys.stdout.flush()
                    response_text += data
                elif ptype == "done":
                    elapsed = time.time() - start_time
                    print()
                    print(f"  {styled('─' * 40, S.GRAY)}")
                    print(f"  {styled('✓', S.GREEN)} {styled(f'done', S.BOLD)} "
                          f"{styled(f'({len(response_text)} chars, {elapsed:.1f}s)', S.GRAY)}")

            # Save to context
            _add_repl_finding(text[:100], response_text[:500])
            print()

    except KeyboardInterrupt:
        print(f"\n  {styled('Goodbye!', S.GRAY)}")
    finally:
        save_history()
        repl.close()

    return 0


def _add_repl_finding(summary, detail):
    """Save REPL interaction to shared context."""
    import subprocess as _sp
    import json as _json
    helper = os.path.join(CONFIG_DIR, "shared", "helpers", "context.py")
    if os.path.exists(helper):
        finding = _json.dumps({
            "type": "repl_interaction",
            "summary": summary[:100],
            "detail": detail[:500],
            "severity": "info",
        })
        try:
            _sp.run([sys.executable, helper, "add-finding", "chat_user", finding],
                    timeout=5, capture_output=True)
        except Exception:
            pass


def _show_repl_stats(repl):
    """Show REPL usage stats."""
    import sqlite3
    try:
        conn = sqlite3.connect(repl.db_path)
        cur = conn.execute("SELECT COUNT(*) FROM session")
        count = cur.fetchone()[0]
        cur = conn.execute(
            "SELECT COUNT(*), MIN(time_created), MAX(time_created) FROM session"
        )
        row = cur.fetchone()
        conn.close()

        print(f"\n  {styled('REPL Statistics', S.BOLD, S.ACCENT)}")
        print(f"  {styled('─' * 40, S.GRAY)}")
        print(f"  {styled('Sessions:', S.BOLD)} {row[0] if row else 0}")
        if row and row[1]:
            print(f"  {styled('From:', S.BOLD)}     {row[1][:19]}")
            print(f"  {styled('To:', S.BOLD)}       {row[2][:19]}")
        print(f"  {styled('Port:', S.BOLD)}     {repl.port}")
        print(f"  {styled('Status:', S.BOLD)}   {'Running' if repl._is_server_running() else 'Stopped'}")
        print()
    except Exception as e:
        print(f"  {styled(f'Error: {e}', S.RED)}")


def _show_repl_context():
    """Show shared context summary within REPL."""
    import subprocess as _sp
    helper = os.path.join(CONFIG_DIR, "shared", "helpers", "context.py")
    if os.path.exists(helper):
        try:
            result = _sp.run([sys.executable, helper, "read-findings"],
                             capture_output=True, text=True, timeout=5)
            if result.stdout:
                print(f"\n  {styled('Shared Context', S.BOLD, S.ACCENT)}")
                print(result.stdout)
        except Exception:
            print(f"  {styled('Could not read context', S.RED)}")
    else:
        print(f"  {styled('Context helper not found', S.RED)}")


def _show_help():
    """Show REPL help."""
    print(f"""
  {styled('OpenCode REPL Commands', S.BOLD, S.ACCENT)}
  {styled('─' * 40, S.GRAY)}
  {styled('/help', S.TEAL):16}  Show this help
  {styled('/exit, /quit', S.TEAL):16}  Exit the REPL
  {styled('/clear, /cls', S.TEAL):16}  Clear the screen
  {styled('/models', S.TEAL):16}  List available models
  {styled('/stats', S.TEAL):16}  Show session statistics
  {styled('/context', S.TEAL):16}  Show shared context summary

  {styled('Keyboard Shortcuts', S.BOLD, S.ACCENT)}
  {styled('Tab', S.TEAL):16}  Command completion
  {styled('↑/↓', S.TEAL):16}  History navigation
  {styled('Ctrl+D', S.TEAL):16}  Exit
  {styled('Ctrl+C', S.TEAL):16}  Cancel input / interrupt

  {styled('Tips', S.BOLD, S.ACCENT)}
  - End a line with {styled('\\', S.TEAL)} to continue on the next line (multi-line)
  - Code blocks in responses are {styled('syntax highlighted', S.GREEN)}
  - The server stays running between messages (no cold start)
  - Use {styled('oc ask', S.TEAL)} for one-shot queries without the REPL
""")


def _show_models(repl):
    """Show available models."""
    try:
        resp = urllib.request.urlopen(
            f"{repl.server_url}/api/model", timeout=5
        )
        models = json.loads(resp.read().decode())
        for m in models:
            enabled = "✓" if m.get("enabled") else " "
            print(f"  [{enabled}] {m.get('id','?')}  {m.get('name','')}")
    except Exception as e:
        print(f"  Error fetching models: {e}")


# ── Entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenCode REPL")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="Server port (default: 4099)")
    parser.add_argument("--message", "-m", type=str,
                        help="Send a single message and exit")
    args = parser.parse_args()

    if args.message:
        # One-shot mode
        repl = OpenCodeREPL(port=args.port)
        try:
            repl.ensure_server()
            for ptype, data in repl.send(args.message):
                if ptype == "text":
                    sys.stdout.write(data)
                    sys.stdout.flush()
                elif ptype == "error":
                    print(f"\nError: {data}", file=sys.stderr)
                    sys.exit(1)
            print()
        except REPLError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            repl.close()
    else:
        sys.exit(run_standalone_repl(port=args.port))

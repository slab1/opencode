#!/usr/bin/env python3
"""
oc — OpenCode CLI
==================
A polished command-line interface for the OpenCode AI coding assistant.

Usage:
    oc ask <message>            One-shot query (streams response)
    oc chat                     Interactive REPL session
    oc session list             List recent sessions
    oc session show <id>        Show session details
    oc session resume           Resume last session
    oc context [subcommand]     Shared context inspection
    oc agent <name> <message>   Dispatch to specific agent
    oc models                   List available models
    oc server <action>          Server management (start/stop/status)
    oc stats                    View usage statistics
    oc search <keyword>         Search sessions
    oc note <text>              Quick session note
    oc cleanup [days]           Delete old sessions (default: 30 days)
    oc docs                     Show this documentation

Zero external dependencies — pure Python stdlib + ANSI codes.
"""

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────
CONFIG_DIR = os.path.expanduser("~/.config/opencode")
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)))
CONTEXT_FILE = os.path.join(CONFIG_DIR, "shared", "context.json")
CONTEXT_HELPER = os.path.join(CONFIG_DIR, "shared", "helpers", "context.py")
SESSIONS_OUTCOMES = os.path.join(CONFIG_DIR, "knowledge-graph", "outcomes", "sessions.json")
OPENCODE_DB = os.path.expanduser("/public/.local/share/opencode/opencode.db")
OPCODE_BIN = shutil.which("opencode") or "/usr/local/lib/node_modules/opencode-ai/bin/opencode.exe"
CHAT_HISTORY_FILE = os.path.join(CONFIG_DIR, "shared", "chat_history.json")
NOTES_FILE = os.path.join(CONFIG_DIR, "shared", "notes.json")

DEFAULT_PORT = 4099
COMMON_PORTS = [4096, 4097, 4098, 4099, 4100]

# Ensure scripts dir is on path for imports
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# ── ANSI helpers ───────────────────────────────────────────────────
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

    # Named colors
    ACCENT = fg(75)
    GREEN = fg(83)
    YELLOW = fg(221)
    RED = fg(196)
    ORANGE = fg(208)
    PURPLE = fg(141)
    TEAL = fg(43)
    PINK = fg(212)
    GRAY = fg(240)
    WHITE = fg(255)

    CHEVRON = "›"
    DOT = "●"
    CIRCLE = "○"
    CHECK = "✓"
    CROSS = "✗"
    STAR = "★"
    GEAR = "⚙"
    ARROW_R = "→"


def styled(text, *styles):
    return f"{''.join(styles)}{text}{S.RESET}"


def vis_len(text):
    """Visible length excluding ANSI codes."""
    import re
    return len(re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text))


def print_header(title):
    """Print a section header."""
    cols = shutil.get_terminal_size((80, 24)).columns
    print()
    print(f"  {styled(title, S.BOLD, S.ACCENT)}")
    print(f"  {styled('─' * min(cols - 4, 60), S.GRAY)}")


def print_status(label, value, color=S.WHITE):
    """Print a labeled status line."""
    print(f"  {styled(label + ':', S.BOLD)} {styled(value, color)}")


def print_error(msg):
    print(f"  {styled('✗', S.RED)} {styled(msg, S.RED)}", file=sys.stderr)


def print_success(msg):
    print(f"  {styled('✓', S.GREEN)} {msg}")


def time_ago(ts):
    """Convert ISO timestamp to relative time string."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        diff = datetime.now().astimezone() - dt
        s = int(diff.total_seconds())
        if s < 60: return f"{s}s ago"
        elif s < 3600: return f"{s // 60}m ago"
        elif s < 86400: return f"{s // 3600}h ago"
        else: return f"{s // 86400}d ago"
    except (ValueError, TypeError):
        return "—"


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default or {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_cmd(cmd, timeout=15):
    """Run a command and return (stdout, stderr, returncode)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except FileNotFoundError:
        return "", "command not found", -1
    except subprocess.TimeoutExpired:
        return "", "timed out", -1


# ═══════════════════════════════════════════════════════════════════
#  REPL / Server Engine
# ═══════════════════════════════════════════════════════════════════

class OpenCodeEngine:
    """
    Lightweight engine wrapping opencode server interactions.
    Manages server lifecycle, session creation, and response streaming.
    """

    def __init__(self, port=None, bin_path=None):
        self.port = port or DEFAULT_PORT
        self.server_url = f"http://127.0.0.1:{self.port}"
        self.bin_path = bin_path or OPCODE_BIN
        self.db_path = OPENCODE_DB
        self._server_proc = None

    # ── Server management ──────────────────────────────────────

    def ensure_server(self, timeout=30):
        """Start opencode serve if not already running."""
        if self._is_running():
            return True
        # Check other common ports
        for port in COMMON_PORTS:
            if port == self.port: continue
            try:
                url = f"http://127.0.0.1:{port}/api/session"
                resp = urllib.request.urlopen(url, timeout=1)
                if resp.status == 200:
                    self.port = port
                    self.server_url = f"http://127.0.0.1:{port}"
                    return True
            except (urllib.error.URLError, OSError):
                continue

        if not os.path.exists(self.bin_path):
            raise RuntimeError(f"opencode binary not found: {self.bin_path}")

        try:
            self._server_proc = subprocess.Popen(
                [self.bin_path, "serve", "--port", str(self.port),
                 "--hostname", "127.0.0.1", "--print-logs"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            raise RuntimeError(f"Failed to start server: {e}")

        for _ in range(timeout):
            time.sleep(1)
            if self._is_running():
                time.sleep(2)  # Extra init time
                return True

        self._kill()
        raise RuntimeError(f"Server did not start within {timeout}s")

    def _is_running(self):
        try:
            resp = urllib.request.urlopen(
                f"{self.server_url}/api/session", timeout=2)
            return resp.status == 200
        except Exception:
            return False

    def server_status(self):
        """Return dict with server status info."""
        running = self._is_running()
        result = {"running": running, "port": self.port, "url": self.server_url}
        if running:
            try:
                resp = urllib.request.urlopen(
                    f"{self.server_url}/api/model", timeout=3)
                models = json.loads(resp.read().decode())
                result["models"] = len(models)
            except Exception:
                result["models"] = "?"
            # Get session count
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.execute("SELECT COUNT(*) FROM session")
                result["session_count"] = cur.fetchone()[0]
                conn.close()
            except Exception:
                result["session_count"] = "?"
        return result

    def _kill(self):
        if self._server_proc:
            try:
                self._server_proc.terminate()
                self._server_proc.wait(timeout=5)
            except Exception:
                self._server_proc.kill()
            self._server_proc = None

    def stop_server(self, force=False):
        """Stop the server. If force, use SIGKILL."""
        if self._server_proc:
            if force:
                self._server_proc.kill()
            else:
                self._server_proc.terminate()
                try:
                    self._server_proc.wait(timeout=5)
                except Exception:
                    self._server_proc.kill()
            self._server_proc = None
            return True
        # Try finding and killing via pkill
        run_cmd(["pkill", "-f", f"opencode.*serve.*{self.port}"])
        return True

    # ── Message sending ────────────────────────────────────────

    def send(self, message, timeout=300):
        """
        Send a message and stream response parts.
        Yields (type, data) tuples:
          "session"   -> session_id
          "reasoning" -> thinking text
          "text"      -> response text chunk
          "done"      -> final accumulated text
          "error"     -> error message
        """
        if not self._is_running():
            raise RuntimeError("Server not running. Call ensure_server() first.")

        before_sid = self._get_latest_session_id()

        try:
            proc = subprocess.Popen(
                [self.bin_path, "run", "--attach", self.server_url, message],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch opencode: {e}")

        session_id = None
        seen_parts = set()
        accumulated = []
        done_yielded = False
        deadline = time.time() + timeout

        try:
            while time.time() < deadline:
                alive = proc.poll() is None

                if not session_id:
                    sid = self._get_latest_session_id()
                    if sid and sid != before_sid:
                        session_id = sid
                        yield ("session", session_id)

                if session_id:
                    for ptype, pdata in self._poll_parts(session_id, seen_parts):
                        seen_parts.add(pdata.get("_part_id"))
                        if ptype == "text":
                            text = pdata.get("text", "")
                            if text:
                                accumulated.append(text)
                                yield ("text", text)
                        elif ptype == "reasoning":
                            r = pdata.get("text", "")
                            if r:
                                yield ("reasoning", r)
                        elif ptype == "step-finish" and not done_yielded:
                            done_yielded = True
                            yield ("done", "".join(accumulated))

                if not alive:
                    if session_id:
                        # Final poll
                        for ptype, pdata in self._poll_parts(session_id, seen_parts):
                            if ptype == "text":
                                text = pdata.get("text", "")
                                if text:
                                    accumulated.append(text)
                                    yield ("text", text)
                        if not done_yielded:
                            yield ("done", "".join(accumulated))
                    else:
                        time.sleep(1)
                        sid = self._get_latest_session_id()
                        if sid and sid != before_sid:
                            yield ("session", sid)
                            continue
                        yield ("error", "No session created")
                    return

                time.sleep(0.2)
        except GeneratorExit:
            pass
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

    def send_sync(self, message, timeout=300):
        """Synchronous convenience: send message, return full response."""
        full = ""
        for ptype, data in self.send(message, timeout=timeout):
            if ptype == "text":
                full += data
            elif ptype == "error":
                raise RuntimeError(data)
        return full

    # ── DB polling ─────────────────────────────────────────────

    def _get_latest_session_id(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "SELECT id FROM session ORDER BY time_created DESC LIMIT 1")
            row = cur.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def _poll_parts(self, session_id, seen_ids):
        """Get new assistant response parts not seen yet."""
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
            for pid, data_json, role in cur.fetchall():
                if pid in seen_ids:
                    continue
                data = json.loads(data_json)
                data["_part_id"] = pid
                ptype = data.get("type", "")
                if ptype in ("text", "reasoning", "step-finish", "error"):
                    if ptype == "text" and role == "user":
                        continue
                    results.append((ptype, data))
            conn.close()
            return results
        except Exception:
            return []

    # ── Session queries ────────────────────────────────────────

    def list_sessions(self, limit=20):
        """List recent sessions from the DB."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                """SELECT id, time_created, json_extract(data, '$.model') as model
                   FROM session ORDER BY time_created DESC LIMIT ?""",
                (limit,),
            )
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as e:
            return []

    def get_session(self, session_id):
        """Get full session details."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "SELECT id, time_created, data FROM session WHERE id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.close()
                return None
            session = {"id": row[0], "time_created": row[1], "data": json.loads(row[2])}

            # Get messages
            cur = conn.execute(
                """SELECT m.id, m.time_created, m.data,
                          json_extract(m.data, '$.role') as role
                   FROM message m
                   WHERE m.session_id = ?
                   ORDER BY m.time_created""",
                (session_id,),
            )
            messages = []
            for m in cur.fetchall():
                msgs = {"id": m[0], "time_created": m[1], "data": json.loads(m[2]), "role": m[3]}
                # Get parts for this message
                cur2 = conn.execute(
                    "SELECT id, time_created, data FROM part WHERE message_id = ? ORDER BY time_created",
                    (m[0],),
                )
                parts = []
                for p in cur2.fetchall():
                    parts.append({"id": p[0], "time_created": p[1], "data": json.loads(p[2])})
                msgs["parts"] = parts
                messages.append(msgs)
            session["messages"] = messages
            conn.close()
            return session
        except Exception as e:
            return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._kill()


# ═══════════════════════════════════════════════════════════════════
#  CLI Subcommand Handlers
# ═══════════════════════════════════════════════════════════════════

def cmd_ask(args):
    """One-shot query — streams response with syntax highlights."""
    message = " ".join(args.message)
    engine = OpenCodeEngine()
    try:
        engine.ensure_server()
    except RuntimeError as e:
        print_error(str(e))
        return 1

    print(f"\n  {styled('oc ask', S.BOLD, S.ACCENT)} {styled(message, S.ITALIC, S.GRAY)}")
    print(f"  {styled('─' * 40, S.GRAY)}")

    reasoning_text = ""
    response_text = ""
    in_reasoning = False

    try:
        for ptype, data in engine.send(message):
            if ptype == "session":
                pass  # Silent in ask mode
            elif ptype == "reasoning":
                if not in_reasoning:
                    print(f"\n  {styled('thinking...', S.ITALIC, S.GRAY)}")
                    in_reasoning = True
                # Show reasoning compactly
                for line in data.split("\n"):
                    line = line.strip()
                    if line:
                        print(f"  {styled(line[:100], S.DIM, S.GRAY)}")
                reasoning_text += data
            elif ptype == "text":
                if in_reasoning:
                    in_reasoning = False
                sys.stdout.write(data)
                sys.stdout.flush()
                response_text += data
            elif ptype == "done":
                print()
                print(f"  {styled('─' * 40, S.GRAY)}")
                print(f"  {styled(f'✓ done ({len(response_text)} chars)', S.GREEN)}")
    except RuntimeError as e:
        print_error(str(e))
        return 1

    # Save to context
    _add_context_finding("chat_user", {
        "type": "chat_input", "summary": message[:100],
        "detail": message, "severity": "info"
    })
    _add_context_finding("general", {
        "type": "response", "summary": f"Response to: {message[:50]}...",
        "detail": response_text[:500], "severity": "info"
    })
    _add_session_outcome({
        "task": message[:80],
        "pattern_matched": "cli-ask",
        "agents_used": ["general"],
        "outcome": "completed",
        "response_length": len(response_text),
    })

    return 0


def cmd_chat(args):
    """Interactive REPL session with syntax highlighting."""
    from oc_repl import run_standalone_repl
    return run_standalone_repl(port=args.port)


def cmd_session_list(args):
    """List recent sessions."""
    engine = OpenCodeEngine()
    sessions = engine.list_sessions(limit=args.limit)
    if not sessions:
        print(f"\n  {styled('No sessions found.', S.GRAY)}")
        return 0

    print()
    print(f"  {styled('Recent Sessions', S.BOLD, S.ACCENT)}")
    print(f"  {styled('─' * 60, S.GRAY)}")
    for sid, ts, model in sessions:
        age = time_ago(ts)
        model_str = model or "—"
        sid_short = sid[:16] if sid else "—"
        print(f"  {styled(sid_short, S.TEAL):18} {styled(age, S.GRAY):10} {styled(model_str, S.DIM)}")
    print(f"  {styled('─' * 60, S.GRAY)}")
    print(f"  {len(sessions)} sessions")
    return 0


def cmd_session_show(args):
    """Show session details with messages."""
    engine = OpenCodeEngine()
    session = engine.get_session(args.id)
    if not session:
        print_error(f"Session not found: {args.id}")
        return 1

    print()
    print(f"  {styled('Session', S.BOLD, S.ACCENT)}: {session['id']}")
    print(f"  {styled('Time', S.BOLD)}: {session['time_created']}")
    model = session['data'].get('model', '—')
    print(f"  {styled('Model', S.BOLD)}: {model}")
    print(f"  {styled('Messages', S.BOLD)}: {len(session.get('messages', []))}")
    print()

    for msg in session.get('messages', []):
        role = msg.get('role', '?')
        role_color = S.ACCENT if role == 'assistant' else (S.GREEN if role == 'user' else S.GRAY)
        role_label = styled(f"[{role}]", S.BOLD, role_color)
        print(f"  {role_label}")

        for part in msg.get('parts', []):
            part_data = part.get('data', {})
            ptype = part_data.get('type', '')
            text = part_data.get('text', '')
            if text:
                # Truncate long text for display
                if len(text) > 500:
                    text = text[:500] + f"\n  {styled('[truncated...]', S.DIM, S.GRAY)}"
                print(f"    {text}")
        print()

    return 0


def cmd_session_resume(args):
    """Resume the last session."""
    engine = OpenCodeEngine()
    sessions = engine.list_sessions(limit=1)
    if not sessions:
        print_error("No sessions to resume")
        return 1

    sid = sessions[0][0]
    print(f"\n  Resuming session {styled(sid[:16], S.TEAL)}...")
    out, err, rc = run_cmd(["ocr"])
    if rc != 0:
        print_error(f"Resume failed: {err}")
        return 1
    print_success("Session resumed via opencode")
    return 0


def cmd_context(args):
    """Shared context inspection."""
    # Import context helper
    if not os.path.exists(CONTEXT_HELPER):
        print_error(f"Context helper not found at {CONTEXT_HELPER}")
        return 1

    subcmd = args.context_command or "summary"
    cmd = [CONTEXT_HELPER]

    if subcmd == "summary":
        cmd += ["read-findings"]
    elif subcmd == "findings":
        cmd += ["read-findings"]
        if args.agent:
            cmd += [args.agent]
    elif subcmd == "decisions":
        # Read full context and extract decisions
        ctx = load_json(CONTEXT_FILE, {"decisions": {}})
        decisions = ctx.get("decisions", {})
        print()
        for cat, items in decisions.items():
            if items:
                print(f"  {styled(f'=== {cat} ===', S.BOLD, S.ACCENT)}")
                for d in items:
                    print(f"    {d.get('summary', '')[:100]}")
                print()
        return 0
    elif subcmd == "artifacts":
        ctx = load_json(CONTEXT_FILE, {"artifacts": {}})
        artifacts = ctx.get("artifacts", {})
        print()
        for cat, items in artifacts.items():
            if items:
                print(f"  {styled(f'=== {cat} ({len(items)} items) ===', S.BOLD, S.ACCENT)}")
                for item in items[-10:]:
                    print(f"    {item[:100]}")
                print()
        return 0
    elif subcmd == "workflow":
        ctx = load_json(CONTEXT_FILE, {"workflow_trace": []})
        trace = ctx.get("workflow_trace", [])
        print()
        if trace:
            print(f"  {styled(f'Workflow Trace ({len(trace)} steps)', S.BOLD, S.ACCENT)}")
            print(f"  {styled('─' * 50, S.GRAY)}")
            for i, step in enumerate(trace, 1):
                agent = step.get("agent", "?")
                status = step.get("status", "?")
                summary = step.get("summary", "")[:70]
                status_color = S.GREEN if status == "completed" else (S.YELLOW if status == "running" else S.RED)
                print(f"  {i:2}. [{styled(status, status_color):10}] {styled(agent, S.TEAL):12} {summary}")
        else:
            print(f"  {styled('No workflow trace.', S.GRAY)}")
        return 0
    elif subcmd == "full":
        # Show full context JSON
        ctx = load_json(CONTEXT_FILE, {})
        print(json.dumps(ctx, indent=2))
        return 0

    # Default: use context.py helper
    out, err, rc = run_cmd([sys.executable] + cmd, timeout=10)
    if rc != 0:
        print_error(err or "Failed to read context")
        return 1
    print(out)
    return 0


def cmd_agent(args):
    """Dispatch a message to a specific agent via opencode CLI."""
    name = args.name
    message = " ".join(args.message)

    valid_agents = [
        "build", "plan", "architect", "debug", "docs", "explore",
        "general", "refactor", "review", "security", "test",
        "video-creator", "web-browser", "display-agent"
    ]

    if name not in valid_agents:
        print_error(f"Unknown agent '{name}'. Valid agents: {', '.join(valid_agents)}")
        return 1

    print(f"\n  Dispatching to {styled(name, S.BOLD, S.ACCENT)}...")
    print(f"  Message: {styled(message, S.ITALIC, S.GRAY)}")
    print(f"  {styled('─' * 40, S.GRAY)}")

    cmd = [OPCODE_BIN, "--agent", name, "--message", message]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Stream output
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()

    proc.wait()
    if proc.returncode != 0:
        stderr = proc.stderr.read()
        if stderr:
            print_error(stderr[:500])
        return 1

    return 0


def cmd_models(args):
    """List available models from the server."""
    engine = OpenCodeEngine()
    try:
        engine.ensure_server()
    except RuntimeError as e:
        print_error(str(e))
        return 1

    try:
        resp = urllib.request.urlopen(f"{engine.server_url}/api/model", timeout=5)
        models = json.loads(resp.read().decode())
    except Exception as e:
        print_error(f"Failed to fetch models: {e}")
        return 1

    print()
    print(f"  {styled('Available Models', S.BOLD, S.ACCENT)}")
    print(f"  {styled('─' * 50, S.GRAY)}")
    for m in models:
        enabled = styled("✓", S.GREEN) if m.get("enabled") else styled(" ", S.GRAY)
        mid = m.get("id", "?")
        name = m.get("name", "")
        print(f"  [{enabled}] {styled(mid, S.TEAL):30} {styled(name, S.DIM)}")
    print(f"  {styled('─' * 50, S.GRAY)}")
    print(f"  {len(models)} models")
    return 0


def cmd_server(args):
    """Server management: start, stop, status."""
    engine = OpenCodeEngine()
    action = args.server_command or "status"

    if action == "status":
        status = engine.server_status()
        print()
        print(f"  {styled('OpenCode Server Status', S.BOLD, S.ACCENT)}")
        print(f"  {styled('─' * 40, S.GRAY)}")
        if status["running"]:
            print_status("Status", "Running", S.GREEN)
            print_status("Port", status["port"])
            print_status("Models", status.get("models", "?"))
            print_status("Sessions", status.get("session_count", "?"))
        else:
            print_status("Status", "Stopped", S.RED)
            print(f"\n  Start with: {styled('oc server start', S.BOLD, S.TEAL)}")

    elif action == "start":
        print(f"\n  Starting OpenCode server on port {engine.port}...")
        try:
            engine.ensure_server(timeout=args.timeout or 30)
            print_success(f"Server ready at {engine.server_url}")
        except RuntimeError as e:
            print_error(str(e))
            return 1

    elif action == "stop":
        print(f"\n  Stopping server...")
        if engine.stop_server():
            print_success("Server stopped")
        else:
            print_error("Failed to stop server")
            return 1

    return 0


def cmd_stats(args):
    """Show usage statistics."""
    engine = OpenCodeEngine()

    # Get session count from DB
    sessions = []
    try:
        conn = sqlite3.connect(engine.db_path)
        cur = conn.execute(
            "SELECT id, time_created, json_extract(data, '$.model') as model "
            "FROM session ORDER BY time_created DESC"
        )
        sessions = cur.fetchall()
        conn.close()
    except Exception:
        pass

    # Get context stats
    ctx = load_json(CONTEXT_FILE, {})
    findings = ctx.get("findings", {})
    finding_counts = {a: len(fs) for a, fs in findings.items() if fs}

    # Get outcome stats
    outcomes = load_json(SESSIONS_OUTCOMES, {"sessions": [], "aggregated_insights": {}})

    print()
    print(f"  {styled('OpenCode Statistics', S.BOLD, S.ACCENT)}")
    print(f"  {styled('─' * 50, S.GRAY)}")

    # Server
    status = engine.server_status()
    print_status("Server", "Running" if status["running"] else "Stopped",
                 S.GREEN if status["running"] else S.RED)

    # Sessions
    print_status("Total Sessions", len(sessions))
    if sessions:
        first = time_ago(sessions[-1][1])  # Oldest
        last = time_ago(sessions[0][1])    # Newest
        print_status("Earliest", first)
        print_status("Latest", last)

    # Findings
    total_findings = sum(finding_counts.values())
    print_status("Agent Findings", total_findings)
    if finding_counts:
        for agent, count in sorted(finding_counts.items()):
            print(f"    {styled(f'{agent}:', S.TEAL):16} {count}")

    # Models used
    if sessions:
        models_used = {}
        for _, _, model in sessions:
            m = model or "unknown"
            models_used[m] = models_used.get(m, 0) + 1
        print()
        print(f"  {styled('Models Used', S.BOLD, S.ACCENT)}")
        for m, c in sorted(models_used.items(), key=lambda x: -x[1]):
            print(f"    {styled(m, S.TEAL):30} {c} sessions")

    # Outcomes
    insights = outcomes.get("aggregated_insights", {})
    if insights.get("total_sessions", 0) > 0:
        print()
        print(f"  {styled('Persisted Outcomes', S.BOLD, S.ACCENT)}")
        print_status("Completed Sessions", insights.get("total_sessions", 0))
        print_status("Total Iterations", insights.get("total_iterations", 0))
        print_status("Gaps Found", insights.get("total_gaps_found", 0))

    print()
    return 0


def cmd_search(args):
    """Search sessions by keyword."""
    keyword = args.keyword
    engine = OpenCodeEngine()

    try:
        conn = sqlite3.connect(engine.db_path)
        cur = conn.execute(
            """SELECT DISTINCT s.id, s.time_created
               FROM session s
               JOIN message m ON m.session_id = s.id
               JOIN part p ON p.message_id = m.id
               WHERE p.data LIKE ?
               ORDER BY s.time_created DESC
               LIMIT 30""",
            (f"%{keyword}%",),
        )
        results = cur.fetchall()
        conn.close()
    except Exception as e:
        print_error(f"Search failed: {e}")
        return 1

    if not results:
        print(f"\n  {styled('No results for:', S.GRAY)} {keyword}")
        return 0

    print()
    print(f"  {styled(f'Search results for:', S.BOLD, S.ACCENT)} {styled(keyword, S.ITALIC)}")
    print(f"  {styled('─' * 50, S.GRAY)}")
    for sid, ts in results:
        age = time_ago(ts)
        print(f"  {styled(sid[:20], S.TEAL):22} {styled(age, S.GRAY)}")
    print(f"  {styled('─' * 50, S.GRAY)}")
    print(f"  {len(results)} results")
    return 0


def cmd_note(args):
    """Quick persistent note."""
    text = " ".join(args.text)
    notes = load_json(NOTES_FILE, {"notes": []})
    note = {
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    notes["notes"].append(note)
    save_json(NOTES_FILE, notes)
    print_success(f"Note saved (total: {len(notes['notes'])})")

    # Also show recent notes
    recent = notes["notes"][-5:]
    if len(recent) > 1:
        print()
        print(f"  {styled('Recent Notes', S.BOLD, S.ACCENT)}")
        for n in reversed(recent[:-1]):
            age = time_ago(n["timestamp"])
            print(f"    {styled(n['text'][:80], S.GRAY)} {styled(f'({age})', S.DIM)}")
    return 0


def cmd_cleanup(args):
    """Delete old sessions."""
    days = args.days
    dry_run = args.dry_run

    engine = OpenCodeEngine()
    if not os.path.exists(engine.db_path):
        print_error("No session database found")
        return 1

    cutoff = time.time() - (days * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    try:
        conn = sqlite3.connect(engine.db_path)
        # Count old sessions
        cur = conn.execute(
            "SELECT COUNT(*) FROM session WHERE time_created < ?",
            (cutoff_iso,),
        )
        count = cur.fetchone()[0]

        if count == 0:
            print(f"\n  {styled('No sessions older than', S.GRAY)} {days} days.")
            conn.close()
            return 0

        print(f"\n  {styled(f'{count} sessions older than {days} days', S.YELLOW)}")
        if dry_run:
            print(f"  {styled('Dry run — no changes made.', S.GRAY)}")
            # Show what would be deleted
            cur = conn.execute(
                "SELECT id, time_created FROM session WHERE time_created < ? ORDER BY time_created LIMIT 10",
                (cutoff_iso,),
            )
            for sid, ts in cur.fetchall():
                print(f"    {styled(sid[:20], S.TEAL)} {ts}")
            if count > 10:
                print(f"    ... and {count - 10} more")
        else:
            confirm = input(f"  Delete {count} sessions? [y/N] ")
            if confirm.lower() == "y":
                # Delete parts first
                conn.execute(
                    "DELETE FROM part WHERE message_id IN "
                    "(SELECT id FROM message WHERE session_id IN "
                    "(SELECT id FROM session WHERE time_created < ?))",
                    (cutoff_iso,),
                )
                conn.execute(
                    "DELETE FROM message WHERE session_id IN "
                    "(SELECT id FROM session WHERE time_created < ?)",
                    (cutoff_iso,),
                )
                conn.execute(
                    "DELETE FROM session WHERE time_created < ?",
                    (cutoff_iso,),
                )
                conn.commit()
                print_success(f"Deleted {count} sessions")
            else:
                print("  Cancelled.")
        conn.close()
    except Exception as e:
        print_error(f"Cleanup failed: {e}")
        return 1

    return 0


def cmd_docs(args):
    """Show detailed documentation."""
    print(__doc__)
    return 0


# ── Context helpers ────────────────────────────────────────────────

def _add_context_finding(agent, finding):
    """Add a finding to the shared context."""
    if not os.path.exists(CONTEXT_HELPER):
        return
    finding_json = json.dumps(finding)
    run_cmd([sys.executable, CONTEXT_HELPER, "add-finding", agent, finding_json])


def _add_session_outcome(outcome_data):
    """Record a session outcome in the knowledge graph."""
    outcomes = load_json(SESSIONS_OUTCOMES, {"sessions": []})
    outcome = {
        "id": f"session-{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **outcome_data,
    }
    outcomes.setdefault("sessions", []).append(outcome)
    outcomes.setdefault("aggregated_insights", {})
    ai = outcomes["aggregated_insights"]
    ai["total_sessions"] = ai.get("total_sessions", 0) + 1
    ai["total_iterations"] = ai.get("total_iterations", 0) + outcome_data.get("iterations", 0)
    ai["total_gaps_found"] = ai.get("total_gaps_found", 0) + outcome_data.get("gaps_found", 0)

    # Track patterns
    pattern = outcome_data.get("pattern_matched")
    if pattern:
        ai.setdefault("patterns_used", {})
        ai["patterns_used"][pattern] = ai["patterns_used"].get(pattern, 0) + 1

    # Track agents
    for agent in outcome_data.get("agents_used", []):
        ai.setdefault("agents_used", {})
        ai["agents_used"][agent] = ai["agents_used"].get(agent, 0) + 1

    save_json(SESSIONS_OUTCOMES, outcomes)


# ═══════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════

def build_parser():
    parser = argparse.ArgumentParser(
        prog="oc",
        description="OpenCode CLI — AI coding assistant interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  oc ask "fix the login bug"
  oc chat
  oc session list
  oc session show ses_abc123
  oc agent debug "investigate memory leak"
  oc server status
  oc search "authentication"
  oc stats
  oc cleanup 30 --dry-run
  oc note "Remember to update the README"
        """,
    )
    parser.add_argument("--version", "-v", action="store_true", help="Show version")

    subparsers = parser.add_subparsers(dest="command")

    # ask
    p = subparsers.add_parser("ask", help="One-shot query with streaming response")
    p.add_argument("message", nargs="+", help="Message to send")

    # chat
    p = subparsers.add_parser("chat", help="Interactive REPL session")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (default: 4099)")

    # session
    p = subparsers.add_parser("session", help="Session management")
    sp = p.add_subparsers(dest="session_command")
    sp_list = sp.add_parser("list", help="List recent sessions")
    sp_list.add_argument("--limit", "-l", type=int, default=20, help="Max results")
    sp_show = sp.add_parser("show", help="Show full session details")
    sp_show.add_argument("id", help="Session ID")
    sp.add_parser("resume", help="Resume the last session")

    # context
    p = subparsers.add_parser("context", help="Shared context inspection")
    sp = p.add_subparsers(dest="context_command")
    sp.add_parser("summary", help="Show human-readable context summary")
    sp_find = sp.add_parser("findings", help="Show agent findings")
    sp_find.add_argument("agent", nargs="?", help="Filter by agent name")
    sp.add_parser("decisions", help="Show architecture/design decisions")
    sp.add_parser("artifacts", help="Show files created/modified")
    sp.add_parser("workflow", help="Show current workflow trace")
    sp.add_parser("full", help="Show raw JSON context")

    # agent
    p = subparsers.add_parser("agent", help="Dispatch task to a specific agent")
    p.add_argument("name", help="Agent name (build, debug, security, test, etc.)")
    p.add_argument("message", nargs="+", help="Task description")

    # models
    subparsers.add_parser("models", help="List available models from server")

    # server
    p = subparsers.add_parser("server", help="Server management")
    sp = p.add_subparsers(dest="server_command")
    sp_start = sp.add_parser("start", help="Start the OpenCode server")
    sp_start.add_argument("--timeout", type=int, default=30, help="Start timeout (seconds)")
    sp.add_parser("stop", help="Stop the server")
    sp.add_parser("status", help="Check server status")

    # stats
    subparsers.add_parser("stats", help="Show usage statistics and analytics")

    # search
    p = subparsers.add_parser("search", help="Search session content by keyword")
    p.add_argument("keyword", help="Search keyword or phrase")

    # note
    p = subparsers.add_parser("note", help="Quick persistent note")
    p.add_argument("text", nargs="+", help="Note text")

    # cleanup
    p = subparsers.add_parser("cleanup", help="Delete old sessions (default: 30 days)")
    p.add_argument("days", nargs="?", type=int, default=30, help="Age in days (default: 30)")
    p.add_argument("--dry-run", "-n", action="store_true", help="Preview without deleting")

    # docs
    subparsers.add_parser("docs", help="Show full documentation")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        v, _, rc = run_cmd([OPCODE_BIN, "--version"])
        print(f"oc CLI (opencode {v or '?'})")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    # Route to handler
    handlers = {
        "ask": cmd_ask,
        "chat": cmd_chat,
        "session": cmd_session_router,
        "context": cmd_context,
        "agent": cmd_agent,
        "models": cmd_models,
        "server": cmd_server,
        "stats": cmd_stats,
        "search": cmd_search,
        "note": cmd_note,
        "cleanup": cmd_cleanup,
        "docs": cmd_docs,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


def cmd_session_router(args):
    """Route session subcommands."""
    sub = args.session_command
    if sub == "list":
        return cmd_session_list(args)
    elif sub == "show":
        return cmd_session_show(args)
    elif sub == "resume":
        return cmd_session_resume(args)
    else:
        print("Usage: oc session {list|show|resume}")
        print("  list          List recent sessions")
        print("  show <id>     Show session details")
        print("  resume        Resume last session")
        return 1


if __name__ == "__main__":
    sys.exit(main())

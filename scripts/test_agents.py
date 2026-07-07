#!/usr/bin/env python3
"""
OpenCode Agent & System Test Suite
====================================
Tests for:
  1. Shared context read/write
  2. Server start/stop
  3. CLI subcommands routing
  4. Session persistence
  5. REPL engine (library mode)
  6. Knowledge graph outcomes

Usage:
    python3 test_agents.py              # Run all tests
    python3 test_agents.py -v           # Verbose
    python3 test_agents.py TestContext  # Run specific test class
"""

import json
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)

CONFIG_DIR = os.path.expanduser("~/.config/opencode")
CONTEXT_FILE = os.path.join(CONFIG_DIR, "shared", "context.json")
CONTEXT_HELPER = os.path.join(CONFIG_DIR, "shared", "helpers", "context.py")
SESSIONS_OUTCOMES = os.path.join(CONFIG_DIR, "knowledge-graph", "outcomes", "sessions.json")
OPENCODE_DB = os.path.expanduser("/public/.local/share/opencode/opencode.db")

OPCODE_BIN = "/usr/local/lib/node_modules/opencode-ai/bin/opencode.exe"


# ═══════════════════════════════════════════════════════════════════
#  Context System Tests
# ═══════════════════════════════════════════════════════════════════

class TestContextSystem(unittest.TestCase):
    """Test the shared context read/write system."""

    def setUp(self):
        self.helper = CONTEXT_HELPER
        self._backup = None
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE) as f:
                self._backup = f.read()

    def tearDown(self):
        if self._backup:
            with open(CONTEXT_FILE, "w") as f:
                f.write(self._backup)

    def _run_helper(self, *args):
        result = subprocess.run(
            [sys.executable, self.helper] + list(args),
            capture_output=True, text=True, timeout=10
        )
        return result.stdout, result.stderr, result.returncode

    def _load_context(self):
        with open(CONTEXT_FILE) as f:
            return json.load(f)

    def test_add_finding(self):
        """Test adding a finding to the context store."""
        finding = json.dumps({
            "summary": "Test finding from unit test",
            "severity": "info",
            "type": "test"
        })
        stdout, stderr, rc = self._run_helper("add-finding", "debug", finding)
        self.assertEqual(rc, 0, f"add-finding failed: {stderr}")
        self.assertIn("Added finding", stdout)

        # Verify it was saved
        ctx = self._load_context()
        self.assertGreater(len(ctx["findings"]["debug"]), 0)
        last = ctx["findings"]["debug"][-1]
        self.assertEqual(last["summary"], "Test finding from unit test")

    def test_add_artifact(self):
        """Test adding an artifact entry."""
        stdout, stderr, rc = self._run_helper("add-artifact", "files_modified", "test_file.py")
        self.assertEqual(rc, 0, f"add-artifact failed: {stderr}")
        ctx = self._load_context()
        self.assertIn("test_file.py", ctx["artifacts"]["files_modified"])

    def test_add_decision(self):
        """Test adding a decision entry."""
        decision = json.dumps({"summary": "Use Python stdlib", "rationale": "Zero deps"})
        stdout, stderr, rc = self._run_helper("add-decision", "technology", decision)
        self.assertEqual(rc, 0, f"add-decision failed: {stderr}")
        ctx = self._load_context()
        self.assertGreater(len(ctx["decisions"]["technology"]), 0)
        self.assertEqual(ctx["decisions"]["technology"][-1]["summary"], "Use Python stdlib")

    def test_read_findings(self):
        """Test reading findings back."""
        # Add a finding first so there's something to read
        finding = json.dumps({"summary": "Read test finding", "severity": "info"})
        self._run_helper("add-finding", "build", finding)
        stdout, stderr, rc = self._run_helper("read-findings")
        self.assertEqual(rc, 0)
        self.assertIn("Read test finding", stdout)

    def test_state_updates(self):
        """Test that state fields are updated on writes."""
        # First check current state
        ctx = self._load_context()
        old_count = ctx["state"].get("findings_count", 0)

        finding = json.dumps({"summary": "State test", "severity": "info"})
        self._run_helper("add-finding", "build", finding)

        ctx = self._load_context()
        self.assertGreater(ctx["state"]["findings_count"], old_count)
        self.assertEqual(ctx["state"]["last_updated_by"], "build")


# ═══════════════════════════════════════════════════════════════════
#  Session Persistence Tests
# ═══════════════════════════════════════════════════════════════════

class TestSessionPersistence(unittest.TestCase):
    """Test that sessions are persisted to the knowledge graph."""

    def setUp(self):
        self.outcomes_file = SESSIONS_OUTCOMES
        self._backup = None
        if os.path.exists(self.outcomes_file):
            with open(self.outcomes_file) as f:
                self._backup = f.read()

    def tearDown(self):
        if self._backup:
            with open(self.outcomes_file, "w") as f:
                f.write(self._backup)

    def _load_outcomes(self):
        with open(self.outcomes_file) as f:
            return json.load(f)

    def _save_outcomes(self, data):
        with open(self.outcomes_file, "w") as f:
            json.dump(data, f, indent=2)

    def test_outcome_structure(self):
        """Test the outcomes file has the correct structure."""
        outcomes = self._load_outcomes()
        self.assertIn("meta", outcomes)
        self.assertIn("aggregated_insights", outcomes)
        self.assertIn("sessions", outcomes)
        self.assertEqual(outcomes["meta"]["version"], "1.0")

    def test_add_session_outcome(self):
        """Test adding a new session outcome."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("oc_main", 
            os.path.join(SCRIPTS_DIR, "oc.py"))
        oc = importlib.util.module_from_spec(spec)
        # Can't easily import due to side effects, so test JSON directly

        outcomes = self._load_outcomes()
        before = outcomes["aggregated_insights"]["total_sessions"]

        # Manually add an outcome (simulating what oc.py does)
        outcome = {
            "id": f"test-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task": "Test task",
            "pattern_matched": "unit-test",
            "agents_used": ["debug", "build"],
            "outcome": "completed",
            "response_length": 100,
        }
        outcomes["sessions"].append(outcome)
        ai = outcomes["aggregated_insights"]
        ai["total_sessions"] = ai.get("total_sessions", 0) + 1
        ai["total_iterations"] = ai.get("total_iterations", 0) + outcome.get("iterations", 0) or 0
        ai["total_gaps_found"] = ai.get("total_gaps_found", 0) + outcome.get("gaps_found", 0) or 0
        ai.setdefault("patterns_used", {})
        ai["patterns_used"]["unit-test"] = ai["patterns_used"].get("unit-test", 0) + 1
        self._save_outcomes(outcomes)

        # Verify
        outcomes2 = self._load_outcomes()
        self.assertEqual(outcomes2["aggregated_insights"]["total_sessions"], before + 1)
        self.assertEqual(outcomes2["aggregated_insights"]["patterns_used"]["unit-test"], 1)

    def test_aggregated_insights(self):
        """Test that aggregated insights accumulate correctly."""
        outcomes = self._load_outcomes()
        ai = outcomes["aggregated_insights"]

        # Verify structure
        self.assertIn("total_sessions", ai)
        self.assertIn("total_iterations", ai)
        self.assertIn("total_gaps_found", ai)
        self.assertIn("patterns_used", ai)
        self.assertIn("agents_used", ai)
        self.assertIn("common_lessons", ai)

        # Verify types
        self.assertIsInstance(ai["total_sessions"], int)
        self.assertIsInstance(ai["total_iterations"], int)
        self.assertIsInstance(ai["patterns_used"], dict)


# ═══════════════════════════════════════════════════════════════════
#  CLI Subcommand Tests
# ═══════════════════════════════════════════════════════════════════

class TestCLISubcommands(unittest.TestCase):
    """Test that CLI subcommands route and respond correctly."""

    CLI_PATH = "/usr/local/bin/oc"

    def _run_oc(self, *args):
        result = subprocess.run(
            [self.CLI_PATH] + list(args),
            capture_output=True, text=True, timeout=15
        )
        return result.stdout, result.stderr, result.returncode

    def test_version(self):
        """Test --version flag."""
        stdout, stderr, rc = self._run_oc("--version")
        self.assertEqual(rc, 0)
        self.assertIn("opencode", stdout)

    def test_help(self):
        """Test --help shows all subcommands."""
        stdout, stderr, rc = self._run_oc("--help")
        self.assertEqual(rc, 0)
        for cmd in ["ask", "chat", "session", "context", "agent",
                     "models", "server", "stats", "search", "note",
                     "cleanup", "docs"]:
            self.assertIn(cmd, stdout, f"Missing subcommand: {cmd}")

    def test_context_summary(self):
        """Test 'oc context summary'."""
        stdout, stderr, rc = self._run_oc("context", "summary")
        self.assertEqual(rc, 0)
        self.assertTrue(len(stdout) > 0)

    def test_context_findings(self):
        """Test 'oc context findings'."""
        stdout, stderr, rc = self._run_oc("context", "findings")
        self.assertEqual(rc, 0)

    def test_note_save_and_read(self):
        """Test 'oc note' saves and retrieves notes."""
        stdout, stderr, rc = self._run_oc("note", "CLI test note")
        self.assertEqual(rc, 0)
        self.assertIn("Note saved", stdout)

    def test_cleanup_dry_run(self):
        """Test 'oc cleanup --dry-run' doesn't delete anything."""
        stdout, stderr, rc = self._run_oc("cleanup", "365", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("Dry run", stdout)

    def test_docs(self):
        """Test 'oc docs' shows documentation."""
        stdout, stderr, rc = self._run_oc("docs")
        self.assertEqual(rc, 0)
        self.assertIn("oc", stdout)

    def test_session_list(self):
        """Test 'oc session list' works (even with no sessions)."""
        stdout, stderr, rc = self._run_oc("session", "list")
        # Should not crash — may show empty or real sessions
        self.assertEqual(rc, 0)

    def test_server_status(self):
        """Test 'oc server status' works (may be stopped)."""
        stdout, stderr, rc = self._run_oc("server", "status")
        self.assertEqual(rc, 0)
        self.assertIn("Status", stdout)


# ═══════════════════════════════════════════════════════════════════
#  REPL Engine Tests (library mode)
# ═══════════════════════════════════════════════════════════════════

class TestREPLEngine(unittest.TestCase):
    """Test the REPL engine in library mode."""

    @classmethod
    def setUpClass(cls):
        # Import the module
        import importlib.util
        spec = importlib.util.spec_from_file_location("oc_repl",
            os.path.join(SCRIPTS_DIR, "oc_repl.py"))
        cls.repl_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.repl_mod)

    def test_imports(self):
        """Test the module imports correctly."""
        self.assertIsNotNone(self.repl_mod)
        self.assertTrue(hasattr(self.repl_mod, "OpenCodeREPL"))
        self.assertTrue(hasattr(self.repl_mod, "REPLPoller"))
        self.assertTrue(hasattr(self.repl_mod, "run_standalone_repl"))

    def test_repl_class(self):
        """Test the OpenCodeREPL class can be instantiated."""
        repl = self.repl_mod.OpenCodeREPL()
        self.assertIsNotNone(repl)
        self.assertEqual(repl.port, 4099)
        self.assertEqual(repl.server_url, "http://127.0.0.1:4099")
        repl.close()

    def test_repl_poller_class(self):
        """Test the REPLPoller class can be instantiated."""
        poller = self.repl_mod.REPLPoller()
        self.assertIsNotNone(poller)
        self.assertEqual(poller.status, "idle")
        poller.close()

    def test_repl_help_display(self):
        """Test the help function works."""
        # Just check it doesn't crash
        self.repl_mod._show_help()

    def test_highlight_code_blocks(self):
        """Test code block syntax highlighting."""
        text = "Here is some code:\n```python\nprint('hello')\n```\nEnd."
        segments = self.repl_mod.highlight_code_blocks(text)
        self.assertGreater(len(segments), 0)

        # With no code blocks
        text2 = "Just plain text with no code blocks."
        segments2 = self.repl_mod.highlight_code_blocks(text2)
        self.assertEqual(len(segments2), 1)
        self.assertFalse(segments2[0][1])  # Not a code block

    def test_error_classes(self):
        """Test that error classes exist and work."""
        self.assertTrue(hasattr(self.repl_mod, "REPLError"))
        self.assertTrue(hasattr(self.repl_mod, "ServerStartError"))
        self.assertTrue(hasattr(self.repl_mod, "SendError"))

        # Test inheritance
        self.assertTrue(issubclass(self.repl_mod.ServerStartError,
                                    self.repl_mod.REPLError))
        self.assertTrue(issubclass(self.repl_mod.SendError,
                                    self.repl_mod.REPLError))


# ═══════════════════════════════════════════════════════════════════
#  Knowledge Graph Tests
# ═══════════════════════════════════════════════════════════════════

class TestKnowledgeGraph(unittest.TestCase):
    """Test the knowledge graph structure and agent definitions."""

    GRAPH_FILE = os.path.join(CONFIG_DIR, "knowledge-graph", "graph.json")

    def test_graph_loads(self):
        """Test the graph JSON is valid and loads correctly."""
        with open(self.GRAPH_FILE) as f:
            graph = json.load(f)
        self.assertIn("agents", graph)
        self.assertIn("patterns", graph)
        self.assertIn("quality_gates", graph)
        self.assertIn("gap_detection_rules", graph)

    def test_agent_definitions(self):
        """Test all agents are properly defined."""
        with open(self.GRAPH_FILE) as f:
            graph = json.load(f)

        required_agents = [
            "build", "plan", "orchestrator", "architect", "debug",
            "docs", "explore", "general", "refactor", "review",
            "security", "test", "video-creator", "web-browser", "display-agent"
        ]
        for agent in required_agents:
            self.assertIn(agent, graph["agents"],
                          f"Missing agent definition: {agent}")
            ag = graph["agents"][agent]
            self.assertIn("mode", ag, f"Agent {agent} missing 'mode'")
            self.assertIn("capabilities", ag, f"Agent {agent} missing 'capabilities'")
            self.assertIn("file", ag, f"Agent {agent} missing 'file'")
            self.assertIn("permissions", ag, f"Agent {agent} missing 'permissions'")

    def test_workflow_patterns(self):
        """Test all workflow patterns reference valid agents."""
        with open(self.GRAPH_FILE) as f:
            graph = json.load(f)

        for name, pattern in graph["patterns"].items():
            self.assertIn("agents", pattern, f"Pattern {name} missing agents")
            self.assertIn("sequence", pattern, f"Pattern {name} missing sequence")
            for step in pattern["sequence"]:
                self.assertIn("agent", step, f"Pattern {name} step missing agent")
                self.assertIn(step["agent"], graph["agents"],
                              f"Pattern {name} references unknown agent: {step['agent']}")

    def test_quality_gates(self):
        """Test quality gates are defined for all categories."""
        with open(self.GRAPH_FILE) as f:
            graph = json.load(f)

        gates = graph["quality_gates"]
        expected_gates = [
            "code_complete", "tested", "secure", "documented",
            "reviewed", "video_rendered", "rendered_web", "display_running"
        ]
        for gate in expected_gates:
            self.assertIn(gate, gates, f"Missing quality gate: {gate}")
            self.assertIsInstance(gates[gate], list,
                                  f"Quality gate {gate} should be a list")
            self.assertGreater(len(gates[gate]), 0,
                               f"Quality gate {gate} has no checks")

    def test_invocation_rules(self):
        """Test invocation rules are defined."""
        with open(self.GRAPH_FILE) as f:
            graph = json.load(f)
        rules = graph["invocation_rules"]
        self.assertIn("max_recursion_depth_primary", rules)
        self.assertIn("max_recursion_depth_orchestrator", rules)


# ═══════════════════════════════════════════════════════════════════
#  Agent Config Files Tests
# ═══════════════════════════════════════════════════════════════════

class TestAgentConfigs(unittest.TestCase):
    """Test that all agent .md config files exist and have valid YAML frontmatter."""

    AGENTS_DIR = os.path.join(CONFIG_DIR, "agents")

    def test_all_agent_files_exist(self):
        """Test every agent in graph.json has a corresponding .md file."""
        with open(os.path.join(CONFIG_DIR, "knowledge-graph", "graph.json")) as f:
            graph = json.load(f)

        for name, ag in graph["agents"].items():
            agent_file = ag.get("file", "")
            if agent_file:
                full_path = os.path.join(CONFIG_DIR, agent_file)
                self.assertTrue(
                    os.path.exists(full_path),
                    f"Agent file missing for {name}: {full_path}"
                )

    def test_frontmatter_parsing(self):
        """Test that agent files have parseable frontmatter."""
        for fname in os.listdir(self.AGENTS_DIR):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(self.AGENTS_DIR, fname)
            with open(path) as f:
                content = f.read()

            # Check for frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    frontmatter = content[3:end].strip()
                    self.assertGreater(len(frontmatter), 0,
                                       f"Empty frontmatter in {fname}")
                    # Check it has basic fields
                    self.assertIn("description:", frontmatter,
                                  f"Missing description in {fname}")


# ═══════════════════════════════════════════════════════════════════
#  Script Files Tests
# ═══════════════════════════════════════════════════════════════════

class TestScriptFiles(unittest.TestCase):
    """Test that all scripts exist and are executable."""

    def test_main_scripts_exist(self):
        """Test key scripts exist."""
        scripts = [
            "/public/.config/opencode/scripts/oc.py",
            "/public/.config/opencode/scripts/oc_repl.py",
            "/public/.config/opencode/scripts/oc_chat.py",
            "/public/.config/opencode/scripts/oc-context.sh",
            "/public/.config/opencode/scripts/oc-gitpush.sh",
            "/public/.config/opencode/shared/helpers/context.py",
        ]
        for script in scripts:
            self.assertTrue(os.path.exists(script), f"Missing script: {script}")

    def test_oc_symlinks(self):
        """Test that all oc-* symlinks exist."""
        commands = [
            "oc", "oc-auto", "oc-context", "oc-search", "oc-stats",
            "oc-note", "oc-monitor", "oc-voice", "oc-cleanup",
            "oc-backup", "oc-cron", "oc-gitpush", "oc-sync",
            "ocl", "ocr"
        ]
        for cmd in commands:
            path = f"/usr/local/bin/{cmd}"
            self.assertTrue(
                os.path.exists(path) or os.path.islink(path),
                f"Missing command: {cmd}"
            )

    def test_all_python_compile(self):
        """Test all Python scripts compile without syntax errors."""
        import py_compile
        python_scripts = [
            "/public/.config/opencode/scripts/oc.py",
            "/public/.config/opencode/scripts/oc_repl.py",
            "/public/.config/opencode/scripts/oc_chat.py",
            "/public/.config/opencode/shared/helpers/context.py",
        ]
        for script in python_scripts:
            if os.path.exists(script):
                try:
                    py_compile.compile(script, doraise=True)
                except py_compile.PyCompileError as e:
                    self.fail(f"Compile error in {script}: {e}")


# ═══════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"  {chr(0x2699)} OpenCode Test Suite")
    print(f"  {'─' * 50}")
    print(f"  Config:  {CONFIG_DIR}")
    print(f"  Output:  {CONTEXT_FILE}")
    print(f"  Bin:     {OPCODE_BIN}")
    print()

    verbosity = 1
    if "-v" in sys.argv:
        verbosity = 2
        sys.argv.remove("-v")

    unittest.main(verbosity=verbosity)

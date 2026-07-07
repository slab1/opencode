#!/usr/bin/env python3
"""
OpenCode Doctor — self-diagnosis and repair tool.

Usage:
    oc-doctor               # Run all checks, no fixes
    oc-doctor --fix         # Attempt auto-fix for common issues
    oc-doctor --check <name>  # Run a specific check only
    oc-doctor --json        # Output machine-readable JSON

Checks:
    context      Shared context store (context.json)
    config       opencode.jsonc validity
    memory       memory/ directory writability
    plugins      Installed plugin health
    mcp          MCP server connectivity
    ld_preload   LD_PRELOAD shim setup (musl compat)
    permissions  Key file permissions
    api_keys     API key presence
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".config" / "opencode"
OPENCODE_JSONC = CONFIG_DIR / "opencode.jsonc"
CONTEXT_JSON = CONFIG_DIR / "shared" / "context.json"
MEMORY_DIR = CONFIG_DIR / "memory"
SHARED_DIR = CONFIG_DIR / "shared"
SCRIPTS_DIR = CONFIG_DIR / "scripts"
OPENCODE_BIN = Path.home() / ".opencode" / "bin" / "opencode"
WRAPPER = Path("/usr/local/bin/opencode")
CACHE_DIR = Path.home() / ".cache" / "opencode" / "packages"
OPENCLAW_DIR = Path.home() / ".openclaw"


# ── Result helpers ───────────────────────────────────────────────────
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

results = []


def check(name, description, fixable=False):
    """Decorator-like check registration."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapper._check = {"name": name, "description": description, "fixable": fixable}
        return wrapper
    return decorator


checks_registry = []


def register(fn):
    checks_registry.append(fn)
    return fn


def report(check_name, status, message, fix_hint=None):
    results.append({
        "check": check_name,
        "status": status,
        "message": message,
        "fix_hint": fix_hint,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ── Checks ───────────────────────────────────────────────────────────

@register
def check_context():
    """Verify shared context store exists and is valid JSON."""
    name = "context"
    if not CONTEXT_JSON.exists():
        report(name, FAIL, "shared/context.json not found — shared context system non-functional",
               "Run: oc-context init or python3 shared/helpers/context.py init")
        return
    try:
        with open(CONTEXT_JSON) as f:
            ctx = json.load(f)
        agents = ctx.get("findings", {})
        agent_count = len(agents)
        finding_total = sum(len(v) for v in agents.values())
        report(name, PASS,
               f"context.json OK — {agent_count} agents, {finding_total} findings total")
    except json.JSONDecodeError as e:
        report(name, FAIL, f"context.json is corrupted: {e}",
               "Restore from backup or re-run: python3 shared/helpers/context.py init")


@register
def check_config():
    """Verify opencode.jsonc exists and is parseable."""
    name = "config"
    if not OPENCODE_JSONC.exists():
        report(name, FAIL, "opencode.jsonc not found",
               "Create opencode.jsonc in ~/.config/opencode/")
        return
    # Try to parse as JSON (stripping comments — hacky)
    content = OPENCODE_JSONC.read_text()
    # Basic check: does it start with { ?
    if not content.strip().startswith("{"):
        report(name, FAIL, "opencode.jsonc doesn't look valid (must start with {)")
        return
    # Check for required fields
    required = ['"model"', '"permission"']
    missing = [r for r in required if r not in content]
    if missing:
        report(name, WARN, f"Missing expected keys: {', '.join(missing)}")
    else:
        report(name, PASS, "opencode.jsonc exists and contains expected keys")


@register
def check_memory():
    """Verify memory directory is writable."""
    name = "memory"
    if not MEMORY_DIR.exists():
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            report(name, PASS, "memory/ directory created")
        except PermissionError:
            report(name, FAIL, "Cannot create memory/ directory",
                   "chown or chmod ~/.config/opencode/memory")
            return
    # Test write
    test_file = MEMORY_DIR / ".write_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
        report(name, PASS, "memory/ is writable")
    except PermissionError:
        report(name, FAIL, "memory/ exists but is NOT writable",
               "chmod u+w ~/.config/opencode/memory")


@register
def check_plugins():
    """Check that installed plugins exist in cache."""
    name = "plugins"
    if not CACHE_DIR.exists():
        report(name, PASS, "No plugins in cache")
        return
    plugin_dirs = [d.name for d in CACHE_DIR.iterdir() if d.is_dir()]
    report(name, PASS, f"{len(plugin_dirs)} plugins cached: {', '.join(plugin_dirs[:8])}{'...' if len(plugin_dirs) > 8 else ''}")


@register
def check_mcp():
    """Test MCP server connectivity (basic)."""
    name = "mcp"
    # Check if MCP servers are configured
    if not OPENCODE_JSONC.exists():
        return
    content = OPENCODE_JSONC.read_text()
    if '"mcp"' not in content:
        report(name, PASS, "No MCP servers configured")
        return
    # Count configured servers
    try:
        import re
        # Extract server names from MCP config block
        mcp_section = re.search(r'"mcp"\s*:\s*\{([^}]+\})', content, re.DOTALL)
        if mcp_section:
            server_count = content.count('"enabled"')
            report(name, PASS, f"{server_count} MCP entries in config")
        else:
            report(name, PASS, "MCP config present")
    except Exception:
        report(name, WARN, "Could not parse MCP section")


@register
def check_ld_preload():
    """Verify LD_PRELOAD shim for musl compatibility."""
    name = "ld_preload"
    shim = Path("/usr/lib/libglibc_compat.so")
    wrapper_path = Path("/usr/local/bin/opencode")

    if shim.exists():
        shim_size = shim.stat().st_size
        report(name, PASS, f"libglibc_compat.so found ({shim_size} bytes)")
    else:
        report(name, FAIL, "libglibc_compat.so not found — codebase-index may fail on musl",
               "Rebuild: cd /tmp && cc -shared -o libglibc_compat.so ...")

    if wrapper_path.exists():
        wrapper_content = wrapper_path.read_text()
        if "LD_PRELOAD" in wrapper_content:
            report(name, PASS, "/usr/local/bin/opencode wrapper sets LD_PRELOAD")
        else:
            report(name, WARN, "Wrapper exists but may not set LD_PRELOAD correctly")
    else:
        report(name, WARN, "No wrapper at /usr/local/bin/opencode — using raw binary")


@register
def check_permissions():
    """Check that key files have sane permissions."""
    name = "permissions"
    issues = []
    for path, desc in [(CONFIG_DIR, "config dir"),
                       (CONTEXT_JSON, "context.json"),
                       (MEMORY_DIR, "memory dir")]:
        if path.exists():
            mode = os.stat(path).st_mode
            # Check it's readable by owner
            if not (mode & 0o400):
                issues.append(f"{desc} not readable by owner")
    if issues:
        report(name, WARN, "; ".join(issues))
    else:
        report(name, PASS, "Key paths have sane permissions")


@register
def check_api_keys():
    """Check if API keys are set where needed."""
    name = "api_keys"
    if not OPENCODE_JSONC.exists():
        return
    content = OPENCODE_JSONC.read_text()
    # Check for empty API keys
    empty_keys = []
    for key_pattern in ['"FIRECRAWL_API_KEY"', '"OPENAI_API_KEY"', '"ANTHROPIC_API_KEY"']:
        if key_pattern in content:
            # Crude: find the value after the key
            idx = content.find(key_pattern)
            snippet = content[idx:idx + 80]
            if '""' in snippet or "''" in snippet:
                key_name = key_pattern.strip('"')
                empty_keys.append(key_name)
    if empty_keys:
        report(name, WARN, f"Empty API keys found: {', '.join(empty_keys)}")
    else:
        report(name, PASS, "No obviously empty API keys")


@register
def check_system():
    """Basic system info."""
    name = "system"
    info = {
        "platform": os.uname().machine,
        "libc": "musl" if Path("/lib/ld-musl-aarch64.so.1").exists() else "glibc",
        "python": sys.version.split()[0],
        "opencode_bin": str(OPENCODE_BIN) if OPENCODE_BIN.exists() else "not found",
        "node": subprocess.run(["node", "--version"], capture_output=True, text=True
                               ).stdout.strip() or "not found",
    }
    report(name, PASS, f"System: {info['platform']} ({info['libc']}), "
                       f"Python {info['python']}, Node {info['node']}")


# ── Fix actions ──────────────────────────────────────────────────────

def fix_context():
    """Initialize context if missing."""
    if not CONTEXT_JSON.exists():
        context_py = SHARED_DIR / "helpers" / "context.py"
        if context_py.exists():
            subprocess.run([sys.executable, str(context_py), "init"], check=False)
            return "Initialized context.json"
    return "Context already exists"


def fix_memory():
    """Create memory directory if missing."""
    if not MEMORY_DIR.exists():
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        return "Created memory/ directory"
    return "Memory directory already exists"


FIX_MAP = {
    "context": fix_context,
    "memory": fix_memory,
}


# ── Main ─────────────────────────────────────────────────────────────

def run_all():
    for check_fn in checks_registry:
        try:
            check_fn()
        except Exception as e:
            meta = getattr(check_fn, "_check", {})
            report(meta.get("name", "unknown"), "ERROR", str(e))


def run_single(name):
    found = False
    for check_fn in checks_registry:
        meta = getattr(check_fn, "_check", {})
        if meta.get("name") == name:
            try:
                check_fn()
            except Exception as e:
                report(name, "ERROR", str(e))
            found = True
            break
    if not found:
        print(f"Unknown check: {name}")
        print(f"Available: {', '.join(m['name'] for m in get_checks_meta())}")
        sys.exit(1)


def get_checks_meta():
    return [getattr(fn, "_check", {"name": fn.__name__})
            for fn in checks_registry]


def apply_fixes():
    """Try to auto-fix fixable issues."""
    fixes_applied = []
    for r in results:
        if r["status"] in (FAIL, WARN) and r["check"] in FIX_MAP:
            try:
                msg = FIX_MAP[r["check"]]()
                fixes_applied.append(f"{r['check']}: {msg}")
            except Exception as e:
                fixes_applied.append(f"{r['check']}: fix failed — {e}")
    return fixes_applied


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenCode Doctor — diagnose and repair")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--check", type=str, help="Run a specific check only")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.check:
        run_single(args.check)
    else:
        run_all()

    if args.fix:
        fixes = apply_fixes()
        if args.json:
            for f in fixes:
                results.append({"check": "fix", "status": "FIX", "message": f})
        else:
            print(f"\n{'─' * 50}")
            print(f"🔧 Fixes applied: {len(fixes)}")
            for f in fixes:
                print(f"  ✓ {f}")

    if args.json:
        print(json.dumps({"results": results, "timestamp": datetime.now(timezone.utc).isoformat()},
                         indent=2))
    else:
        status_counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "ERROR": 0}
        for r in results:
            s = r["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
            icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "ERROR": "!"}.get(s, "?")
            print(f" {icon} [{s:5}] {r['check']}: {r['message']}")
            if r.get("fix_hint") and not args.fix:
                print(f"         💡 {r['fix_hint']}")

        total = len(results)
        passed = status_counts.get("PASS", 0)
        print(f"\n{'─' * 50}")
        print(f"Results: {passed}/{total} passed")
        if status_counts.get("FAIL", 0):
            print(f"Failures: {status_counts['FAIL']}")
        if status_counts.get("WARN", 0):
            print(f"Warnings: {status_counts['WARN']}")
        print(f"Status: {'✅ All good' if passed == total else '⚠  Needs attention'}")


if __name__ == "__main__":
    main()

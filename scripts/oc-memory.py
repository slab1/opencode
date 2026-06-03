#!/usr/bin/env python3
"""
OpenCode Memory Auto-Save — Saves session context to daily notes.

Writes session findings, decisions, and artifacts from shared/context.json
into memory/YYYY-MM-DD.md for long-term continuity.

Usage:
    oc-memory save         # Save current context as today's daily note
    oc-memory list         # List recent daily notes
    oc-memory show <date>  # Show a specific daily note
    oc-memory summary      # Show summary of what's been saved
"""

import json
import os
import sys
import subprocess
from datetime import datetime, date, timezone
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "opencode"
CONTEXT_JSON = CONFIG_DIR / "shared" / "context.json"
MEMORY_DIR = CONFIG_DIR / "memory"
FINDINGS_DIR = CONFIG_DIR / "shared" / "findings"


def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def load_context():
    if not CONTEXT_JSON.exists():
        print("No context.json found — run oc-context init first", file=sys.stderr)
        return None
    try:
        with open(CONTEXT_JSON) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Corrupted context.json: {e}", file=sys.stderr)
        return None


def get_today_path():
    today = date.today()
    return MEMORY_DIR / f"{today.isoformat()}.md"


def read_existing_note(path):
    if path.exists():
        return path.read_text()
    return None


def format_section(title, items, max_items=5):
    """Format a list of items into a markdown section."""
    if not items:
        return ""
    lines = [f"### {title}"]
    for item in items[:max_items]:
        if isinstance(item, dict):
            summary = item.get("summary", str(item.get("id", "")))[:120]
            severity = item.get("severity", "")
            severity_tag = f" [{severity.upper()}]" if severity else ""
            lines.append(f"- {summary}{severity_tag}")
        else:
            lines.append(f"- {str(item)[:120]}")
    if len(items) > max_items:
        lines.append(f"- *...and {len(items) - max_items} more*")
    lines.append("")
    return "\n".join(lines)


def cmd_save():
    """Save current context as today's daily note."""
    ctx = load_context()
    if not ctx:
        return 1

    ensure_memory_dir()
    path = get_today_path()

    # Build the note content
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    session = ctx.get("session", {})
    session_id = session.get("current_id", "unknown")
    session_title = session.get("current_title", "Untitled")
    workflow = session.get("workflow_pattern", "")

    lines = [
        f"# Session Notes — {date.today().isoformat()}",
        f"",
        f"_Saved at {now}_",
        f"",
        f"**Session**: `{session_id}` — {session_title}",
        (f"**Workflow**: {workflow}" if workflow else ""),
        f"",
        f"---",
        f"",
    ]

    # Agent findings
    for agent, findings in ctx.get("findings", {}).items():
        if findings:
            lines.append(format_section(f"Findings: {agent}", findings))

    # Decisions
    for category, decisions in ctx.get("decisions", {}).items():
        if decisions:
            lines.append(format_section(f"Decisions: {category}", decisions))

    # Artifacts (stored as strings, not dicts)
    artifacts = ctx.get("artifacts", {})
    for cat, items in artifacts.items():
        if items:
            lines.append(f"### Artifacts: {cat}")
            for item in items[:10]:
                lines.append(f"- {str(item)[:120]}")
            if len(items) > 10:
                lines.append(f"- *...and {len(items) - 10} more*")
            lines.append("")

    # Cross-references
    refs = ctx.get("cross_references", [])
    if refs:
        lines.append(format_section("Cross-References", refs))

    # Workflow trace
    trace = ctx.get("workflow_trace", [])
    if trace:
        lines.append(format_section("Workflow Trace", trace))

    note_content = "\n".join(line for line in lines if line) + "\n"

    # Merge with existing if present
    existing = read_existing_note(path)
    if existing:
        # Append new content after the existing note
        if note_content.strip() not in existing:
            note_content = existing.rstrip() + "\n\n---\n\n" + note_content
        else:
            print(f"Today's note already contains this context — skipping duplicate")
            return 0

    path.write_text(note_content)
    finding_count = sum(len(v) for v in ctx.get("findings", {}).values())
    artifact_count = sum(len(v) for v in ctx.get("artifacts", {}).values())
    decision_count = sum(len(v) for v in ctx.get("decisions", {}).values())
    print(f"Saved session context to {path}")
    print(f"  {finding_count} findings, {decision_count} decisions, {artifact_count} artifacts")
    return 0


def cmd_list():
    """List recent daily notes."""
    ensure_memory_dir()
    notes = sorted(MEMORY_DIR.glob("*.md"), reverse=True)
    if not notes:
        print("No daily notes yet. Run 'oc-memory save' to create one.")
        return

    print(f"{'Date':<14} {'Size':<8} {'Preview'}")
    print("-" * 60)
    for note in notes[:14]:
        size = note.stat().st_size
        preview = note.read_text().split("\n")[0][:55] if size > 0 else "(empty)"
        print(f"{note.stem:<14} {size:<8} {preview}")


def cmd_show(date_str):
    """Show a specific daily note."""
    ensure_memory_dir()
    # Try exact match first
    path = MEMORY_DIR / f"{date_str}.md"
    if not path.exists():
        # Try as a stem
        path = MEMORY_DIR / date_str
        if not path.exists():
            print(f"No note found for date: {date_str}", file=sys.stderr)
            print(f"Notes: {', '.join(p.stem for p in sorted(MEMORY_DIR.glob('*.md')))}")
            return 1
    print(path.read_text())
    return 0


def cmd_summary():
    """Show summary of all saved memory."""
    ctx = load_context()
    ensure_memory_dir()
    notes = sorted(MEMORY_DIR.glob("*.md"))
    total_notes = len(notes)
    total_size = sum(n.stat().st_size for n in notes)

    # Count findings in context
    ctx_findings = {}
    for agent, findings in (ctx or {}).get("findings", {}).items():
        if findings:
            ctx_findings[agent] = len(findings)

    print(f"📝 Memory Summary")
    print(f"{'─' * 50}")
    print(f"Daily notes:      {total_notes} ({total_size:,} bytes)")
    print(f"Date range:       {notes[0].stem} → {notes[-1].stem}" if notes else "  None yet")
    print(f"Agents with data: {len(ctx_findings)} ({sum(ctx_findings.values())} findings total)")
    for agent, count in sorted(ctx_findings.items()):
        print(f"  · {agent}: {count} findings")
    print(f"\nStorage:         {MEMORY_DIR}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OpenCode Memory Manager")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("save", help="Save current context as daily note")
    sub.add_parser("list", help="List recent daily notes")
    show_p = sub.add_parser("show", help="Show a specific daily note")
    show_p.add_argument("date", help="Date (YYYY-MM-DD or filename stem)")
    sub.add_parser("summary", help="Show memory summary")

    args = parser.parse_args()

    commands = {
        "save": cmd_save,
        "list": cmd_list,
        "show": lambda: cmd_show(args.date),
        "summary": cmd_summary,
    }

    fn = commands.get(args.command)
    if fn:
        return fn()
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Skill Curator — Hermes-inspired skill manifest tracking

Usage:
  python3 scripts/oc-skills-curate.py check      # Check for changes vs manifest
  python3 scripts/oc-skills-curate.py update     # Rebuild manifest
  python3 scripts/oc-skills-curate.py stale      # Report stale/unused skills
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILLS_DIR = Path.home() / ".config" / "opencode" / "skills"
MANIFEST_FILE = SKILLS_DIR / "manifest.json"
STALE_AFTER_DAYS = 90


def scan_skills() -> dict:
    """Scan all SKILL.md files and return manifest entries."""
    manifest = {}
    for f in sorted(SKILLS_DIR.rglob("SKILL.md")):
        rel = str(f.relative_to(SKILLS_DIR))
        content = f.read_bytes()
        manifest[rel] = {
            "hash": hashlib.md5(content).hexdigest(),
            "size": len(content),
            "modified": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }
    return manifest


def load_manifest() -> dict:
    """Load existing manifest from disk."""
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def save_manifest(manifest: dict):
    """Write manifest to disk."""
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"✓ Manifest updated: {len(manifest)} skills")


def cmd_check():
    """Check for changes since last manifest."""
    old = load_manifest()
    current = scan_skills()

    new_skills = []
    changed = []
    removed = []
    unchanged = 0

    for name, info in current.items():
        if name not in old:
            new_skills.append(name)
        elif old[name]["hash"] != info["hash"]:
            changed.append(name)
        else:
            unchanged += 1

    for name in old:
        if name not in current:
            removed.append(name)

    print(f"\n{'═' * 60}")
    print(f"  Skill Curator — Change Check")
    print(f"{'═' * 60}")
    print(f"  Total:    {len(current)}")
    print(f"  Unchanged: {unchanged}")
    print(f"  New:       {len(new_skills)}")
    print(f"  Changed:   {len(changed)}")
    print(f"  Removed:   {len(removed)}")
    print()

    if new_skills:
        print(f"  📄 New skills:")
        for s in new_skills:
            print(f"    + {s}")
        print()
    if changed:
        print(f"  ✏️  Changed skills:")
        for s in changed:
            print(f"    ~ {s}")
        print()
    if removed:
        print(f"  🗑️  Removed skills:")
        for s in removed:
            print(f"    - {s}")
        print()

    if not (new_skills or changed or removed):
        print("  ✅ Everything up to date.")
        return 0
    return 1 if (changed or removed) else 0


def cmd_update():
    """Rebuild manifest from current state."""
    manifest = scan_skills()
    save_manifest(manifest)
    return 0


def cmd_stale():
    """Report skills not modified recently."""
    manifest = scan_skills()
    now = datetime.now(timezone.utc)
    stale_found = False

    print(f"\n{'═' * 60}")
    print(f"  Skill Curator — Stale Check (>={STALE_AFTER_DAYS} days)")
    print(f"{'═' * 60}")

    for name, info in sorted(manifest.items()):
        mod = datetime.fromisoformat(info["modified"])
        age_days = (now - mod).days
        if age_days >= STALE_AFTER_DAYS:
            print(f"  🗄️  {name:<50} {age_days:3d} days old")
            stale_found = True

    if not stale_found:
        print(f"  ✅ No stale skills (threshold: {STALE_AFTER_DAYS} days)")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    commands = {
        "check": cmd_check,
        "update": cmd_update,
        "stale": cmd_stale,
    }

    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    sys.exit(commands[cmd]())


if __name__ == "__main__":
    main()

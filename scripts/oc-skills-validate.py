#!/usr/bin/env python3
"""oc-skills-validate - Validate all skills in the skills directory.

Checks:
- Frontmatter exists and is well-formed
- name follows [a-z0-9-]+ pattern, 1-64 chars
- description is present, 1-1024 chars
- description contains useful trigger info (not just title)
- No obvious formatting issues

Usage:
    oc-skills-validate           # validate all skills
    oc-skills-validate <name>    # validate one skill
    oc-skills-validate --strict  # also check description quality
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / ".config" / "opencode" / "skills"

NAME_PATTERN = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
NAME_MAX = 64
DESC_MAX = 1024
FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---', re.DOTALL)


def validate_skill(skill_dir, strict=False):
    """Return (ok: bool, errors: list, info: dict)."""
    errors = []
    info = {"path": str(skill_dir), "name": skill_dir.name}
    
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return False, ["SKILL.md not found"], info
    
    content = skill_file.read_text()
    info["size_bytes"] = len(content.encode("utf-8"))
    
    # Check frontmatter
    fm_match = FRONTMATTER_RE.match(content)
    if not fm_match:
        return False, ["No frontmatter (must start with --- and end with ---)"], info
    
    fm = fm_match.group(1)
    
    # Parse name
    name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
    name = name_m.group(1).strip() if name_m else None
    if not name:
        errors.append("Missing 'name' in frontmatter")
    elif not NAME_PATTERN.match(name):
        errors.append(f"Invalid name format: '{name}' (must match [a-z0-9-]+, 1-64 chars)")
    elif len(name) > NAME_MAX:
        errors.append(f"Name too long: {len(name)} chars (max {NAME_MAX})")
    else:
        info["name"] = name
        if name != skill_dir.name:
            errors.append(f"Name '{name}' doesn't match directory '{skill_dir.name}'")
    
    # Parse description
    desc_m = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
    desc = desc_m.group(1).strip() if desc_m else None
    if not desc:
        errors.append("Missing 'description' in frontmatter")
    elif len(desc) > DESC_MAX:
        errors.append(f"Description too long: {len(desc)} chars (max {DESC_MAX})")
    else:
        info["desc_len"] = len(desc)
        if strict:
            # Strict checks: description should have trigger words
            trigger_words = ['use', 'when', 'for', 'how', 'agent']
            if not any(w in desc.lower() for w in trigger_words):
                errors.append(f"Description lacks trigger words (should say 'use when...' or 'for...')")
            if len(desc) < 50:
                errors.append(f"Description too short ({len(desc)} chars) — should be 100+ for discoverability")
    
    # Check compatibility
    compat_m = re.search(r'^compatibility:\s*(.+)$', fm, re.MULTILINE)
    if compat_m:
        info["compatibility"] = compat_m.group(1).strip()
    
    # Check for required structure (a body with at least one heading)
    body = content[fm_match.end():]
    if not re.search(r'^#\s+', body, re.MULTILINE):
        errors.append("No markdown heading (# Title) in body")
    
    # Check for "When to use" section (helps with skill discovery)
    # Accept multiple phrasings, case-insensitive
    if strict:
        body_lower = body.lower()
        has_when_to_use = any(
            phrase in body_lower for phrase in [
                'when to use', 'when to use me', 'use when', 'when to use this'
            ]
        )
        if not has_when_to_use:
            errors.append("Missing 'When to use' (or 'Use when') section")
    
    return len(errors) == 0, errors, info


def main():
    parser = argparse.ArgumentParser(description="Validate skill files")
    parser.add_argument("name", nargs="?", help="Validate one skill by name")
    parser.add_argument("--strict", action="store_true", help="Stricter checks")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    if not SKILLS_DIR.exists():
        print(f"ERROR: {SKILLS_DIR} does not exist", file=sys.stderr)
        sys.exit(1)
    
    if args.name:
        skill_dir = SKILLS_DIR / args.name
        if not skill_dir.exists():
            print(f"ERROR: Skill '{args.name}' not found in {SKILLS_DIR}", file=sys.stderr)
            sys.exit(1)
        ok, errors, info = validate_skill(skill_dir, strict=args.strict)
        if args.json:
            print(json.dumps({"ok": ok, "errors": errors, "info": info}, indent=2))
        else:
            if ok:
                print(f"OK: {info['name']}")
                print(f"  Path: {info['path']}")
                print(f"  Size: {info.get('size_bytes', 0)} bytes")
                if 'desc_len' in info:
                    print(f"  Description: {info['desc_len']} chars")
            else:
                print(f"FAIL: {info['name']}")
                for e in errors:
                    print(f"  - {e}")
        sys.exit(0 if ok else 1)
    
    # Validate all skills
    results = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        ok, errors, info = validate_skill(skill_dir, strict=args.strict)
        results.append((ok, errors, info))
    
    if args.json:
        print(json.dumps({
            "total": len(results),
            "passed": sum(1 for ok, _, _ in results if ok),
            "failed": sum(1 for ok, _, _ in results if not ok),
            "results": [{"ok": ok, "errors": errors, "info": info} for ok, errors, info in results]
        }, indent=2))
    else:
        print(f"Validating {len(results)} skills in {SKILLS_DIR}")
        print()
        passed = 0
        failed = 0
        for ok, errors, info in results:
            if ok:
                print(f"  PASS  {info['name']:30s}  {info.get('size_bytes', 0):5d} bytes  desc={info.get('desc_len', '?')} chars")
                passed += 1
            else:
                print(f"  FAIL  {info['name']:30s}")
                for e in errors:
                    print(f"        - {e}")
                failed += 1
        print()
        print(f"Summary: {passed} passed, {failed} failed, {len(results)} total")
        if failed > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()

"""Quality-gated skills hub (Bet 9).

Verification gateway for the skill collection: structural rules + stub
detection, producing a machine-readable manifest ("listed = eval-passed").

A skill PASSes only if it is structurally complete AND clearly not an
unverified stub. Any UNVERIFIED-DO-NOT-USE / NotImplementedError /
placeholder marker in the body fails the skill — the same honesty rule the
skill_synthesizer scaffold mode already encodes.

This is the wedge vs ToxicSkills (36% of public skills flawed, 13.4%
critical) and every unverified marketplace: in this hub, a skill is listed
only after verification, verified by CI on every skills/ change.

Usage (CLI): python3 -m opencode_improvement skills-verify ...
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

BASE_DIR = Path.home() / ".config" / "opencode"
SKILLS_DIR = BASE_DIR / "skills"

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# Honesty markers — presence of any in body/frontmatter = unverified stub.
STUB_MARKERS = [
    "UNVERIFIED-DO-NOT-USE",
    "NotImplementedError",
    "NOT IMPLEMENTED",
    "TODO: implement actual",
    "print stub",
]
MIN_BODY_CHARS = 50


def parse_frontmatter(content: str) -> Tuple[Dict[str, str], str, str]:
    """Return (fields, body, error). fields is a dict of lowercase-keyed scalars.

    Handles plain scalars and block scalars (|- / >): subsequent indented
    lines are folded into the current key's value.
    """
    fm_match = FRONTMATTER_RE.match(content)
    if not fm_match:
        return {}, content, "No frontmatter (must start with --- and end with ---)"
    fm = fm_match.group(1)
    fields: Dict[str, str] = {}
    current_key: str = None
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            current_key = m.group(1).lower()
            fields[current_key] = m.group(2).strip()
        elif current_key and line[:1] in (" ", "\t") and line.strip():
            # Block-scalar continuation line — fold into the current value.
            fields[current_key] = (fields[current_key] + " " + line.strip()).strip()
        else:
            current_key = None  # blank line or unindented non-key line
    return fields, content[fm_match.end():].strip(), None


def verify_skill(skill_dir: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Verify one skill dir (must contain SKILL.md). Returns (ok, errors, info)."""
    errors: List[str] = []
    info: Dict[str, Any] = {"name": skill_dir.name, "path": str(skill_dir)}

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return False, ["SKILL.md not found"], info

    content = skill_file.read_text()
    info["size_bytes"] = len(content.encode("utf-8"))

    fields, body, fm_error = parse_frontmatter(content)
    if fm_error:
        return False, [fm_error], info

    name = fields.get("name", "")
    if not name:
        errors.append("Missing 'name' in frontmatter")
    elif not NAME_PATTERN.match(name):
        errors.append(f"Invalid name format: '{name}' (must match [a-z0-9_-]+)")
    else:
        info["name"] = name
        if name != skill_dir.name:
            info["note"] = f"name '{name}' != directory '{skill_dir.name}' (layout convention, OK)"

    desc = fields.get("description", "")
    if not desc:
        errors.append("Missing 'description' in frontmatter")
    else:
        info["desc_len"] = len(desc)
        if len(desc) < 10:
            errors.append("Description too short (likely unverified)")

    if not body:
        errors.append("Empty body")
    elif len(body) < MIN_BODY_CHARS:
        errors.append(f"Body too short ({len(body)} chars < {MIN_BODY_CHARS}) — likely a stub")
    if body and not re.search(r"^#\s+", body, re.MULTILINE):
        info.setdefault("note", "")
        info["note"] = (info["note"] + " | " if info["note"] else "") + "no '# Title' heading (h2/h3 OK)"

    # Stub detection: honesty markers anywhere in the document.
    doc = content.lower()
    for marker in STUB_MARKERS:
        if marker.lower() in doc:
            errors.append(f"Unverified marker present: '{marker}' (skill must not be listed)")

    return len(errors) == 0, errors, info


def verify_all(root: Path) -> Dict[str, Any]:
    """Walk root recursively; every dir with a SKILL.md is one skill."""
    results: List[Dict[str, Any]] = []
    if not root.exists():
        return {
            "format": "aether-skills-verified",
            "version": 1,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "root": str(root),
            "note": f"root does not exist: {root}",
            "total": 0, "passed": 0, "failed": 0, "skills": [],
        }
    for skill_file in sorted(root.rglob("SKILL.md")):
        skill_dir = skill_file.parent
        ok, errors, info = verify_skill(skill_dir)
        results.append({"ok": ok, "errors": errors, "info": info})
    return {
        "format": "aether-skills-verified",
        "version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "root": str(root),
        "total": len(results),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "skills": results,
    }


def write_manifest(manifest: Dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))
    return path


def main(argv: List[str] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="skills-verify", description=__doc__.splitlines()[0])
    p.add_argument("--path", default=str(SKILLS_DIR), help=f"Root dir to scan (default {SKILLS_DIR})")
    p.add_argument("--json", action="store_true", help="Print manifest JSON to stdout")
    p.add_argument("--manifest", metavar="PATH", default=None, help="Write verified-manifest JSON to PATH")
    p.add_argument("--no-fail", action="store_true", help="Exit 0 even when skills fail (report-only)")
    args = p.parse_args(argv)

    manifest = verify_all(Path(args.path))
    if args.manifest:
        write_manifest(manifest, args.manifest)
        print(f"Verified manifest -> {args.manifest} ({manifest['passed']}/{manifest['total']} passed)")
    if args.json:
        print(json.dumps(manifest, indent=2))
    elif not args.manifest:
        for s in manifest["skills"]:
            mark = "PASS" if s["ok"] else "FAIL"
            print(f"  {mark}  {s['info']['name']}")
            for e in s["errors"]:
                print(f"        - {e}")
        print(f"Summary: {manifest['passed']} passed, {manifest['failed']} failed, {manifest['total']} total")

    if manifest["failed"] > 0 and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
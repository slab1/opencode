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

# --- Official Agent Skills spec conformance (https://agentskills.io/specification) ---
# NAME_PATTERN above is deliberately permissive (it allows `_` and a leading digit-run)
# because it guards against garbage names. The spec is stricter, so spec violations are
# reported separately and only promoted to failures under --strict-spec. That keeps the
# 71 vendored `category-skill` directory conventions from breaking every build while
# still making the debt visible and blocking for newly authored skills.
SPEC_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SPEC_MAX_NAME = 64
SPEC_MAX_DESC = 1024
SPEC_MAX_COMPAT = 500
SPEC_MAX_LINES = 500  # progressive-disclosure budget for SKILL.md

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
    #
    # Opt-in escape hatch: a skill that *teaches* stub detection (e.g. one that
    # documents NotImplementedError as a red flag it greps for) contains those
    # markers legitimately and must not be failed for honesty. This is an
    # explicit frontmatter declaration rather than a heuristic, because a
    # genuine stub is ALSO written as a fenced `raise NotImplementedError` —
    # so "is it inside a code fence" cannot distinguish the two cases without
    # silently weakening the honesty gate across the whole collection.
    # The suppression is recorded in the manifest so it stays auditable.
    metadata = fields.get("metadata") or ""
    teaches_markers = "teaches_stub_markers" in metadata and "true" in metadata.lower()
    doc = content.lower()
    if teaches_markers:
        info["marker_check_suppressed"] = True
        info.setdefault("note", "")
        info["note"] = (info["note"] + " | " if info["note"] else "") + \
            "stub-marker check suppressed via metadata.teaches_stub_markers (reviewed by hand)"
    else:
        for marker in STUB_MARKERS:
            if marker.lower() in doc:
                errors.append(f"Unverified marker present: '{marker}' (skill must not be listed)")

    info["spec"] = spec_conformance(skill_dir, fields, content)
    return len(errors) == 0, errors, info


def spec_conformance(skill_dir: Path, fields: Dict[str, str], content: str) -> List[Dict[str, str]]:
    """Check a skill against the official Agent Skills specification.

    Returns a list of {severity, check, detail}. `error` = spec violation,
    `warn` = quality signal. These are advisory unless --strict-spec is passed,
    because vendored third-party skills carry known, accepted deviations.
    """
    out: List[Dict[str, str]] = []

    def err(check: str, detail: str) -> None:
        out.append({"severity": "error", "check": check, "detail": detail})

    def warn(check: str, detail: str) -> None:
        out.append({"severity": "warn", "check": check, "detail": detail})

    name = (fields.get("name") or "").strip()
    if name:
        if len(name) > SPEC_MAX_NAME:
            err("name", f"name is {len(name)} chars (spec max {SPEC_MAX_NAME})")
        if not SPEC_NAME_RE.match(name):
            err("name", f"name {name!r} violates spec: lowercase letters/digits/hyphens only, "
                         "no leading/trailing/consecutive hyphen")
        if name != skill_dir.name:
            err("name-matches-dirname",
                f"name {name!r} != directory {skill_dir.name!r} (spec requires they match)")

    desc = (fields.get("description") or "").strip()
    if desc:
        if len(desc) > SPEC_MAX_DESC:
            err("description", f"description is {len(desc)} chars (spec max {SPEC_MAX_DESC})")
        if "use when" not in desc.lower():
            warn("description", "description has no 'Use when' trigger clause — "
                                "weaker skill routing")

    compat = (fields.get("compatibility") or "").strip()
    if compat and len(compat) > SPEC_MAX_COMPAT:
        err("compatibility", f"compatibility is {len(compat)} chars (spec max {SPEC_MAX_COMPAT})")

    unknown = sorted(set(fields) - SPEC_KEYS)
    if unknown:
        warn("top-level-keys", f"non-spec frontmatter keys are ignored by loaders: {unknown}")

    n_lines = len(content.rstrip("\n").split("\n"))
    if n_lines > SPEC_MAX_LINES:
        err("length", f"{n_lines} lines exceeds the {SPEC_MAX_LINES}-line SKILL.md budget; "
                      "move detail into references/")
    elif n_lines > SPEC_MAX_LINES * 0.7 and not (skill_dir / "references").is_dir():
        warn("progressive-disclosure",
             f"{n_lines} lines but no references/ dir to defer detail into")
    return out


def verify_all(root: Path, strict_spec: bool = False) -> Dict[str, Any]:
    """Walk root recursively; every dir with a SKILL.md is one skill.

    strict_spec promotes official-spec violations (bad name, name!=dirname,
    over-length SKILL.md) from advisory to failure.
    """
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
    spec_errors = 0
    spec_warnings = 0
    for skill_file in sorted(root.rglob("SKILL.md")):
        skill_dir = skill_file.parent
        ok, errors, info = verify_skill(skill_dir)
        spec = info.get("spec", [])
        violations = [s for s in spec if s["severity"] == "error"]
        spec_warnings += len([s for s in spec if s["severity"] == "warn"])
        if strict_spec:
            for v in violations:
                errors.append(f"[spec:{v['check']}] {v['detail']}")
            ok = len(errors) == 0
        spec_errors += len(violations)
        results.append({
            "ok": ok,
            "errors": errors,
            "spec_violations": violations,
            "info": info,
        })
    return {
        "format": "aether-skills-verified",
        "version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "root": str(root),
        "strict_spec": strict_spec,
        "total": len(results),
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "spec_errors": spec_errors,
        "spec_warnings": spec_warnings,
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
    p.add_argument("--path", default=None, help="Root dir to scan (default: repo 'skills/' or user config skills/)")
    p.add_argument("--json", action="store_true", help="Print manifest JSON to stdout")
    p.add_argument("--manifest", metavar="PATH", default=None, help="Write verified-manifest JSON to PATH")
    p.add_argument("--no-fail", action="store_true", help="Exit 0 even when skills fail (report-only)")
    p.add_argument("--strict-spec", action="store_true",
                   help="Promote official Agent Skills spec violations (name!=dirname, "
                        "over-500-line SKILL.md, illegal name chars) to failures")
    args = p.parse_args(argv)

    # Resolve the scan root: explicit --path wins; otherwise prefer the
    # repo-root "skills/" convention (CI cwd == repo root), falling back to
    # the user config dir for a bare install.
    if args.path:
        root = Path(args.path)
    else:
        cwd_skills = Path.cwd() / "skills"
        root = cwd_skills if cwd_skills.exists() else SKILLS_DIR

    manifest = verify_all(root, strict_spec=args.strict_spec)

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
            if not args.strict_spec:
                for v in s.get("spec_violations", []):
                    print(f"        ~ spec: {v['detail']}")
        print(f"Summary: {manifest['passed']} passed, {manifest['failed']} failed, {manifest['total']} total")
        print(f"Spec conformance: {manifest['spec_errors']} violation(s), "
              f"{manifest['spec_warnings']} warning(s)"
              + ("  [strict]" if args.strict_spec else "  [advisory - use --strict-spec to gate]"))

    # Gate integrity: a missing or empty root must NEVER pass vacuously —
    # "0/0 verified" is a red run, not a green one.
    if manifest["total"] == 0:
        print(f"ERROR: no skills found at {root} — gate FAILS (never passes vacuously)", file=sys.stderr)
        return 1 if not args.no_fail else 0
    if manifest["failed"] > 0 and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Audit SKILL.md files against the official Agent Skills specification
(https://agentskills.io/specification).

Checks enforced:
  1. name present, 1-64 chars, [a-z0-9-] only, no leading/trailing/-- hyphen
  2. name MUST match the parent directory name
  3. description present, 1-1024 chars
  4. SKILL.md body under 500 lines (spec progressive-disclosure budget)
  5. metadata values must be a flat map of string -> string
  6. only spec-recognised top-level keys (unknown keys are ignored per spec,
     but flag them since they usually signal a vendor-specific hack)
  7. progressive disclosure: warn if body is large and there is no references/ dir

Exit code: 0 if no FAILs, 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_LINES = 500
MAX_DESC = 1024
MAX_NAME = 64
MAX_COMPAT = 500

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/root/.config/opencode/skills")


def parse_frontmatter(text):
    """Minimal YAML-subset frontmatter parser (no external deps).

    Handles the shapes real SKILL.md files use: scalars, inline [a, b] lists,
    and one level of nested block maps. Returns (fields, errors).
    """
    if not text.startswith("---"):
        return None, ["missing frontmatter: file does not start with '---'"]
    end = text.find("\n---", 3)
    if end == -1:
        return None, ["unterminated frontmatter"]
    block = text[3:end]
    lines = block.split("\n")
    fields, errors = {}, []
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw[0] in " \t":  # nested block value
            i += 1
            continue
        if ":" not in raw:
            errors.append(f"malformed line: {raw!r}")
            i += 1
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        val = val.strip()
        if val in ("|", ">", "|-", ">-"):  # block scalar
            j = i + 1
            chunk = []
            while j < len(lines) and (not lines[j].strip() or lines[j][0] in " \t"):
                chunk.append(lines[j].strip())
                j += 1
            fields[key] = " ".join(c for c in chunk if c)
            i = j
            continue
        if val == "":  # empty value -> block scalar OR nested map; disambiguate
            j = i + 1
            indented = [l for l in lines[j:] if l.strip()]
            # A nested map's first child looks like `key: value`; a block scalar's
            # does not (prose lines). This is the only ambiguous corner of the
            # YAML subset and it decides empty-vs-populated for `description:`.
            is_map = bool(indented) and indented[0].startswith((" ", "\t")) \
                and ":" in indented[0].strip().split(" ")[0] + ":" \
                and bool(re.match(r"^\s*[A-Za-z_][\w.-]*\s*:", indented[0]))
            if is_map:
                sub = {}
                while j < len(lines) and (lines[j].startswith("  ") or not lines[j].strip()):
                    s = lines[j].strip()
                    if s and ":" in s and not s.startswith("-"):
                        k2, _, v2 = s.partition(":")
                        sub[k2.strip()] = v2.strip()
                    elif s.startswith("-"):
                        sub.setdefault("_list", []).append(s.lstrip("- ").strip())
                    j += 1
                fields[key] = sub
                i = j
                continue
            chunk = []
            while j < len(lines) and (not lines[j].strip() or lines[j][0] in " \t"):
                chunk.append(lines[j].strip())
                j += 1
            fields[key] = " ".join(c for c in chunk if c)
            i = j
            continue
        if val.startswith("["):
            inner = val.strip("[]").strip()
            items = [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
            fields[key] = {"_list": items}
            i += 1
            continue
        fields[key] = val.strip("'\"")
        i += 1
    return fields, errors


def audit_skill(skill_md: Path):
    fails, warns, info = [], [], {}
    dirname = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    body = text.split("\n---", 1)[1] if text.startswith("---") and "\n---" in text[3:] else text
    n_lines = len(text.rstrip("\n").split("\n"))
    info["lines"] = n_lines

    fields, errs = parse_frontmatter(text)
    if fields is None:
        return [{"check": "frontmatter", "detail": e} for e in errs], warns, info
    fails.extend({"check": "frontmatter", "detail": e} for e in errs)

    name = fields.get("name")
    if not isinstance(name, str) or not name:
        fails.append({"check": "name", "detail": "name field missing or not a string"})
    else:
        info["name"] = name
        if len(name) > MAX_NAME:
            fails.append({"check": "name", "detail": f"name is {len(name)} chars (max {MAX_NAME})"})
        if not NAME_RE.match(name):
            bad = [c for c in name if not (c.islower() or c.isdigit() or c == "-")]
            fails.append({
                "check": "name",
                "detail": f"name {name!r} violates [a-z0-9-]; offending chars: {sorted(set(bad))}"
                            + (" (uppercase not allowed)" if name != name.lower() else ""),
            })
        if name != dirname:
            fails.append({
                "check": "name-matches-dirname",
                "detail": f"name {name!r} != directory {dirname!r} (spec requires they match)",
            })

    desc = fields.get("description")
    if not isinstance(desc, str) or not desc.strip():
        fails.append({"check": "description", "detail": "description missing or empty"})
    else:
        if len(desc) > MAX_DESC:
            fails.append({"check": "description", "detail": f"description is {len(desc)} chars (max {MAX_DESC})"})
        if "use when" not in desc.lower():
            warns.append({"check": "description", "detail": "description has no 'Use when' trigger clause"})

    compat = fields.get("compatibility")
    if isinstance(compat, str) and len(compat) > MAX_COMPAT:
        fails.append({"check": "compatibility", "detail": f"compatibility is {len(compat)} chars (max {MAX_COMPAT})"})

    md = fields.get("metadata")
    if md is not None and isinstance(md, dict):
        for k, v in md.items():
            if k == "_list":
                continue
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if k2 == "_list":
                        fails.append({
                            "check": "metadata",
                            "detail": f"metadata.{k}.{k2} is a list; spec requires string->string values",
                        })
                    elif not isinstance(v2, str):
                        fails.append({
                            "check": "metadata",
                            "detail": f"metadata.{k}.{k2} is {type(v2).__name__}; spec requires string values",
                        })
            elif not isinstance(v, str):
                fails.append({
                    "check": "metadata",
                    "detail": f"metadata.{k} is {type(v).__name__}; spec requires string->string",
                })

    unknown = set(fields) - SPEC_KEYS
    if unknown:
        warns.append({"check": "top-level-keys", "detail": f"non-spec keys ignored by loaders: {sorted(unknown)}"})

    if n_lines > MAX_LINES:
        fails.append({
            "check": "length",
            "detail": f"{n_lines} lines exceeds the {MAX_LINES}-line SKILL.md budget; move detail to references/",
        })
    elif n_lines > MAX_LINES * 0.7 and not (skill_md.parent / "references").is_dir():
        warns.append({
            "check": "progressive-disclosure",
            "detail": f"{n_lines} lines but no references/ dir to defer detail into",
        })
    return fails, warns, info


def main():
    skills = sorted(ROOT.rglob("SKILL.md"))
    results, n_fail, n_warn = [], 0, 0
    for md in skills:
        rel = str(md.relative_to(ROOT.parent))
        fails, warns, info = audit_skill(md)
        n_fail += len(fails)
        n_warn += len(warns)
        if fails or warns:
            results.append({"skill": rel, "name": info.get("name"), "lines": info["lines"],
                            "fail": fails, "warn": warns})
    print(json.dumps({
        "spec": "https://agentskills.io/specification",
        "skills_scanned": len(skills),
        "failures": n_fail,
        "warnings": n_warn,
        "skills_with_issues": len(results),
        "results": results,
    }, indent=2))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
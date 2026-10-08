#!/usr/bin/env python3
"""floor-guard.py — diff-scoped guard against weakening a project's own quality bar.

Detects the five moves an agent makes to make its change pass by lowering the
standard instead of meeting it:

  1. THRESHOLD MOVED  a budget lowered / severity dropped / check removed
  2. TEST GOT EASIER  .skip / .only added, test deleted, assertion loosened
  3. CHECKER SILENCED new @ts-ignore / eslint-disable / istanbul ignore /
                     nosemgrep / gitleaks:allow / type: ignore / stryker disable
  4. UNFINISHED       new stub that throws, empty catch, TODO in a claimed body
  5. UNDISCUSSED EXC  new ignore-list entry / exception row in the same diff

Exit codes:
  0  clean
  1  violation(s) found
  2  misconfigured / could not evaluate  (NEVER report this as clean)

Usage:
  floor-guard.py [--base REF] [--allow REGEX] [--quiet] [--format text|json]
                 [--max-file-lines N] [--diff-file PATH]

  --base REF      diff against this ref (default: auto-detect origin/main, then
                  origin/master, main, master, else HEAD~1). Uses the two-dot
                  form, so uncommitted work in the tree is guarded too.
  --allow REGEX   skip a finding whose file path matches; repeatable. Always
                  pair with an inline comment explaining the narrow reason.
  --diff-file     read a unified diff from a file instead of git (for tests/CI
                  fixtures)
  --format json   machine-readable output for CI annotations

Stdlib only. Requires git in PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict

MAX_FILE_LINES = 2_000_000  # refuse to slurp pathological inputs

# --- Finding 1: thresholds that moved downward -------------------------------
# Config-ish files where a numeric or severity value lowering matters.
THRESHOLD_FILES = re.compile(
    r"(^|/)(codecov\.yml|\.nycrc|\.codecov\.(yml|yaml)|jest\.config\.[jt]s|"
    r"vitest\.config\.[jt]s|karma\.conf\.[jt]s|"
    r"\.eslintrc[.\w]*|eslint\.config\.[cm]?[jt]s|\.stylelintrc[.\w]*|"
    r"pyproject\.toml|ruff\.toml|\.flake8|setup\.cfg|tox\.ini|"
    r"Cargo\.toml|clippy\.toml|deny\.toml|"
    r"size-limit\.[jt]s|\.size-limit\.[jt]s|.*\.size-limit\.json|"
    r"lighthouserc[.\w]*|\.lighthouserc[.\w]*|"
    r"stryker\.config\.[jt]s|stryker\.[jt]s|.*ratchet\.ya?ml)$"
)
# (name, regex for the whole line, group holding the value)
NUMERIC_KEYS = [
    ("statements", r"(?:statements|lines|branches|functions|lines_pct)\s*[:=]\s*(\d+)"),
    ("threshold", r"threshold\s*[:=]\s*[\"']?(\d+)"),
    ("budget", r"(?:maxSize|max_size|budget|sizeLimit)\s*[:=]\s*[\"']?(\d+)"),
    ("lcp", r"\b(?:largest-contentful-paint|lcp)[^\n]{0,40}?(\d{3,6})"),
    ("cls", r"\bcumulative-layout-shift[^\n]{0,40}?(0?\.\d+)"),
    ("severity", r"severity\s*[:=]\s*[\"']?(critical|high|moderate|medium|low)\b"),
    ("pct", r"pct\s*[:=]\s*[\"']?(\d+)"),
]
SEVERITY_RANK = {"low": 1, "moderate": 2, "medium": 2, "high": 3, "critical": 4}


def _num(s: str):
    try:
        return float(s)
    except ValueError:
        return None


def check_threshold(removed: str, path: str) -> list[str]:
    """A numeric/severity value that got smaller in a config file."""
    if not THRESHOLD_FILES.search(path):
        return []
    hits = []
    for line in removed:
        if line.startswith(("---", "+++")):
            continue
        for name, rx in NUMERIC_KEYS:
            m = re.search(rx, line, re.I)
            if not m:
                continue
            val = m.group(1)
            if name == "severity":
                if SEVERITY_RANK.get(val.lower(), 0) < 3:
                    hits.append(f"severity set to {val!r} (was stricter)")
            else:
                n = _num(val)
                if n is None:
                    continue
                # Removed line = old value. If it looks like a floor/coverage
                # percentage it must not go down; for budgets it must not go up.
                if name in ("statements", "threshold", "pct") and n >= 1:
                    hits.append(f"{name} lowered from {val}")
                elif name in ("budget", "lcp", "cls") and n > 0:
                    hits.append(f"{name} limit relaxed from {val}")
    return hits


# --- Finding 2: tests got easier ---------------------------------------------
TEST_FILES = re.compile(r"(^|/)(tests?|spec|__tests__|e2e)/|(^|/).*\.(test|spec)\.[jt]sx?$")
ASSERT_RX = re.compile(r"\b(?:assert|expect\s*\(|assertEquals|assertThat|toBe|toEqual|"
                       r"toThrow|should\s*\(|toStrictEqual)\b")
EASIER_TESTS = [
    ("test skipped", re.compile(r"^\+\s*(?:.*\b(?:it|test|describe)\s*\.\s*skip\b|"
                                r".*\b(?:xdescribe|xit|xcontext)\s*\(|"
                                r".*\bfdescribe\b|.*\bfit\b|.*#\s*\[Ignore|"
                                r".*@Ignore|.*\bpytest\.mark\.skip|.*\bt\.Skip\b)")),
    ("assertion loosened", re.compile(r"^\+.*\b(?:toBeTruthy|toBeDefined|toBeFalsy|"
                                      r"toBeGreaterThanOrEqual|toBeLessThanOrEqual|"
                                      r"assert\.ok|assert\.truthy|startswith\b|contains\b)")),
]


def _is_test_file(path: str) -> bool:
    return bool(TEST_FILES.search(path))


def check_test(path: str, removed: list[str], added: list[str]) -> list[str]:
    """Report only when this diff is touching test code."""
    if not _is_test_file(path):
        return []
    hits = []
    for line in added:
        for label, rx in EASIER_TESTS:
            if rx.match(line):
                hits.append(label)
    for line in removed:
        if re.match(r"^-\s*(?:def\s+test_|async\s+def\s+test_)", line) or \
           re.match(r"^-\s*(?:.*\b(?:it|test|testEach|test\.)\s*\(|.*@Test\b)", line):
            hits.append("test deleted")
        if ASSERT_RX.search(line):
            hits.append("assertion removed")
    # An expected value weakened to a status class / loose range.
    for line in added:
        if ASSERT_RX.search(line) and re.search(r"\b[1-5]\d\d\b\s*[),;]?\s*$", line) \
           and not re.search(r"\b(?:toBe|toEqual|toStrictEqual)\s*\(\s*[1-5]\d\d\s*\)", line):
            hits.append("expected value loosened to a loose range")
    return sorted(set(hits))


def check_deleted_test_files(removed_files: set[str]) -> list[Finding]:
    out = []
    for f in sorted(removed_files):
        if _is_test_file(f) or re.search(r"(^|/)(tests?|spec|__tests__)/", f):
            out.append(Finding("test-got-easier", f, "test file deleted"))
    return out


# --- Finding 3: the checker got silenced --------------------------------------
SUPPRESSIONS = [
    ("ts-ignore", re.compile(r"^\+.*@ts-(?:ignore|expect-error|nocheck)\b")),
    ("type-ignore", re.compile(r"^\+.*(?:#|//)\s*type:\s*ignore\b")),
    ("eslint-disable", re.compile(r"^\+.*eslint-disable(?:-next-line|-line)?")),
    ("biome-ignore", re.compile(r"^\+.*(?:biome-ignore|biome-ignore-file)")),
    ("istanbul ignore", re.compile(r"^\+.*istanbul\s+ignore\b")),
    ("c8 ignore", re.compile(r"^\+.*c8\s+ignore\b")),
    ("nosemgrep", re.compile(r"^\+.*\bnosemgrep\b")),
    ("gitleaks allow", re.compile(r"^\+.*gitleaks:allow\b")),
    ("ruff noqa", re.compile(r"^\+.*#\s*noqa\b")),
    ("pylint disable", re.compile(r"^\+.*#\s*pylint:\s*disable")),
    ("nolint", re.compile(r"^\+.*\bnolint\b")),
    ("stryker disable", re.compile(r"^\+.*\bstryker\s+disable\b")),
    ("bandit skip", re.compile(r"^\+.*#\s*(?:nosec|noqa\s*:\s*S\d+)")),
    ("coverage ignore", re.compile(r"^\+.*(?:LCOV_EXCL|pragma:\s*no\s*cover|/\*\s*istanbul\s+ignore)")),
]
SUPPRESSION_NOTES = {
    "istanbul ignore": "removes the code from coverage rather than testing it",
    "c8 ignore": "removes the code from coverage rather than testing it",
    "nosemgrep": "disables a security finding",
    "gitleaks allow": "disables a secret-scanner finding",
    "stryker disable": "hides a surviving mutant",
    "coverage ignore": "removes the code from coverage rather than testing it",
}


def check_suppressions(added: list[str]) -> list[str]:
    hits = []
    for line in added:
        for label, rx in SUPPRESSIONS:
            if rx.match(line):
                note = SUPPRESSION_NOTES.get(label)
                hits.append(f"{label}{' — ' + note if note else ''}")
    return sorted(set(hits))


# --- Finding 4: work is unfinished --------------------------------------------
STUBS = [
    ("stub that throws", re.compile(r"^\+.*(?:raise\s+NotImplementedError|throw\s+new\s+"
                                   r"(?:Error|NotImplemented)|todo!\s*\(|unimplemented!\s*\()")),
    ("empty catch", re.compile(r"^\+\s*(?:except[^:]*:\s*)?(?:pass\b|catch\s*\([^)]*\)\s*\{\s*\})")),
    ("swallowed error", re.compile(r"^\+.*(?:except\s*:\s*$|catch\s*\(\s*\)\s*\{\s*\}|\.catch\(\s*\(\s*\)\s*=>\s*(?:\{\}|null))")),
    ("TODO in new code", re.compile(r"^\+.*\b(?:TODO|FIXME|XXX|HACK)\b")),
]


OPENS_BODY = re.compile(r"^\+.*(?:\bfunction\b|=>|\bclass\b|^\+\s*def\b|\{\s*$)")
CLOSES_BODY = re.compile(r"^\+\s*\}")


def check_stubs(added: list[str]) -> list[str]:
    hits = [label for label, rx in STUBS for line in added if rx.match(line)]
    # Empty function/class body: an opening line immediately followed by a close.
    for prev, cur in zip(added, added[1:]):
        if OPENS_BODY.match(prev) and CLOSES_BODY.match(cur):
            hits.append("empty function/class body")
    return sorted(set(hits))


# --- Finding 5: an exception nobody discussed ---------------------------------
IGNORE_LIST_FILES = re.compile(
    r"(^|/)(\.gitignore|\.eslintignore|\.prettierignore|\.dockerignore|"
    r"\.npmignore|\.semgrepignore|semgrepignore|\.git-blame-ignore-revs)$")
EXCEPTION_FILES = re.compile(
    r"(^|/)(CONSTRAINTS\.md|\.constraints-ratchet\.ya?ml|codecov\.yml|\.nycrc|"
    r"\.eslintignore|\.gitignore|\.prettierignore|"
    r"semgrepignore|\.semgrepignore|.*ignore.*)$")
# An Exceptions row must carry an expiry date; Floor/Enforced rows must not.
EXCEPTION_ROW = re.compile(r"^\+\s*\|.*\|.*\|.*\|.*\|.*\|.*\|\s*$")
DATE_CELL = re.compile(r"\b(20\d{2}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2})\b")
IGNORE_EDIT = re.compile(r"\b(?:ignore|exclude|paths-ignore|allow|skip|suppress)\b", re.I)


def check_exceptions(path: str, added: list[str]) -> list[str]:
    hits = []
    if not EXCEPTION_FILES.search(path):
        return hits
    is_constraints = path.endswith("CONSTRAINTS.md")
    # In a pure ignore list, every added pattern is an exclusion.
    is_ignore_list = bool(IGNORE_LIST_FILES.search(path))
    for line in added:
        body = line[1:].strip()
        if not body or body.startswith("#") or body.startswith("+"):
            continue
        if is_constraints:
            # A 5-column row containing a date is an Exceptions row.
            if EXCEPTION_ROW.match(line) and DATE_CELL.search(line):
                hits.append("new Exceptions row added in the same diff")
        elif is_ignore_list or IGNORE_EDIT.search(body):
            hits.append("new exclusion/ignore entry in the same diff")
    return sorted(set(hits))


# --- diff plumbing -------------------------------------------------------------
@dataclass
class Finding:
    rule: str
    file: str
    detail: str


def default_base() -> str | None:
    for ref in ("origin/main", "origin/master", "main", "master"):
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return ref
    # Detached HEAD / no main branch: fall back to the last commit.
    r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD~1"],
                       capture_output=True, text=True)
    return "HEAD~1" if r.returncode == 0 else None


def get_diff(base: str | None, diff_file: str | None) -> tuple[str, int]:
    if diff_file:
        with open(diff_file, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(), 0
    cmd = ["git", "diff", "--no-color", "--unified=0"]
    # Two-dot form on purpose: it compares the working tree against the base, so
    # uncommitted work is guarded too. `base...HEAD` would silently skip it.
    cmd += [base if base else "HEAD"]
    cmd += ["--", "."]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return "", r.returncode
    return r.stdout, 0


def parse_diff(diff: str) -> tuple[dict[str, dict], set[str]]:
    files: dict[str, dict] = {}
    current = None
    removed_files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            m = re.search(r" b/(.+)$", line)
            current = m.group(1) if m else None
            if current:
                files.setdefault(current, {"added": [], "removed": []})
            continue
        if line.startswith("deleted file mode") and current:
            removed_files.add(current)
            continue
        if current is None:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            files[current]["added"].append(line)
        elif line.startswith("-"):
            files[current]["removed"].append(line)
    return files, removed_files


def audit(diff: str, allow: list[str]) -> list[Finding]:
    files, removed_files = parse_diff(diff)
    findings: list[Finding] = []
    allow_rx = [re.compile(a) for a in allow]

    for path, hunks in files.items():
        if any(rx.search(path) for rx in allow_rx):
            continue
        added, removed = hunks["added"], hunks["removed"]
        rules = {
            "threshold-moved": check_threshold(removed, path),
            "test-got-easier": check_test(path, removed, added),
            "checker-silenced": check_suppressions(added),
            "unfinished": check_stubs(added),
            "undiscussed-exception": check_exceptions(path, added),
        }
        for rule, details in rules.items():
            for detail in details:
                findings.append(Finding(rule, path, detail))

    # Whole-diff rules: evaluated once, not once per file.
    if not any(rx.search(f) for rx in allow_rx for f in removed_files):
        findings.extend(check_deleted_test_files(removed_files))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff-scoped quality-bar guard.")
    ap.add_argument("--base", help="diff base ref (default: auto)")
    ap.add_argument("--allow", action="append", default=[],
                    help="regex; findings in matching paths are skipped")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--diff-file", help="read a unified diff from this path")
    ap.add_argument("--max-file-lines", type=int, default=MAX_FILE_LINES)
    args = ap.parse_args()

    if args.diff_file and not os.path.exists(args.diff_file):
        print(f"floor-guard: cannot read --diff-file {args.diff_file!r}", file=sys.stderr)
        return 2

    base = args.base or (None if args.diff_file else default_base())
    if not args.diff_file and base is None and args.base is None:
        print("floor-guard: could not determine a diff base "
              "(tried origin/main, origin/master, main, master). "
              "Pass --base REF or --diff-file. NOT reporting clean.", file=sys.stderr)
        return 2

    diff, rc = get_diff(base, args.diff_file)
    if rc != 0:
        print(f"floor-guard: git diff failed (exit {rc}). NOT reporting clean.",
              file=sys.stderr)
        return 2
    if not diff.strip():
        if not args.quiet:
            print("floor-guard: no diff to inspect — clean.")
        return 0
    if len(diff.splitlines()) > args.max_file_lines:
        print("floor-guard: diff too large to evaluate. NOT reporting clean.",
              file=sys.stderr)
        return 2

    findings = audit(diff, args.allow)

    if args.format == "json":
        print(json.dumps({
            "base": base or args.diff_file,
            "clean": not findings,
            "findings": [asdict(f) for f in findings],
        }, indent=2))
    elif not args.quiet:
        if not findings:
            print(f"floor-guard: clean (base={base or args.diff_file}).")
        else:
            print(f"floor-guard: {len(findings)} finding(s) "
                  f"(base={base or args.diff_file})\n")
            by_file: dict[str, list[Finding]] = {}
            for f in findings:
                by_file.setdefault(f.file, []).append(f)
            for path, fs in sorted(by_file.items()):
                print(f"  {path}")
                for f in fs:
                    print(f"    [{f.rule}] {f.detail}")
                print()
            print("Fix the finding or add a time-boxed Exception row to "
                  "CONSTRAINTS.md. Do not delete the rule.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

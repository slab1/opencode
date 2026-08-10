#!/usr/bin/env python3
"""Bet 9 verification — quality-gated skills hub.

Tests (isolated temp skills tree; real skills/ touched only by a read-only
baseline sanity check):
  1. well-formed skill            -> PASS
  2. stub with honesty marker     -> FAIL (must never be listed)
  3. missing frontmatter          -> FAIL
  4. name != directory            -> PASS with note (layout convention)
  5. block-scalar description     -> PASS (folded continuation lines)
  6. near-empty body              -> FAIL
  7. manifest aggregates + writes parseable JSON, exit codes honored
  8. live inventory sanity: verify_all(skills/) covers all SKILL.md files

Run: python3 scripts/test-skills-verifier.py   (exit 0 = pass)
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.skills_verifier import verify_all, write_manifest

GOOD = """---
name: good-skill
description: Use when testing skill verification round trips. Agent should pass.
---

# Good Skill

Real, substantial body that documents the workflow properly with enough
content to never be confused for a scaffold or placeholder stub.
"""

STUB = """---
name: stub-skill
description: Use when testing stub detection.
---

# Stub Skill

UNVERIFIED-DO-NOT-USE — scaffold only, real implementation pending.
"""


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="aether-skill-test-"))
    try:
        (tmp / "good-skill" / "SKILL.md").parent.mkdir(parents=True)
        (tmp / "good-skill" / "SKILL.md").write_text(GOOD)
        (tmp / "stub-skill" / "SKILL.md").parent.mkdir(parents=True)
        (tmp / "stub-skill" / "SKILL.md").write_text(STUB)
        (tmp / "no-frontmatter" / "SKILL.md").parent.mkdir(parents=True)
        (tmp / "no-frontmatter" / "SKILL.md").write_text("# No Frontmatter\n\njust a body")
        (tmp / "mismatch" / "SKILL.md").parent.mkdir(parents=True)
        (tmp / "mismatch" / "SKILL.md").write_text(
            "---\nname: other-name\ndescription: use when testing mismatch. Agent checks.\n"
            "---\n\n# Header\n\nReal, substantial body that documents the workflow "
            "properly with enough content to never be confused for a stub.")
        (tmp / "block-scalar" / "SKILL.md").parent.mkdir(parents=True)
        (tmp / "block-scalar" / "SKILL.md").write_text(
            "---\nname: block-scalar\ndescription:\n  Multi-line folded description that\n"
            "  spans several lines like the vercel skills do. Agent checks parser.\n"
            "---\n\n## Uses h2 heading only\n\nReal body text with enough content to pass "
            "the minimum body length requirement easily.")
        (tmp / "near-empty" / "SKILL.md").parent.mkdir(parents=True)
        (tmp / "near-empty" / "SKILL.md").write_text(
            "---\nname: near-empty\ndescription: short. Agent checks.\n---\n\n# Header")

        m = verify_all(tmp)
        by_name = {s["info"]["name"]: s for s in m["skills"]}
        assert m["total"] == 6, m["total"]
        assert by_name["good-skill"]["ok"], by_name["good-skill"]
        assert not by_name["stub-skill"]["ok"], by_name["stub-skill"]["errors"]
        assert not by_name["no-frontmatter"]["ok"]
        assert by_name["other-name"]["ok"] and "!= directory" in by_name["other-name"]["info"]["note"]
        assert by_name["block-scalar"]["ok"], by_name["block-scalar"]
        assert by_name["block-scalar"]["info"]["desc_len"] > 10
        assert "no '# Title' heading" in by_name["block-scalar"]["info"]["note"]
        assert not by_name["near-empty"]["ok"]
        assert m["passed"] == 3 and m["failed"] == 3, (m["passed"], m["failed"])

        # manifest write parses back
        out = tmp / "manifest.json"
        write_manifest(m, out)
        reloaded = json.loads(out.read_text())
        assert reloaded["format"] == "aether-skills-verified" and reloaded["total"] == 6

        # CLI exit code honors failures (expect rc=1) and --no-fail (rc=0)
        r1 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "skills-verify",
             "--path", str(tmp), "--json"],
            capture_output=True, text=True, timeout=60)
        assert r1.returncode == 1, "expected rc=1 with failures"
        r2 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "skills-verify",
             "--path", str(tmp), "--json", "--no-fail"],
            capture_output=True, text=True, timeout=60)
        assert r2.returncode == 0, "expected rc=0 with --no-fail"

        # Vacuous-pass guard: missing root (0/0 must FAIL, never silently pass)
        r3 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "skills-verify",
             "--path", str(tmp / "does-not-exist"), "--json"],
            capture_output=True, text=True, timeout=60)
        assert r3.returncode == 1, "expected rc=1 on missing root (vacuous pass guard)"
        assert "never passes vacuously" in r3.stderr
        r4 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "skills-verify",
             "--path", str(tmp / "does-not-exist"), "--json", "--no-fail"],
            capture_output=True, text=True, timeout=60)
        assert r4.returncode == 0, "expected rc=0 with --no-fail even on missing root"

        # Repo-root convention: running from the opencode config dir with no
        # --path must resolve to the real skills/ tree (CI parity).
        r5 = subprocess.run(
            [sys.executable, "-m", "opencode_improvement", "skills-verify",
             "--manifest", str(tmp / "ci-manifest.json")],
            cwd=str(Path.home() / ".config" / "opencode"),
            capture_output=True, text=True, timeout=120)
        assert r5.returncode == 0, r5.stderr
        ci_m = json.loads((tmp / "ci-manifest.json").read_text())
        assert ci_m["total"] > 100 and ci_m["failed"] == 0, (ci_m["total"], ci_m["failed"])

        # live inventory sanity (read-only)
        real = verify_all(Path.home() / ".config" / "opencode" / "skills")
        n_files = len(list((Path.home() / ".config" / "opencode" / "skills").rglob("SKILL.md")))
        assert real["total"] == n_files, f"{real['total']} != {n_files}"
        print(f"PASS: skills verifier tests green "
              f"(live inventory: {real['total']} skills, "
              f"{real['passed']} passed, {real['failed']} failed)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
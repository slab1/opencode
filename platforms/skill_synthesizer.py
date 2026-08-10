"""Project Aether: Dynamic Capability Synthesis (DCS) — HONEST scaffold mode.

Synthesizes skill skeletons that are explicitly marked **UNVERIFIED-DO-NOT-USE**
until a human provides a real implementation:

- A synthesized ``tool.py`` raises ``NotImplementedError`` with a clear message
  instead of a print stub that pretends to work.
- The generated ``SKILL.md`` carries a mandatory ``## Human Review Required``
  section stating the tool has no verified implementation.
- ``_validate_skill()`` reports a ``NotImplementedError`` tool as ``unverified``
  (never ``success``).
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

# Paths
BASE_DIR = Path.home() / ".config" / "opencode"
SKILLS_DIR = BASE_DIR / "skills" / "skills"
# For synthesized skills, we'll use a dedicated 'synthesized' category to avoid cluttering core categories
SYNTH_CAT = SKILLS_DIR / "synthesized"

UNVERIFIED_MARKER = "UNVERIFIED-DO-NOT-USE"


class SkillSynthesizer:
    """
    Project Aether: Dynamic Capability Synthesis (DCS).
    Researches and creates new skills when a capability gap is detected.
    """

    def __init__(self):
        SYNTH_CAT.mkdir(parents=True, exist_ok=True)

    def synthesize_skill(
        self,
        capability_gap: str,
        target_behavior: str,
        scaffold: bool = True,
        implementation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main pipeline: Research -> Implementation -> Documentation -> Validation.

        Args:
            capability_gap: The capability the skill should fill.
            target_behavior: The behavior the skill should achieve.
            scaffold: If True (default), produce an UNVERIFIED skeleton that
                requires human review. This is the honest default: without a
                real implementation there is nothing to verify.
            implementation: Optional real ``tool.py`` source. When provided it
                is used verbatim; otherwise the tool raises NotImplementedError.

        Returns:
            dict with skill name, status ("success" | "unverified" |
            "failed_validation"), and artifact paths.
        """
        print(f"Synthesizing capability: {capability_gap}...")

        # 1. Research (honest: no fabricated findings)
        research_notes = self._conduct_research(capability_gap, target_behavior)

        # 2. Implementation
        skill_name = self._slugify(capability_gap)
        tool_path = SYNTH_CAT / skill_name / "tool.py"
        tool_path.parent.mkdir(parents=True, exist_ok=True)

        tool_code = self._generate_implementation(skill_name, research_notes, implementation=implementation)
        tool_path.write_text(tool_code)

        # 3. Documentation (Following hermes-agent-skill-authoring)
        skill_md_path = SYNTH_CAT / skill_name / "SKILL.md"
        skill_md = self._generate_skill_md(
            skill_name, capability_gap, target_behavior, research_notes, scaffold=scaffold
        )
        skill_md_path.write_text(skill_md)

        # 4. Validation
        status = self._validate_skill(tool_path, target_behavior)

        return {
            "skill_name": skill_name,
            "status": status,
            "verified": status == "success",
            "paths": {
                "tool": str(tool_path),
                "md": str(skill_md_path),
            },
            "research_summary": research_notes,
        }

    def _conduct_research(self, gap: str, behavior: str) -> str:
        """Honest research: we do not fabricate findings.

        Returns a note stating that no verified research was performed, so the
        scaffold cannot claim an implementation basis.
        """
        return (
            f"No verified research was performed for '{gap}'. "
            f"Target behavior: {behavior}. A human must supply the real "
            f"implementation and validation before this skill is usable."
        )

    def _generate_implementation(
        self, name: str, notes: str, implementation: Optional[str] = None
    ) -> str:
        """Generate ``tool.py``.

        If a real implementation is provided, use it verbatim. Otherwise emit
        a tool that raises ``NotImplementedError`` with a clear message — never
        a print stub that pretends to work.
        """
        if implementation:
            return implementation
        return f'''"""{name} — {UNVERIFIED_MARKER}

This tool has NO verified implementation. It is a scaffold produced by the
Aether SkillSynthesizer and MUST NOT be used until a human implements and
validates the real logic.

Research notes (unverified): {notes}
"""


def main():
    raise NotImplementedError(
        "{name} is an {UNVERIFIED_MARKER} scaffold. "
        "Implement the real logic and remove this raise before use."
    )


if __name__ == "__main__":
    main()
'''

    def _generate_skill_md(
        self, name: str, gap: str, behavior: str, notes: str, scaffold: bool = True
    ) -> str:
        """Generate SKILL.md with an explicit human-review gate."""
        status_line = f"status: {UNVERIFIED_MARKER}" if scaffold else "status: verified"
        review_section = f"""## Human Review Required

This skill is an **{UNVERIFIED_MARKER}** scaffold. The tool has **no verified
implementation** — `tool.py` raises `NotImplementedError` on purpose.

Before this skill may be used:

- [ ] A human must implement the real logic in `tool.py`.
- [ ] The implementation must be validated against the target behavior.
- [ ] The `status` field in the frontmatter must be changed to `verified`.
- [ ] This section must be removed.
"""
        return f'''---
name: {name}
description: Use when {gap}. {behavior}.
version: 0.1.0
author: Aether-Synthesizer
license: MIT
{status_line}
metadata:
  hermes:
    tags: [synthesized, aether, unverified]
    related_skills: []
---

# {name.replace("-", " ").title()}

## Overview
This skill was scaffolded by Project Aether to fill a capability gap.
Target behavior: {behavior}

## When to Use
- Use when {gap} is required.
- Do not use for tasks already covered by core platform tools.
- **Do not use this skill yet** — it is unverified.

## Implementation Details
The functionality is intended to live in `tool.py`. Current state:
{notes}

{review_section}
'''

    def _validate_skill(self, tool_path: Path, behavior: str) -> str:
        """Validate a synthesized skill.

        Returns:
            "success" — the tool ran and exited 0.
            "unverified" — the tool raised NotImplementedError (scaffold).
            "failed_validation" — the tool failed for any other reason.
        """
        try:
            result = subprocess.run(
                ["python3", str(tool_path)], capture_output=True, text=True, timeout=10
            )
        except Exception:
            return "failed_validation"
        if result.returncode == 0:
            return "success"
        if "NotImplementedError" in result.stderr:
            return "unverified"
        return "failed_validation"

    def _slugify(self, text: str) -> str:
        return text.lower().replace(" ", "-").replace("_", "-")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthesize a skill scaffold (UNVERIFIED until human review)."
    )
    parser.add_argument("capability_gap", help="The capability gap to fill")
    parser.add_argument("target_behavior", help="The target behavior the skill should achieve")
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Produce an UNVERIFIED skeleton requiring human review (default behavior)",
    )
    parser.add_argument(
        "--implementation",
        default=None,
        help="Path to a real tool.py implementation to use verbatim (optional)",
    )
    args = parser.parse_args(argv)

    implementation = None
    if args.implementation:
        impl_path = Path(args.implementation)
        if not impl_path.exists():
            print(f"Error: implementation file not found: {impl_path}")
            return 1
        implementation = impl_path.read_text()

    synthesizer = SkillSynthesizer()
    res = synthesizer.synthesize_skill(
        args.capability_gap,
        args.target_behavior,
        scaffold=True,
        implementation=implementation,
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
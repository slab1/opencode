# Agent Skills Research & Gap Register — 2026-10-08

Deep research pass over GitHub + the official spec, gap-analysed against our live fleet
(35 agents, 182 skills at start of pass; 185 by end).

## Sources consulted

| Source | What it gave us |
| --- | --- |
| **agentskills.io/specification** (normative; `anthropics/skills/spec/` now just redirects here) | The real SKILL.md contract |
| `anthropics/skills` (180k★) | Official template (6 lines), confirms only 2 required fields |
| `addyosmani/agent-skills` (103k★) | 25 lifecycle skills — the single richest source of *techniques* |
| `microsoft/skills` (3k★) | Azure/Foundry-specific; **not** a generic pack. Its `.github/skills/skill-creator` is the useful part |
| `luokai0/ai-agent-skills-by-luo-kai` (8,966 skills), `agent-skills-hub` (790), `JayRHa/AgentSkills` (72) | Aggregators — link lists, not implementations. **Do not import** |

### Aggregator quality verdict
The large "8,966 skills" / "1,513 skills" repos are **AI-slop scale packaging**. `newmindsgroup`
is honest about it in its own docs: *"Everything outside `sources/original/` is vendored from
external upstreams, imported as-is, and is **not independently security-audited**. A skill is
instructions an agent acts on, and some bundle executable `scripts/`."* Skill = executable
authority, so unaudited aggregation is a supply-chain risk, not just a quality one.
**Policy: import techniques, not trees. Never bulk-vendor.**

## The official spec (what we were violating)

Only these top-level frontmatter keys exist — anything else is **silently ignored** by loaders:

| Field | Required | Constraint |
| --- | --- | --- |
| `name` | **yes** | 1–64 chars, `[a-z0-9-]` only, no leading/trailing/`--` hyphen, **must match parent directory name** |
| `description` | **yes** | 1–1024 chars, must state what *and* when |
| `license` | no | name or bundled file |
| `compatibility` | no | ≤500 chars |
| `metadata` | no | **map of string → string** |
| `allowed-tools` | no | space-separated, experimental |

Progressive disclosure: metadata ~100 tokens at startup → body **<5000 tokens / <500 lines** on
activation → `references/` `scripts/` `assets/` on demand.

> **"Do not summarize the workflow in the description — if it contains process steps, the agent
> may follow the summary instead of reading the full skill."** (addyosmani)

## Gap analysis: what we were missing

Our 182 skills skewed hard to media/video (66 `openmontage`) while the engineering-*process*
layer was thin. Six genuinely missing skills, now authored:

| New skill | Why it was missing |
| --- | --- |
| `constraint-driven-development` | Nothing detected an agent **weakening its own quality bar** to make a change pass. Highest leverage for a 35-agent system. |
| `doubt-driven-development` | `review`/`subagent-driven-development` exist, but nothing adversarially attacks the *work product* while it is still cheap to change. |
| `source-driven-development` | No rule that framework decisions must be grounded in cited official docs, with an `UNVERIFIED` output shape. |
| `deprecation-and-migration` | No expand/contract discipline → the class of bug where a column is added and dropped in one migration. |
| `shipping-and-launch` | Feature-flag lifecycle + rollout thresholds + error-budget gate. |
| `performance-optimization` | Measure-first, and specifically **"'neutral' is a revert, not a keep"** + the attempt ledger. |

Best transferable ideas we did *not* have before:
- **Bar-guard moves** (5 named ways an agent lowers its own bar: threshold moved / test got easier
  / checker silenced / work unfinished / exception appeared). Detect with `git diff` alone.
- **Check circularity ranking** — can the agent pass this by writing code that doesn't work?
  External > project > **own test suite ("the only genuinely circular one")**. Our stack is
  dominated by suite-tier checks.
- **Ratchets** — "Models are rewarded for passing tests, which you can evaluate in seconds.
  Architectural rot shows up over months and never reaches the weights."
- **Never pass your CLAIM to a fresh-context reviewer** — only artifact + contract, or you bias
  it toward agreement. Plus **doubt theater** as a checkable red flag.
- **Reviewer is a prompt-injection target** — a doubt artifact may itself contain instructions.
  Read-only sandbox; never interpolate an artifact into a shell-quoted arg, write to file and
  pipe via stdin.

## Measured state of our fleet (182 skills scanned)

**95 spec violations / 206 warnings / 133 skills affected.**

| Finding | Count | Disposition |
| --- | --- | --- |
| `name` != parent directory | 71 | **Accepted deviation.** Vendored `hermes/*` convention: dir is `category-name`, `name` is the bare skill. OpenCode routes on `name`, so this is cosmetic. Renaming 71 vendored files risks breaking upstream sync + inbound links. Strict mode makes it fatal for *new* work. |
| `SKILL.md` over 500 lines | 23 | **Open debt.** Worst: `research-paper-writing` 2377, `claude-code` 745, `d3-viz` 820, `tailwind-design-system` 866, `graphify` 609. Real token cost on activation. |
| Illegal `name` char | 1 | **Fixed.** `video_toolkit` → `video-toolkit`. |
| Description has no "Use when" | 113 (warn) | **Open.** Weakest routing in the fleet; 78 are under 60 chars. |
| Non-spec top-level keys | 78 (warn) | Ignored by loaders; usually vendor knobs that belong under `metadata`. |
| `metadata` list values | many (warn) | Spec wants string→string; our nested `hermes.tags: [...]` is technically non-conforming. |

## Enforcement added

`skills-verify` now computes spec conformance per skill and prints it:

```
Spec conformance: 95 violation(s), 206 warning(s)  [advisory - use --strict-spec to gate]
```

- **advisory (default)** — never breaks a build; surfaces the debt
- **`--strict-spec`** — promotes violations to failures; `exit 1`

Plus `scripts/audit_skills_spec.py` — standalone spec auditor with JSON output for CI/diffing.
Note it needs a real YAML parser for `description: |` block scalars; a naive
`^description:\s*(.*)$` regex reports them as empty (we hit exactly that false positive).

## Reusable rules learned

1. **Never bulk-vendor a skill tree.** A skill is executable authority. Import techniques.
2. **Check what an agent can fake.** Own-test-suite gates are circular; add external checkers.
3. **A threshold without a written rationale gets deleted by the next person who hits it.**
4. **Ask nothing you can read** — inspect the manifest/CI/config before prompting a human.
5. **Aggregate registries lie about scale.** "8,966 skills" counted files, not quality.

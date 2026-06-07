---
name: documentation-skeleton
description: Standardized templates and patterns for README, CHANGELOG, API docs, and architecture decision records. Use when the docs agent or any other agent needs to write user-facing documentation. Ensures consistent structure, discoverability, and the right level of detail for each doc type.
license: MIT
compatibility: opencode>=1.16.0
---

# Documentation Skeleton

Provide **consistent, scannable, useful documentation** across all agent output. The goal is docs that someone can read in 30 seconds to understand, and in 5 minutes to act on.

## Doc-type decision tree

```
Need to document code?
├── User-facing project?         → README + CHANGELOG + ARCHITECTURE
├── Public API?                  → API reference (auto-generated preferred)
├── Major decision made?         → ADR (Architecture Decision Record)
├── Single feature/module?       → Module docstring + README in module dir
├── Internal process?            → RUNBOOK
└── Onboarding?                  → TUTORIAL
```

## Templates

### README.md

```markdown
# <Project Name>

<One-sentence description: what it does, who it's for>

## Why
<2-3 sentences on the problem it solves>

## Quick start
<5-line copy-pasteable example>

## Install
<Step-by-step with prerequisites>

## Usage
<Common tasks, not exhaustive — link to docs/ for full reference>

## Architecture
<Brief diagram or 1-paragraph explanation>

## Contributing
<How to submit issues, PRs, run tests>

## License
<SPDX identifier>
```

### CHANGELOG.md (Keep a Changelog format)

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- <new feature>

### Changed
- <change in existing functionality>

### Deprecated
- <soon-to-be removed feature>

### Removed
- <now removed feature>

### Fixed
- <bug fix>

### Security
- <vulnerability fix>
```

### ADR (Architecture Decision Record)

```markdown
# ADR-NNNN: <Title>

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
**Date:** YYYY-MM-DD
**Deciders:** <who was involved>

## Context
<What is the issue we're seeing that motivates this decision?>

## Decision
<What is the change we're proposing or have agreed to implement?>

## Consequences
<What becomes easier? What becomes harder?>

## Alternatives considered
<What other options were on the table? Why weren't they chosen?>
```

### RUNBOOK

```markdown
# Runbook: <Procedure Name>

## When to use
<Trigger conditions>

## Prerequisites
<What must be in place>

## Steps
1. <Step with expected output>
2. <Step with expected output>
3. ...

## Verification
<How to confirm it worked>

## Rollback
<How to undo>

## Escalation
<Who to call, what to tell them>
```

## Style rules

- **Imperative voice** for instructions ("Run the test", not "The test should be run")
- **Code blocks for everything runnable** — no inline `code` for multi-line commands
- **One H1 per file** — the title
- **No "Introduction" or "Overview" sections** — be specific
- **Examples before explanations** — show, then tell
- **Link liberally** — to source, related docs, external references
- **Date everything** — especially ADRs and CHANGELOG entries
- **No marketing speak** — describe what it does, not why it's "amazing"

## Anti-patterns to flag

- "Getting Started" without prerequisites
- Code blocks without expected output
- "TODO: write this" left in committed docs
- Documenting what code does (read the code) instead of why (read the doc)
- Walls of text without headings

## When to use

- `docs` agent creating new project documentation
- Any agent creating a README, CHANGELOG, or ADR
- `meta-agent` when adding a new skill or major config change (write an ADR)
- `pioneer` when researching a new technology (write a research note in this format)

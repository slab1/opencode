---
name: git-commit-hygiene
description: Conventional Commits and clean git history for the build, refactor, and meta-agent. Use when committing changes, generating commit messages, or reviewing PRs. Enforces 50/72 character rules, type prefixes, and single-concern commits to make history readable and automatable.
license: MIT
compatibility: opencode>=1.16.0
---

# Git Commit Hygiene

Produce **clean, automatable, scannable git history** that humans and tools can both read.

## The rules

### 1. Conventional Commits format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types** (lowercase):
- `feat` — new user-visible feature
- `fix` — bug fix
- `refactor` — code change that neither fixes a bug nor adds a feature
- `perf` — performance improvement
- `test` — add or correct tests
- `docs` — documentation only
- `build` — build system, CI, dependencies
- `chore` — tooling, config, non-code changes
- `style` — formatting, whitespace (no code change)
- `revert` — revert a previous commit

**Scope** (optional, in parens): the module, file, or feature affected
- `feat(auth):` — auth module
- `fix(api):` — API layer
- `chore(deps):` — dependencies

**Subject**: imperative mood, no period, no capitalization of first word
- GOOD: `add user registration endpoint`
- BAD:  `Added user registration endpoint.`

### 2. Length limits

- **Subject line: 50 characters max** (hard limit)
- **Body wrap: 72 characters per line** (soft limit)
- **Total subject + type + scope: 72 characters max** (stretch limit)

If subject exceeds 50, split the change into two commits or shorten the scope.

### 3. Body — what and why, not how

```
fix(api): return 404 for missing resources

Previously, GET /users/:id returned 200 with null body
when the user did not exist, which caused clients to crash
on null dereference.

Return 404 with a structured error body matching RFC 7807.
```

### 4. Footer — refs and breaking changes

```
feat(api)!: switch to cursor-based pagination

BREAKING CHANGE: page-based clients must migrate to cursor API.

Refs: #123, #456
```

### 5. One concern per commit

A commit should be **revertable as a single unit**. If you need to say "and", split it.

## Validation checklist (before commit)

- [ ] Subject ≤ 50 chars?
- [ ] Type prefix present?
- [ ] Imperative mood?
- [ ] No period at end of subject?
- [ ] Body wraps at 72?
- [ ] Footer references issue numbers?
- [ ] `BREAKING CHANGE:` noted for breaking changes?
- [ ] `git diff` shows only what subject describes?

## Anti-patterns to flag

- `wip`, `fix`, `update`, `stuff` as the entire subject
- Mixing refactor + feature in one commit
- Committing `.env`, secrets, or large binaries
- Vague bodies: "fix bug", "update code"
- 500-line commits

## When to use

- Before any `git commit` call from build/refactor/meta-agent
- When reviewing a PR's commit history
- When generating release notes (Conventional Commits → changelog)
- When writing a hook to enforce format

## Integration with build agent

The `build` agent should:
1. Stage only the files described in the change
2. Generate the commit message following these rules
3. Show the user the proposed message before committing
4. Refuse to commit files matching secret patterns

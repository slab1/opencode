# Shared Context System — AGENTS.md

This directory holds cross-agent shared state. Every agent should read `context.json`
before starting work and write back completed work before finishing.

## File Map

| File                | Purpose                                        | Format     |
| ------------------- | ---------------------------------------------- | ---------- |
| `AGENTS.md`         | THIS FILE                                      | markdown   |
| `context.json`      | Cross-agent shared context — READ FIRST        | JSON       |
| `commitments.json`  | Track cross-agent commitments                  | JSON Array  |
| `performance.json`  | Performance tracking data                      | JSON Array  |
| `free-models-guide.md` | Guide to free AI image/video models        | markdown   |
| `helpers/`          | Helper scripts                                  | —          |

## Protocol

1. **Read** `context.json` at session start
2. **Write** completed tasks, new artifacts, and decisions to `context.json` before finishing
3. **Update** `performance.json` via the tracking tool for operations > 30s
4. **Respect** commitments in `commitments.json` — don't duplicate work

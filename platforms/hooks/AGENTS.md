# Hooks System — AGENTS.md

Pre/post publishing hooks for the Platform Manager.

## How It Works

- `post.sh` automatically runs `hooks/pre-post.sh` before posting to each platform
- `post.sh` automatically runs `hooks/post-post.sh` after posting to each platform
- Hooks are **optional** — if a hook file doesn't exist, it's skipped silently
- A hook returning non-zero exit code **aborts the post**

## Available Hooks

| Hook | When | Purpose |
|------|------|---------|
| `pre-post.sh` | Before each platform post | Validation, enrichment, abort |
| `post-post.sh` | After each platform post | Logging, notification, tracking |

## Environment Variables

All hooks receive these env vars:

| Variable | Description |
|----------|-------------|
| `PLATFORM` | Target platform (twitter, linkedin, etc.) |
| `TEXT` | Post text content |
| `MEDIA` | Media file path |
| `SCHEDULE` | ISO datetime or "now" |
| `URL` | Link to attach |
| `HASHTAGS` | Comma-separated hashtags |
| `DRY_RUN` | "true" or "false" |
| `BACKEND` | Configured backend |
| `POST_ID` | (post-post only) Unique post ID |
| `SUCCESS` | (post-post only) "true" or "false" |
| `RESPONSE` | (post-post only) API response snippet |

## Adding New Hooks

1. Create a new script in this directory
2. Make it executable: `chmod +x hooks/your-hook.sh`
3. It will be picked up automatically — no registration needed

## Convention

- File names: `kebab-case.sh`
- Must have `#!/bin/bash` shebang
- Must be executable (`chmod +x`)
- Exit 0 = continue, exit non-zero = abort (for pre-hooks)

---
name: background-subagent
description: Run OpenCode agents in the background for parallel or long-running work. Use when a task takes too long for interactive mode, or when you want to dispatch work and continue with other tasks. Built on `oc-bg` wrapper script and OpenCode v1.16.2's `run --agent` + nohup pattern.
license: MIT
compatibility: opencode>=1.16.0
---

# Background Subagent

Run OpenCode agents in the background so you can continue with other work. Useful for:
- **Long research tasks** that take minutes to hours
- **Parallel work** — dispatch multiple agents, gather results
- **Heartbeat-style periodic checks** that shouldn't block the main session
- **Cron jobs** that need to invoke an agent

## The wrapper

`oc-bg` is at `/home/.config/opencode/scripts/oc-bg.sh` (symlinked to `/usr/local/bin/oc-bg`).

```bash
oc-bg <agent> <message>   # spawn agent in background
oc-bg list                 # show running agents
oc-bg status <id>          # check if still running + tail log
oc-bg log <id>             # tail -f the output
oc-bg kill <id>            # terminate
oc-bg clean                # remove logs of completed agents
```

## Spawning a background agent

```bash
oc-bg pioneer "research latest MCP servers for 2026"
# Output:
#   Background agent started:
#     ID:    1780790000-12345
#     PID:   67890
#     Agent: pioneer
#     Log:   /tmp/oc-bg/1780790000-12345.log
```

The agent runs in a separate `opencode run` process. It writes to its own log file. You can check on it later or in another terminal.

## When to use

- Task is estimated > 5 minutes
- Task is independent of your current work
- You want to dispatch multiple agents in parallel
- Running via cron and want to invoke an agent
- You want to keep the main session interactive

## When NOT to use

- Quick tasks (< 30 seconds) — overhead not worth it
- Tasks that need to share state with the main session — use the `task` tool instead
- Tasks that depend on the current conversation context — use subagent delegation

## Limitations

- The background agent does NOT have access to the calling session's conversation history. Pass any needed context in the message.
- The background agent does NOT share memory with the caller. Use shared context via files.
- Results come back via the log file or shared context. No direct return value.
- **Permission handling**: In non-interactive mode, tool permissions may auto-reject. For background work that needs bash/edit, use `--dangerously-skip-permissions` flag, or use a primary agent (orchestrator, build, plan, pioneer) whose permissions are pre-configured.
- **Subagent fallback**: If you pass a subagent name (general, debug, etc.), opencode falls back to the default primary agent with a warning. This is usually fine but means the agent's persona won't be exactly what you specified.

## Reading results

```bash
oc-bg log <id>             # tail -f live output
oc-bg status <id>          # check if running, get final tail when done
```

Or read the log file directly:
```bash
cat /tmp/oc-bg/1780790000-12345.log
```

## Cleanup

```bash
oc-bg clean   # remove logs of completed agents
```

## Integration

- `orchestrator` — can spawn background agents to parallelize work
- `meta-agent` — can run heartbeat agents in the background
- `pioneer` — can spawn long research tasks in the background
- `heartbeat` — can be invoked via cron + `oc-bg heartbeat "..."`

## Example: parallel research

```bash
# Dispatch three research tasks
oc-bg pioneer "research WebGPU maturity in 2026" &
oc-bg pioneer "research Bun 2.0 features" &
oc-bg pioneer "research local LLM performance on Android" &
wait

# Gather results
for id in $(oc-bg list | grep DONE | awk '{print $2}'); do
    echo "=== $id ==="
    oc-bg log $id
done

# Cleanup
oc-bg clean
```

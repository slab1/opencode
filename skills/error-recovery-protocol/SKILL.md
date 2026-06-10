---
name: error-recovery-protocol
description: Standardized recovery procedure for tool failures, MCP errors, timeouts, and stale state across all agents. Use when a tool returns an error, a command fails, the user reports something broken, or an edit doesn't apply. Reduces churn by providing a single, reliable recovery path.
license: MIT
compatibility: opencode>=1.16.0
---

# Error Recovery Protocol

When something goes wrong, **follow this protocol before retrying or escalating**. The goal is to recover quickly without thrashing.

## The 4-step protocol

### Step 1: Classify the error

Match the error to one of these categories:

| Category | Symptom | First action |
|----------|---------|--------------|
| **Stale read** | "oldString not found", "Found multiple matches" | Re-read the file fully, re-apply |
| **Permission denied** | "permission denied", "ask before X" | Check `bash`/`edit`/`read` permission syntax; do not retry blindly |
| **MCP failure** | "tool not found", "MCP server unavailable" | Check MCP server status, restart if needed, retry once |
| **Network/timeout** | "request timed out", "connection reset" | Retry once with backoff; if persistent, fall back to cached/local data |
| **Out of memory** | "can't allocate", OOM, Bun crash | Reduce batch size, free memory, restart with `ulimit -v 800000` |
| **Stale context** | Wrong dates, outdated info, references missing | Run `oc-doctor`, check `shared/context.json`, reload |
| **Logic error** | "expected X got Y" but no tool failure | Read source code, verify assumption, do not retry the same call |

### Step 2: Apply the standard recovery

**For Stale read (most common)**:
1. Re-read the target file with `read` tool — capture full content
2. If edit is multi-line, capture line numbers and content snippets
3. For complex edits, consider `hash-anchored-edits` skill pattern
4. Re-apply the edit with the updated content

**For Permission denied**:
1. Check the relevant section in `agents/<name>.md` frontmatter
2. Verify glob pattern syntax
3. If genuinely blocked, escalate to user with specific request

**For MCP failure**:
1. Check `opencode.jsonc` — is the MCP enabled?
2. Verify credentials (Supabase needs `SUPABASE_ACCESS_TOKEN`, Higgsfield needs OAuth)
3. Try the call once more
4. If still failing, document in shared context and use an alternative tool

**For Network/timeout**:
1. Wait 5s, retry once
2. If still failing, fall back to: cached `webfetch` content, alternate source, or local data
3. Log the failure in `findings` for that agent

**For Out of memory** (Android/Bun):
1. Check available memory: `cat /proc/meminfo | grep -E "MemAvailable|MemFree"`
2. Set `ulimit -v 800000` (or lower) before next launch
3. Reduce concurrent operations
4. Restart opencode if needed

### Step 3: Log the recovery

After recovering, record what happened in shared context:
```json
{
  "findings": {
    "<agent>": {
      "errors_recovered": [
        {
          "error_class": "stale_read",
          "tool": "edit",
          "file": "agents/build.md",
          "recovery": "re-read file, re-apply with updated line numbers",
          "took": 2
        }
      ]
    }
  }
}
```

### Step 4: Prevent recurrence

If the same error happened 2+ times, update the relevant agent's `<rules>` to prevent it:
- Add: "Always re-read file fully before edit operations"
- Add: "Check `python3 -m opencode_improvement audit` before claiming health"
- Add: "Verify X exists before calling Y"

## Anti-patterns to avoid

- **Retry spam** — Don't loop the same failed call 5 times
- **Silent fallback** — Don't switch tools without telling the user
- **Error masking** — Don't catch and rethrow as a generic error
- **State amnesia** — Don't lose the original error context

## Integration with debug agent

The `debug` agent should use this protocol for all investigation. The `debug-systematic-investigation` skill is the high-level strategy; this protocol is the low-level recovery procedure.

## Integration with meta-agent

The `meta-agent` should track error recovery patterns and update agent rules when a pattern repeats. Use `python3 -m opencode_improvement track` to log each recovery.


## When to use

Load this skill when:
- The task description matches the patterns described in this skill
- You are uncertain about the recommended approach
- You need a checklist or pattern to follow

## When NOT to use

- The task clearly doesn't match (use a different skill)
- You have a more specific skill for the situation
- The user explicitly requests a different approach

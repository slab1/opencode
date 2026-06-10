---
name: debug-systematic-investigation
description: Systematically investigate bugs and failures by following a hypothesis-driven approach. Trace data flow, test theories with minimal reproductions, isolate root cause before proposing fixes. Use for any non-trivial bug, performance issue, or unexpected behavior.
license: MIT
compatibility: opencode>=1.16.0
---

# Debug: Systematic Investigation

A **hypothesis-driven** approach to debugging. Never guess. Always reproduce, then isolate.

## The Method (RBIER)

### 1. Reproduce
- Find the **minimal** inputs that trigger the bug
- If you can't reproduce, gather more context (logs, environment)
- Document the exact steps, environment, expected vs actual

### 2. Bound
- When did this start happening?
- What changed recently? (config, deps, data, traffic)
- Does it affect all users, or specific scenarios?

### 3. Isolate
- Bisect: is it config / code / data / environment?
- Disable features one at a time to find the trigger
- Check logs at the right timestamps (before, during, after)

### 4. Examine
- Read the actual code that runs (not what you think runs)
- Trace data flow: input → processing → output
- Check trust boundaries: who can change what

### 5. Resolve
- Fix the **root cause**, not the symptom
- Add a regression test
- Document the fix and the diagnosis

## Common Anti-Patterns

- **Shotgun debugging**: Changing random things hoping it works
- **Symptom-chasing**: Fixing the visible error without understanding why
- **Cargo-culting**: Copying fixes from similar issues without validating
- **Confirmation bias**: Only looking for evidence that supports your guess

## Tools by Layer

| Layer       | Tools                                        |
|-------------|----------------------------------------------|
| OS          | `dmesg`, `/var/log`, `journalctl`           |
| Process     | `ps`, `top`, `strace`, `ltrace`              |
| Network     | `netstat`, `tcpdump`, `curl -v`, `mtr`      |
| Filesystem  | `lsof`, `inotifywait`, `stat`                |
| Language    | debuggers, REPL, print/logging              |
| Application | structured logs, metrics, traces            |

## Investigation Patterns

### "It works on my machine"
- Compare environment variables, PATH, locales
- Check dependency versions
- Look for case sensitivity in paths
- Check file ownership / permissions

### "It worked yesterday"
- Check git log for recent changes
- Check dependency updates
- Check data changes (corrupted files, schema migrations)
- Check external service status

### "It crashes randomly"
- Look for race conditions
- Check resource exhaustion (memory, file descriptors, connections)
- Check timer/timeout interactions
- Check load patterns (CPU, IO, network)

### "It's slow"
- Profile: CPU-bound vs IO-bound
- Check N+1 queries, missing indexes
- Check network latency, DNS resolution
- Check cache hit/miss rates

## Output Format

When reporting a debug finding:

```json
{
  "id": "debug-1717700000",
  "type": "bug_finding",
  "summary": "API returns 500 on retry after timeout",
  "reproduction": "POST /api/x with retry-after timeout, then immediate retry",
  "root_cause": "Database connection pool exhausted; retry opens new connection without releasing",
  "evidence": "stack trace at auth.py:142, connection count = 100/100",
  "fix": "release connection in finally block; add pool size limit",
  "severity": "high",
  "location": {"file": "src/auth.py", "line": 142}
}
```


## When to use

Load this skill when:
- The task description matches the patterns described in this skill
- You are uncertain about the recommended approach
- You need a checklist or pattern to follow

## When NOT to use

- The task clearly doesn't match (use a different skill)
- You have a more specific skill for the situation
- The user explicitly requests a different approach

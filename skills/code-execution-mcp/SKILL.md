---
name: code-execution-mcp
description: Reduce token usage ~100x by writing code to call MCPs/tools instead of direct tool calls. Tool definitions and intermediate results stay out of the context window. For any workflow with multiple tool calls, especially when using MCP servers.
license: MIT
compatibility: opencode>=1.16.0
metadata:
  source: Anthropic Code Execution with MCP (Nov 2025)
---

# Code Execution with MCP

The pattern from Anthropic's [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) blog (November 2025) that reduces token usage by **~100x** in multi-tool workflows.

## The Problem

Direct tool calls are token-expensive:
- **Tool definitions** load upfront into context (every tool, every session)
- **Intermediate results** pass through the context window (model sees them, may comment, then they're discarded)
- **Cumulative cost**: 100+ tools × large outputs = context window fills fast

## The Solution

Write code that calls tools directly. The model only sees:
- The code (one block, not 100 tool calls)
- The final result (one summary, not intermediate steps)

## Before / After

### Before (direct tool calls)
```
Tool: gdrive.getDocument({id: "abc123"})
  → Returns 5,000 token document body
  → ALL 5,000 tokens sit in context

Tool: salesforce.updateRecord({...})
  → Returns 2,000 token response
  → ALL 2,000 tokens sit in context

Tool: gmail.sendEmail({...})
  → Returns 500 token response
  → ALL 500 tokens sit in context

Total: 7,500 tokens in context
```

### After (code execution)
```python
# This entire script is one tool call (~200 tokens)
const doc = await gdrive.getDocument({id: "abc123"})
const summary = doc.content.slice(0, 500)  # Trim before returning
const updated = await salesforce.updateRecord({...summary, status: "reviewed"})
await gmail.sendEmail({to: doc.owner, subject: `Updated: ${doc.title}`})
return {record_id: updated.id, email_sent: true}
# Only the final return value (1 line, ~30 tokens) hits context
```

**Token usage: ~230 tokens vs 7,500 tokens** — a 32x reduction. With more tools, the ratio approaches 100x.

## When to Use

Use this pattern when:
- The workflow involves 3+ tool calls
- Tools have large outputs (documents, query results, file contents)
- You can process results in code (filter, transform, summarize)
- The user wants the final result, not every intermediate step

Don't use when:
- Single tool call (no benefit)
- Need to show reasoning about intermediate steps
- Tool outputs are already small

## MCP Server Patterns

### Pattern 1: Code-Execution MCP Wrapper

Create a thin MCP server that exposes a `run_code` tool:
```python
# mcp_servers/code_exec.py
async def run_code(code: str, ctx: Context):
    """Execute arbitrary code with access to all MCP tools."""
    # In a sandboxed environment
    exec_globals = {
        "gdrive": gdrive_client,
        "salesforce": salesforce_client,
        "gmail": gmail_client,
    }
    result = await asyncio.run(exec(code, exec_globals))
    return result
```

### Pattern 2: Skill-Embedded Code Patterns

For common patterns, save them as skills:
- `pdf-extract` — load PDF, extract relevant sections
- `db-migrate` — connect, migrate, verify
- `git-pr-create` — branch, commit, push, open PR

### Pattern 3: Streaming Results

For long-running workflows, stream results:
```python
async def long_workflow():
    yield {"step": "fetching", "progress": 0.2}
    data = await gdrive.getDocument(...)
    yield {"step": "processing", "progress": 0.5}
    result = process(data)
    yield {"step": "done", "result": result.summary}
```

## Sample Code Patterns

### Bulk data processing
```python
# Get all customer records, filter, update
async def update_churned_customers():
    customers = await salesforce.query("SELECT Id, Last_Login__c FROM Contact")
    churned = [c for c in customers if is_churned(c)]
    
    # Process in batches of 100
    for batch in chunked(churned, 100):
        await salesforce.bulkUpdate([{
            "Id": c["Id"],
            "Status__c": "Churned"
        } for c in batch])
    
    return f"Updated {len(churned)} customers"
```

### Multi-source data aggregation
```python
# Get data from 3 sources, merge, return only summary
async def quarterly_report():
    sales = await salesforce.getQuarterlySales()
    support = await zendesk.getQuarterlyTickets()
    feedback = await gdrive.getNPSExports()
    
    return {
        "revenue": sum(s["amount"] for s in sales),
        "ticket_count": len(support),
        "avg_nps": mean(f["score"] for f in feedback),
        "top_issue": most_common(support, "category")
    }
```

## Security Considerations

⚠️ Code execution is powerful — sandbox carefully:

- **No network access by default** — only allowlisted MCP servers
- **No filesystem writes outside workspace**
- **No subprocess execution** unless explicitly allowed
- **Timeout limits** — 30s default, configurable
- **Resource caps** — memory, CPU per execution
- **Audit log** — log every code execution for review

## Integration with OpenCode

In OpenCode, this pattern is enabled by:
1. **Bun's runtime** (already in use) — can execute JS/TS directly
2. **MCP servers** (already configured) — exposed as code libraries
3. **The `bash` tool** — can run scripts that import MCP clients
4. **The `edit`/`write` tools** — can save code as artifacts

The orchestrator should detect multi-tool workflows and suggest code execution:
```
"This workflow has 5+ tool calls. Consider writing a script 
to reduce context window usage by ~100x."
```

## Related

- Anthropic blog: https://www.anthropic.com/engineering/code-execution-with-mcp
- MCP 2026 roadmap: includes Tasks extension, streaming results
- Anthropic skill: this pattern is available as a skill for the `general` agent

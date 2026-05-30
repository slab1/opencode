# Agent Router - Smart Agent Selection

This document defines rules for suggesting the most appropriate agent based on user intent.

## Default Routing

**All user tasks route to the `orchestrator` agent by default.**
The orchestrator then decides:
- Handle directly (simple tasks: explain, read, quick search)
- Delegate to build/plan (implementation or planning tasks)
- Dispatch full workflow (complex multi-agent tasks)

This ensures every task goes through decomposition, gap detection, and quality gates.

## Direct Agent Routing (When Bypassing Orchestrator)

If the user explicitly requests a specific agent, or for simple single-agent tasks, route directly:

## Routing Rules

### Keyword-Based Routing

| User Intent/Keywords | Suggested Agent | Reason |
|---------------------|-----------------|--------|
| `build`, `implement`, `code`, `create`, `write code` | **build** | Implementation tasks |
| `plan`, `design`, `architect`, `review architecture` | **plan** → **architect** | Planning needs both |
| `debug`, `error`, `bug`, `issue`, `problem` | **debug** | Diagnostic investigation |
| `document`, `docs`, `README`, `documentation` | **docs** | Documentation tasks |
| `refactor`, `clean up`, `improve code` | **refactor** | Code quality improvements |
| `review`, `PR`, `pull request`, `code review` | **review** | Code review process |
| `security`, `vulnerability`, `audit`, `CVE` | **security** | Security analysis |
| `test`, `coverage`, `unit test`, `integration test` | **test** | Testing tasks |
| `explore`, `find files`, `search code`, `where is` | **explore** | Codebase exploration |
| `research`, `investigate`, `multi-step` | **general** | Complex research tasks |
| `image`, `screenshot`, `photo`, `picture`, `diagram` | **media-agent** | Image analysis and OCR |
| `audio`, `transcribe`, `meeting`, `voice`, `recording` | **media-agent** | Audio transcription |
| `video`, `screen recording`, `demo`, `clip` | **media-agent** | Video analysis |
| `document`, `PDF`, `pdf`, `DOCX`, `scan` | **document-agent** | Document parsing and OCR |
| `OCR`, `extract text from`, `read this file` | **document-agent** or **media-agent** | Text extraction from files |
| `deploy`, `release`, `ship`, `publish`, `rollout` | **orchestrator** → deploy-release workflow | Build → Test → Deploy → Monitor |
| `migration`, `schema`, `migrate db`, `alter table` | **orchestrator** → db-migration workflow | Plan → Backup → Migrate → Verify |
| `onboarding`, `setup`, `new project`, `initialize` | **orchestrator** → project-onboarding workflow | Explore → Plan → Setup → Verify |

### Context-Based Routing

| Context | Suggested Agent | Workflow |
|---------|-----------------|-----------|
| User mentions "architecture" or "system design" | **plan** (then task→**architect**) | Planning phase first |
| User has error stack trace | **debug** | Diagnostic investigation |
| User mentions "new feature" | **plan** (then task→**build**) | Plan then implement |
| User mentions "security audit" | **security** | Specialized security review |
| User asks "how does X work?" | **explore** | Fast codebase exploration |

---

## Implementation

### Step 1: Add Routing Logic to Primary Agents

Add a "Agent Selection" section to the **build** agent (as the default entry point):

```markdown
## Agent Selection Guidelines

When you receive a task, consider if another agent is better suited:
- Need architecture advice? → Use task tool to invoke "architect"
- Need to debug an issue? → Use task tool to invoke "debug"  
- Need documentation? → Use task tool to invoke "docs"
- Need security review? → Use task tool to invoke "security"
- Need to explore codebase? → Use task tool to invoke "explore"
```

### Step 2: Create Workflow Presets

Define common multi-agent workflows in a config file.

---

## Example Routing Scenarios

### Scenario 1: "I need to add a login feature"
```
1. User → orchestrator (default entry point)
2. orchestrator reads knowledge graph, matches "auth-flow" pattern
3. orchestrator dispatches: plan → architect → build → security → test
4. orchestrator evaluates each agent's output against quality gates
5. orchestrator detects gaps (e.g., missing email verification) and re-dispatches
6. orchestrator synthesizes and returns complete result to user
```

### Scenario 2: "There's a bug in the API"
```
1. User → orchestrator (default entry point)
2. orchestrator matches "bug-fix" pattern from knowledge graph
3. orchestrator dispatches: debug → build → test → review
4. orchestrator evaluates each output, detects any remaining issues
5. orchestrator re-dispatches if needed, then returns complete fix
```

### Scenario 3: "Review my PR"
```
1. User → orchestrator (default entry point)
2. orchestrator matches "code-review" pattern from knowledge graph
3. orchestrator dispatches: review → security → test
4. orchestrator evaluates findings from all three agents
5. orchestrator synthesizes comprehensive review report
```

---

## Smart Suggestions (Future Enhancement)

To implement automatic suggestions, the system would need to:
1. Parse user intent from message
2. Match against routing rules
3. Suggest: "This sounds like a job for @debug. Switch? [Y/n]"

**Current workaround**: Primary agents can suggest: "Consider using the debug agent for this task."

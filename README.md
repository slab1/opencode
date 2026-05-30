# OpenCode Config — Agent System, Plugins & Tools

Full OpenCode configuration featuring a multi-agent architecture, knowledge graph orchestration, shared context system, and an extensive plugin ecosystem.

## 🧠 Agent System

### Primary Agents (interact directly with users)

| Agent | Description |
|-------|-------------|
| **orchestrator** | Master coordinator — decomposes tasks, dispatches agents, evaluates outputs, detects gaps, iterates until success |
| **build** | Implements features, fixes bugs, writes production code |
| **plan** | Analyzes code, creates implementation plans, breaks down requirements |
| **pioneer** | Research & Innovation — explores cutting-edge tech, trends, prototypes, and provides actionable recommendations |

### Subagents (invoked by primary agents)

| Agent | Specialty |
|-------|-----------|
| **architect** | System architecture design, technology decisions, scalability planning |
| **debug** | Bug investigation, root cause analysis, error diagnostics |
| **docs** | Documentation writing, API docs, user guides |
| **explore** | Fast codebase exploration, file search, pattern matching |
| **general** | Multi-step research, parallel investigations, complex analysis |
| **refactor** | Code improvement, optimization, pattern application |
| **review** | Code quality review, best practices enforcement |
| **security** | Security audits, vulnerability detection, CVE analysis |
| **test** | Test writing, coverage analysis, test framework integration |
| **video-creator** | Programmatic video creation (MoviePy + FFmpeg) |
| **web-browser** | Full browser automation — navigate, click, fill forms |
| **display-agent** | Virtual display & VNC session management |

### Invocation Rules
- **Primary agents** invoke subagents via the `task` tool (max depth 3)
- **Subagents** can only invoke other agents when explicitly delegated (max depth 3)
- **Orchestrator** can invoke ALL agents (max depth 5)
- All agents participate in the cross-agent shared context system

---

## 🧩 Installed Plugins (9)

All auto-installed by OpenCode on startup via Bun:

| Plugin | Purpose | Cost |
|--------|---------|------|
| **opencode-memfs** | Git-backed persistent memory across sessions | $0 |
| **opencode-vibeguard** | Redacts secrets/PII before LLM calls, restores locally | $0 |
| **opencode-cross-repo** | Clone, grep, commit, PR across multiple GitHub/GitLab repos | $0 |
| **opencode-worktree** | Git worktree isolation for session branches | $0 |
| **opencode-notify** | Desktop notifications on task completion | $0 |
| **@franlol/opencode-md-table-formatter** | Auto-formats LLM-generated markdown tables | $0 |
| **opencode-codebase-index** | Semantic codebase search (plain English queries) | $0 |
| **opencode-swarm** | Architect-led multi-agent team with gated pipeline (14+ agents) | $0 |
| **oh-my-opencode-slim** | Background agents, LSP/AST tools, curated presets | $0 |

---

## 🖥️ MCP Servers (3)

| Server | Type | Purpose |
|--------|------|---------|
| **Supabase** | Remote | Database, Auth, Edge Functions, Realtime, Storage |
| **Context7** | Local (npx) | Fresh library docs — no more outdated API guesses |
| **Firecrawl** | Local (npx) | Web scraping, crawling, and search at scale |

### API Keys Needed
- **Supabase**: `{env:SUPABASE_ACCESS_TOKEN}` — set in environment
- **Context7**: Free key at [context7.com/dashboard](https://context7.com/dashboard) (optional, works with rate limits without)
- **Firecrawl**: Free key at [firecrawl.dev/app](https://firecrawl.dev/app) — set `FIRECRAWL_API_KEY` in `opencode.jsonc`

---

## 🧠 Knowledge Graph System

The orchestrator uses a structured knowledge graph at `knowledge-graph/graph.json` containing:

- **Agent registry** — all agent definitions, capabilities, permissions
- **Workflow patterns** — 10 pre-defined patterns (auth-flow, bug-fix, full-feature, tech-research, etc.)
- **Quality gates** — code_complete, tested, secure, documented, reviewed, and more
- **Gap detection rules** — domain-specific checks per task type
- **Shared context config** — cross-agent memory and workflow continuity

### Workflow Patterns

| Pattern | Agents | Triggers |
|---------|--------|----------|
| auth-flow | plan → architect → build → security → test | login, register, auth, oauth |
| api-endpoint | plan → build → test → docs | endpoint, api, route, rest |
| bug-fix | debug → build → test | bug, error, crash, not working |
| refactor | explore → refactor → test | refactor, cleanup, technical debt |
| security-audit | security → build → test | security, vulnerability, audit |
| full-feature | plan → architect → build → test → docs | feature, implement, add, create |
| code-review | review → security | review, PR, code review |
| performance | debug → refactor | slow, performance, optimize |
| video-creation | video-creator → build → test | video, slideshow, reels, shorts |
| web-automation | web-browser → build | browse, scrape, extract, book flight |
| flight-booking | web-browser → build | flight, book flight, airline, travel |
| display-management | display-agent → build | display, vnc, screen, headed browser |
| **tech-research** | **pioneer → build** | **research, trend, innovation, compare, pioneer** |

---

## 🔄 Shared Context System

Cross-agent memory persistence for workflow continuity:

```
shared/
├── context.json          # Central store — all agents read/write here
├── README.md             # Detailed usage guide
├── helpers/
│   └── context.py        # Python helper for programmatic access
└── findings/             # Per-agent finding files
```

**Flow**: Orchestrator → Dispatch agent (with context) → Agent reads context → Agent writes findings → Orchestrator evaluates → Next agent gets accumulated context

---

## 🖥️ REPL Tool

A fully-interactive Read-Eval-Print Loop for OpenCode at `scripts/repl` (installed as `/usr/local/bin/repl`):

- Interactive & one-shot modes
- SQLite DB polling (captures opencode responses)
- Syntax highlighting, tab completion, multi-line input
- Commands: `/help`, `/exit`, `/clear`, `/history`, `/stats`, `/context`

---

## 📱 Acode Plugin (Legacy)

The original OpenCode AI plugin for Acode editor on Android.

### Commands

| Shortcut | Command | Description |
|----------|---------|-------------|
| `Ctrl+Shift+A` | Ask | Ask OpenCode about selected code |
| `Ctrl+Shift+F` | Fix | Fix bugs in selected code |
| `Ctrl+Shift+E` | Explain | Explain selected code |
| `Ctrl+Shift+G` | Generate | Generate code from description |
| `Ctrl+Shift+S` | Status | Check OpenCode CLI status |
| `Ctrl+Shift+D` | Debug | Show diagnostic info |

### Installation

1. Install OpenCode: `npm install -g opencode-ai`
2. Download `dist/acode-oc.zip` → Acode Settings → Plugins → Install from ZIP
3. Select code → press `Ctrl+Shift+A`

---

## 📁 Project Structure

```
~/.config/opencode/
├── opencode.jsonc            # Main config (plugins, MCP, permissions)
├── README.md                 # This file
├── agents/                   # Agent definitions (*.md)
│   ├── orchestrator.md
│   ├── build.md
│   ├── plan.md
│   ├── pioneer.md            # <-- NEW: Research & Innovation agent
│   ├── architect.md
│   ├── debug.md
│   ├── docs.md
│   ├── explore.md
│   ├── general.md
│   ├── refactor.md
│   ├── review.md
│   ├── security.md
│   ├── test.md
│   ├── video-creator.md
│   ├── web-browser.md
│   └── display-agent.md
├── knowledge-graph/
│   ├── graph.json             # Agent registry, patterns, quality gates
│   ├── README.md
│   └── outcomes/
│       └── sessions.json      # Session outcome tracking
├── shared/
│   ├── context.json           # Cross-agent shared context store
│   ├── README.md
│   ├── helpers/context.py
│   └── findings/
├── scripts/
│   └── repl                   # Interactive REPL for OpenCode
└── plugin.json                # Acode plugin manifest
```

---

## License

MIT

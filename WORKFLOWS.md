# OpenCode Agent Workflows

Orchestrator-driven multi-agent workflows for common development scenarios.

## How Workflows Work Now

**All workflows route through the orchestrator by default.** The orchestrator:
1. Reads the knowledge graph to identify the workflow pattern
2. Reads the shared context store (`~/.config/opencode/shared/context.json`) for existing findings
3. Dispatches agents in the optimal sequence, **injecting accumulated context** from previous agents
4. Each agent reads shared context at start, writes findings back before finishing
5. Evaluates each agent's output against quality gates
6. Detects gaps and re-dispatches until complete
7. Synthesizes the final result, finalizing the shared context for future use

### Context Flow Between Agents

```
 Workflow Start
      │
      ▼
 Orchestrator reads shared/context.json
      │
      ├──→ Dispatches Agent 1
      │     (with context from previous agents + workflow trace)
      │     Agent reads context.json → works → writes findings → done
      │
      ├──→ Orchestrator reads updated context.json
      │     Updates workflow_trace, persists findings
      │
      ├──→ Dispatches Agent 2
      │     (with Agent 1's findings + accumulated context)
      │     Agent reads context.json → works → writes findings → done
      │
      └──→ ... continues for all agents in workflow
           Final context.json persists for cross-session reference
```

This ensures every agent has full visibility into what previous agents discovered, decided, and built.

---

## Workflow 1: Full-Stack Feature Development

**Pattern**: `full-feature`  
**Trigger**: "Add feature [X]" or "Implement [X]"

```
User → orchestrator
         │
         ├─→ task → plan (analyze requirements, break down tasks)
         │           └─→ task → architect (system design if complex)
         │
         ├─→ task → build (implement the feature)
         │
         ├─→ task → test (write unit + integration tests)
         │
         └─→ task → docs (update documentation)
```

**Quality Gates**: code_complete, tested, documented, reviewed  
**Gap Checks**: error handling, edge cases, input validation

---

## Workflow 2: Bug Investigation & Fix

**Pattern**: `bug-fix`  
**Trigger**: "Fix bug [X]" or "Debug [X]"

```
User → orchestrator
         │
         ├─→ task → debug (investigate, identify root cause)
         │
         ├─→ task → build (implement the fix)
         │
         ├─→ task → test (write regression tests)
         │
         └─→ task → review (verify fix quality)
```

**Quality Gates**: code_complete, tested, reviewed  
**Gap Checks**: regression risk, related components, logging

---

## Workflow 3: Code Review & Audit

**Pattern**: `code-review`  
**Trigger**: "Review PR" or "Audit code"

```
User → orchestrator
         │
         ├─→ task → review (code quality, best practices)
         │
         ├─→ task → security (vulnerability scan)
         │
         └─→ task → test (coverage analysis)
```

**Quality Gates**: reviewed, secure, tested  
**Gap Checks**: performance issues, maintainability, test gaps

---

## Workflow 4: Architecture Planning

**Pattern**: Custom (orchestrator builds from plan + architect)  
**Trigger**: "Design system" or "Plan architecture"

```
User → orchestrator
         │
         ├─→ task → plan (requirements, constraints, roadmap)
         │
         └─→ task → architect (system design, technology decisions)
```

**Quality Gates**: code_complete (design docs), reviewed  
**Gap Checks**: scalability, security by design, deployment strategy

---

## Workflow 5: Security Audit

**Pattern**: `security-audit`  
**Trigger**: "Security audit" or "Check vulnerabilities"

```
User → orchestrator
         │
         ├─→ task → security (vulnerability scan, dependency audit)
         │
         ├─→ task → build (implement fixes for findings)
         │
         ├─→ task → test (regression tests for security fixes)
         │
         └─→ task → docs (document findings and remediation)
```

**Quality Gates**: secure, tested, documented, code_complete  
**Gap Checks**: dependency pinning, secrets exposure, input validation

---

## Workflow 6: Codebase Exploration

**Pattern**: Custom (orchestrator dispatches explore)  
**Trigger**: "How does X work?" or "Find Y"

```
User → orchestrator
         │
         └─→ task → explore (fast search, pattern matching)
```

**Quality Gates**: None (informational)  
**Gap Checks**: None — returns findings directly

---

## Workflow 7: Authentication Feature

**Pattern**: `auth-flow`  
**Trigger**: "login", "register", "auth", "oauth", "password", "signup"

```
User → orchestrator
         │
         ├─→ task → plan (auth requirements, compliance needs)
         │
         ├─→ task → architect (auth system design, data flow)
         │
         ├─→ task → build (implement auth feature)
         │
         ├─→ task → security (audit for auth vulnerabilities)
         │
         └─→ task → test (comprehensive auth test suite)
```

**Quality Gates**: code_complete, tested, secure, documented  
**Gap Checks**: email verification, password reset, rate limiting, session management, CSRF protection

---

## Workflow 8: API Endpoint Development

**Pattern**: `api-endpoint`  
**Trigger**: "endpoint", "api", "route", "handler", "rest", "graphql"

```
User → orchestrator
         │
         ├─→ task → plan (endpoint requirements, request/response schema)
         │
         ├─→ task → build (implement endpoint)
         │
         ├─→ task → test (unit + integration tests)
         │
         └─→ task → docs (API documentation)
```

**Quality Gates**: code_complete, tested, documented, secure  
**Gap Checks**: input validation, error handling, rate limiting, authentication

---

## Workflow 9: Code Refactoring

**Pattern**: `refactor`  
**Trigger**: "refactor", "cleanup", "improve", "restructure", "optimize"

```
User → orchestrator
         │
         ├─→ task → explore (map code area to refactor)
         │
         ├─→ task → refactor (apply patterns, improve structure)
         │
         ├─→ task → test (verify behavior preserved)
         │
         └─→ task → review (quality assessment)
```

**Quality Gates**: tested, reviewed, code_complete  
**Gap Checks**: performance regression, behavior change, breaking changes

---

## Workflow 10: Performance Optimization

**Pattern**: `performance`  
**Trigger**: "slow", "performance", "optimize", "bottleneck", "latency"

```
User → orchestrator
         │
         ├─→ task → debug (profile, identify bottlenecks)
         │
         ├─→ task → architect (recommend architectural improvements)
         │
         ├─→ task → refactor (implement optimizations)
         │
         └─→ task → test (benchmark verification)
```

**Quality Gates**: tested, reviewed  
**Gap Checks**: memory leaks, N+1 queries, cache strategy, connection pooling

---

---

## Workflow 11: Video Content Creation

**Pattern**: `video-creation`  
**Trigger**: "video", "create video", "make a video", "tiktok", "youtube shorts", "reels", "slideshow"

```
User → orchestrator
         │
         ├─→ task → video-creator (create video with opencode_video Python module)
         │
         ├─→ task → build (implement any custom scripts if needed)
         │
         └─→ task → test (verify: file exists, correct duration, resolution, format)
```

**Quality Gates**: video_rendered, code_complete  
**Gap Checks**: platform preset, aspect ratio, audio integration, file size, text readability

**Available Platforms**:
| Platform | Key | Resolution | Aspect |
|----------|-----|-----------|--------|
| YouTube | `youtube` | 1920×1080 | 16:9 |
| YouTube Shorts | `youtube_shorts` | 1080×1920 | 9:16 |
| TikTok | `tiktok` | 1080×1920 | 9:16 |
| Instagram Reel | `instagram_reel` | 1080×1920 | 9:16 |
| Instagram Post | `instagram_post` | 1080×1080 | 1:1 |
| Twitter/X | `twitter` | 1280×720 | 16:9 |
| LinkedIn | `linkedin` | 1920×1080 | 16:9 |
| Facebook | `facebook` | 1920×1080 | 16:9 |

**Python API Quick Reference**:
```python
from opencode_video import create_video, compose_video
from opencode_video.scripts import VideoScript, Scene, script_to_video

# Simple text-to-video
create_video(
    output="intro.mp4",
    texts=[{"text": "Hello World", "font_size": 72}],
    platform="youtube",
    duration_per_clip=5,
)

# Multiple scenes (script-based)
script = VideoScript(
    title="My Video",
    platform="youtube_shorts",
    intro_scene=Scene(text="Intro", duration=3),
    scenes=[Scene(text="Content", duration=5)],
    outro_scene=Scene(text="Outro", duration=3),
)
script_to_video(script)

# Compose with overlays
compose_video(
    main_clip="footage.mp4",
    overlays=[
        {"type": "text", "source": "Title", "position": "center"},
        {"type": "image", "source": "logo.png", "position": ("right", "top")},
    ],
    platform="tiktok",
)
```

---

## Workflow 12: Web Browser Automation

**Pattern**: `web-automation`  
**Trigger**: "browse", "web", "website", "browser", "click", "form", "login", "search", "scrape", "extract", "book", "fill", "navigate", "automate"

```
User → orchestrator
         │
         ├─→ task → web-browser (launch browser, navigate, interact, extract data)
         │
         └─→ task → build (custom scripts if selectors need adaptation)
```

**Pattern**: `flight-booking`  
**Trigger**: "flight", "book flight", "airline", "travel", "trip", "airfare", "ticket", "plane"

```
User → orchestrator
         │
         ├─→ task → web-browser (search flights using workflows.search_flights())
         │
         └─→ task → build (customize for specific travel site if needed)
```

**Quality Gates**: rendered_web, code_complete  
**Gap Checks**: cookie consent handling, dynamic content waits, JavaScript-rendered content, element selector resilience, page load completion

**Python API Quick Reference**:
```python
from opencode_web import Browser
from opencode_web.workflows import search_flights, browse_and_extract

# Context manager (recommended)
with Browser() as b:
    b.navigate("https://www.google.com")
    b.fill("textarea[name='q']", "hello world")
    b.press_key("Enter")
    b.wait(2000)
    print(b.get_title())

# Multi-step data extraction
with Browser() as b:
    data = browse_and_extract("https://example.com", [
        {"action": "wait", "timeout": 2000},
        {"action": "extract", "type": "all"},
    ])

# Flight search
with Browser() as b:
    results = search_flights(
        b, origin="JFK", destination="LHR",
        departure_date="2026-06-15", site="google_flights",
    )
```

---

## Workflow 13: Deployment & Release

**Pattern**: `deploy-release`  
**Trigger**: "deploy", "release", "ship", "publish", "rollout", "production"

```
User → orchestrator
         │
         ├─→ task → plan (release plan, version bump, changelog)
         │
         ├─→ task → build (build artifacts, bundle assets)
         │
         ├─→ task → test (run full test suite, smoke tests)
         │
         ├─→ task → security (final security scan, dependency check)
         │
         ├─→ task → review (release review, changelog verification)
         │
         └─→ task → docs (release notes, migration guide, changelog)
```

**Post-Deployment**:
```
         ├─→ task → explore (verify deployment: health checks)
         └─→ task → general (monitor: logs, errors, metrics)
```

**Quality Gates**: built, tested, secure, reviewed, documented, deployed  
**Gap Checks**: version consistency, DB migrations, env variables, feature flags, rollback plan, monitoring alerts

---

## Workflow 14: Database Migration

**Pattern**: `db-migration`  
**Trigger**: "migration", "schema", "database change", "alter table", "migrate db"

```
User → orchestrator
         │
         ├─→ task → explore (map current schema, find all DB references)
         │
         ├─→ task → plan (migration strategy, rollback plan, downtime assessment)
         │
         ├─→ task → general (backup database)
         │
         ├─→ task → build (write migration files, update models)
         │
         ├─→ task → test (migration dry-run, data integrity tests, rollback tests)
         │
         └─→ task → review (verify migration safety, index strategy, performance)
```

**Quality Gates**: backed_up, tested (dry-run), reviewed, reversible, code_complete  
**Gap Checks**: foreign key impacts, data loss risk, index performance, lock contention, rollback script

---

## Workflow 15: Display / VNC Session Management

**Pattern**: `display-management`  
**Trigger**: "display", "vnc", "screen", "headed", "virtual display", "xvfb", "gui", "show browser", "preview video"

```
User → orchestrator
         │
         ├─→ task → display-agent (start Xvfb + fluxbox + x11vnc)
         │
         ├─→ task → build (custom config if needed)
         │
         └─→ Integration with headed browser or video preview
```

**Quality Gates**: display_running, code_complete  
**Gap Checks**: xvfb installed, x11vnc installed, VNC port available, cleanup on exit

**Python API Quick Reference**:
```python
from opencode_display import Display, ensure_display

# Global singleton (auto-starts, shared across agents)
d = ensure_display()
print(f"VNC: {d.vnc_address}")

# Context manager for isolated sessions
with Display(display_num=99, vnc_port=5900) as d:
    d.launch_browser("https://example.com")
    d.launch_video_preview("output.mp4")
    path = d.take_screenshot("/tmp/screen.png")
```

**VNC Connection**:
```bash
vncviewer localhost:5900
# Password: opencode
```

---

## Workflow 16: Project Onboarding / Setup

**Pattern**: `project-onboarding`  
**Trigger**: "setup", "onboarding", "new project", "initialize", "first time", "get started"

```
User → orchestrator
         │
         ├─→ task → explore (discover project structure, config files, dependencies)
         │
         ├─→ task → plan (setup roadmap, missing configs, environment needs)
         │
         ├─→ task → docs (README setup instructions, contribution guide)
         │
         ├─→ task → build (create missing config files, env template, CI setup)
         │
         ├─→ task → test (verify setup: run tests, lint, build)
         │
         └─→ task → review (final setup review, checklist verification)
```

**Onboarding Checklist** (auto-generated):
```
 Project structure documented
 Dependencies installed & locked
 Environment variables templated (.env.example)
 CI/CD pipeline configured
 Test suite runs green
 Linting/formatting configured
 README has setup instructions
 Contribution guide exists
 First contributor can run in < 5 min
```

**Quality Gates**: documented, setup_verified, tested, reviewed  
**Gap Checks**: missing env vars, unlisted dependencies, broken setup steps, platform-specific issues

---

To define a custom workflow, add a pattern to the knowledge graph:

```json
{
  "patterns": {
    "my-workflow": {
      "name": "My Custom Workflow",
      "agents": ["plan", "build", "test"],
      "trigger_keywords": ["keyword1", "keyword2"],
      "description": "What this workflow does",
      "sequence": [
        {"agent": "plan", "task": "Analyze requirements"},
        {"agent": "build", "task": "Implement the feature"},
        {"agent": "test", "task": "Write tests"}
      ]
    }
  }
}
```

The orchestrator will automatically pick up new patterns from the knowledge graph.

---

## Workflow Execution Rules

| Rule | Description |
|------|-------------|
| **Parallel dispatch** | Independent agents run concurrently (e.g., security + test after build) |
| **Sequential dispatch** | Dependent agents run in order (e.g., plan before build) |
| **Gap iteration** | Orchestrator re-dispatches agents to fill detected gaps |
| **Quality gates** | Every workflow runs applicable quality gates before returning |
| **Depth limit** | Agent invocation capped at depth 5 (orchestrator) or 3 (build/plan) |

# OpenCode Configuration Toolkit

A production-ready [OpenCode](https://opencode.ai) configuration with **23 agents**, multimodal file processing, web automation, video creation, virtual display management, MCP server integration, and a **self-improving agent evaluation system**.

## Quick Start

```bash
# Option A: Fresh install via bootstrap
git clone https://github.com/slab1/opencode.git ~/.config/opencode
~/.config/opencode/install.sh

# Option B: Just add to existing OpenCode config
git clone https://github.com/slab1/opencode.git /tmp/opencode-config
cp -r /tmp/opencode-config/agents ~/.config/opencode/
cp /tmp/opencode-config/opencode.jsonc ~/.config/opencode/
```

After install, restart OpenCode. The toolkit activates automatically.

## Architecture

```
~/.config/opencode/
├── opencode.jsonc          # Main configuration
├── install.sh              # Bootstrap installer
├── package.json            # npm dependencies for MCP servers
├── agents/                 # 23 OpenCode agent definitions
│   ├── orchestrator.md
│   ├── build.md
│   ├── plan.md
│   ├── pioneer.md          # Research & innovation
│   ├── media-agent.md      # Multimodal file processing
│   ├── document-agent.md   # Document parsing
│   ├── web-browser.md      # Full browser automation
│   ├── video-creator.md    # Programmatic video
│   ├── display-agent.md    # Virtual display manager
│   ├── meta-agent.md       # Self-improvement engine
│   ├── platform-manager.md # Social media management
│   ├── content-creator.md  # AI content generation
│   ├── heartbeat.md        # Periodic health monitoring
│   └── ... (10 more)
├── opencode_improvement/   # Self-improvement engine
│   ├── __init__.py         # Evaluators, strategies, audit, A/B comparison
│   ├── __main__.py         # CLI: audit, eval, kappa, inspect, strategies
│   └── track.py            # Performance tracking
├── knowledge-graph/
│   └── graph.json          # Agent registry & workflow patterns
├── opencode_media/         # Python module for multimodal processing
├── opencode_video/         # Python module for video creation
├── opencode_web/           # Python module for web automation
├── opencode_display/       # Python module for virtual display
├── reports/
│   └── trends/             # Auto-committed eval trend data (CI)
└── shared/
    ├── context.json        # Cross-agent shared state (READ FIRST)
    ├── eval/               # Agent evaluation configuration
    │   ├── agent_eval.yaml # Main YAML eval config (regokan/evalh pattern)
    │   ├── baseline.json   # Baseline for regression detection
    │   └── {agent}_eval.yaml  # Per-agent eval configs (23 files)
    ├── golden/
    │   └── agent_tasks.json # 53 test cases (46 behavioral + 7 property)
    └── helpers/context.py  # Context management helpers
```

## Agent Catalog

### Core Development Agents

| Agent | File | Purpose |
|-------|------|---------|
| **orchestrator** | `agents/orchestrator.md` | Master coordinator — decomposes tasks, dispatches agents, evaluates outputs |
| **build** | `agents/build.md` | Feature implementation and code writing |
| **plan** | `agents/plan.md` | Code analysis and implementation planning |
| **pioneer** | `agents/pioneer.md` | Research, innovation, prototyping, trend analysis |
| **debug** | `agents/debug.md` | Bug investigation and diagnostics |
| **review** | `agents/review.md` | Code quality reviews |
| **refactor** | `agents/refactor.md` | Code refactoring and optimization |
| **docs** | `agents/docs.md` | Documentation writing and maintenance |
| **test** | `agents/test.md` | Test writing and coverage improvement |
| **security** | `agents/security.md` | Security audits and vulnerability checks |

### Specialized Capability Agents

| Agent | File | Purpose |
|-------|------|---------|
| **media-agent** | `agents/media-agent.md` | Image/audio/video processing with vision bridge fallback |
| **document-agent** | `agents/document-agent.md` | PDF/DOCX/spreadsheet parsing via pdftotext + MCP |
| **web-browser** | `agents/web-browser.md` | Full browser automation — click, fill, scroll, screenshot, flight booking (16 capabilities) |
| **video-creator** | `agents/video-creator.md` | Programmatic video for 9 platforms — YouTube, TikTok, Instagram, Twitter (14 capabilities) |
| **display-agent** | `agents/display-agent.md` | Virtual display (Xvfb) + VNC for headed browser preview (12 capabilities) |
| **explore** | `agents/explore.md` | Fast codebase exploration and search |
| **architect** | `agents/architect.md` | System architecture and technology decisions |
| **general** | `agents/general.md` | General-purpose research and execution |

## Features

### Multimodal File Processing

Process images, audio, video, and documents — all through text, no vision model required.

```bash
# Analyze an image
python3 -m opencode_media screenshot.png --summary

# Transcribe audio
python3 -m opencode_media recording.mp3 --summary

# Analyze video (extract frames + transcribe)
python3 -m opencode_media presentation.mp4 --summary --frames 10

# Parse document
python3 -m opencode_media report.pdf --summary
```

**Vision Bridge** automatically detects whether your model supports images. If it doesn't, it generates a rich text description as fallback — so even text-only models can "see."

### Web Automation

Full browser control via Playwright + Python:

```python
from opencode_web import Browser

with Browser(headless=False) as b:
    b.navigate("https://github.com")
    b.fill("#search", "opencode")
    b.press_key("Enter")
    links = b.get_links()
    print(links)
```

Supported actions: navigate, click, fill, type, select, check, upload, hover, scroll, screenshot, JavaScript evaluation, cookie management, multi-tab, form extraction.

### Video Creation

Programmatic video for any platform:

```python
from opencode_video import create_video, PlatformPreset

create_video(
    output="intro.mp4",
    clips=[...],
    platform="youtube"   # or tiktok, instagram, twitter
)
```

Platform presets: YouTube 1080p, TikTok 9:16, Instagram Reel/Post/Story, Twitter/X, LinkedIn, Twitch.

### Virtual Display + VNC

See what your browser and video tools are doing in real time:

```python
from opencode_display import Display

with Display() as d:
    print(f"VNC: {d.vnc_url}")  # Connect via any VNC client
    d.launch_browser("https://example.com")
    d.take_screenshot("page.png")
```

### MCP Server Integration

| Server | Tool | Status | Purpose |
|--------|------|--------|---------|
| **Supabase MCP** | Remote | Enabled | Database, Auth, Edge Functions via Supabase |
| **Context7** | npx | Enabled | Context-aware code assistance |
| **Firecrawl** | npx | Enabled | Website crawling and scraping |
| **Filesystem** | npx | Enabled | Read/write/search files, read media files |
| **Imagine MCP** | npx | Disabled | Image generation |
| **PDF MCP** | npx | Disabled | Advanced PDF processing with OCR |
| **Go Docs MCP** | npx | Disabled | Multi-format document access |
| **Mobile Device MCP** | npx | Enabled | Android/iOS phone control — list devices, launch apps, tap, screenshot, UI tree |

## MCP Servers: What They Do and How to Enable

### Currently Enabled

- **Supabase** (`remote`): Direct access to your Supabase project's database, auth, storage, and edge functions. Requires `SUPABASE_ACCESS_TOKEN` env var. Configured for project `reewcfpjlnufktvahtii`.
- **Context7** (`npx`): Context-aware code search and understanding. No env vars needed.
- **Firecrawl** (`npx`): Website crawling and content extraction. Set `FIRECRAWL_API_KEY` for premium features.
- **Filesystem** (`npx`): Read/write files, search, and read media files (images/audio as base64). Scoped to: `~/.config/opencode`, `/public`, and the Acode cache directory.
- **Mobile Device MCP** (`npx`): Control Android and iOS devices over ADB. Auto-detects platform. 13 tools for screenshots, taps, gestures, app launch, UI tree inspection, and on-device code execution.

### Phone Control Quick Start

Connect your Android phone via USB, then:

```bash
# 1. Verify device is detected
adb devices

# 2. List available devices (auto-detects Android/iOS)
#    (call via MCP tool: list_devices)

# 3. Launch an app by package name
#    (call via MCP tool: launch_app, app_id: "com.twitter.android")

# 4. See what's on screen
#    (call via MCP tool: screenshot)
```

**Prerequisites:**
- **Android**: USB debugging enabled (Settings → Developer Options), phone connected via USB
- **iOS**: Requires macOS with Xcode (not supported on Linux)

**Available tools** (13 total): `list_devices`, `screenshot`, `uitree`, `tap`, `double_tap`, `long_press`, `scroll`, `type_text`, `press_button`, `launch_app`, `terminate_app`, `list_apps`, `run_code`

### Disabled but Ready

To enable a disabled MCP server, edit `opencode.jsonc` and change `"enabled": false` to `"enabled": true`:

```jsonc
"pdf-mcp": {
    "type": "local",
    "command": ["npx", "-y", "pdf-mcp"],
    "enabled": true,  // <-- change this
    "env": {}
}
```

## Agent Evaluation System (Self-Improvement Engine)

The toolkit includes a built-in evaluation system for measuring and improving agent quality, inspired by patterns from 7 evaluation harness repos (DeepEval ⭐7k, regokan/evalh, linny006, Juanllenato, Victor-David-Medina, mpuodziukas-labs, victorwhale).

### Architecture

```
opencode_improvement/          # Python module — CLI + evaluators
├── __init__.py                # 24 strategies, 8 evaluator classes, audit
└── __main__.py                # CLI: audit, eval, kappa, inspect, strategies

shared/
├── eval/
│   ├── agent_eval.yaml        # YAML-driven eval config (regokan/evalh)
│   ├── baseline.json          # Baseline snapshot (Victor-David-Medina)
│   └── {23}_eval.yaml         # Per-agent configs
├── golden/
│   └── agent_tasks.json       # 53 test cases (53 total, 46 behavioral + 7 property)
└── context.json               # Strategy log for metacognitive tracking
```

### CLI Commands

| Command | Description | Source Pattern |
|---------|-------------|----------------|
| `audit` | Structural completeness check of all agent configs | Built-in |
| `eval` | Run golden test cases with configurable pass thresholds | Juanllenato `--fail-under` |
| `eval --compare` | Generate markdown comparison report against baseline | Victor-David-Medina |
| `eval --scorecard` | ASCII bar chart scorecard with green/yellow/red tiers | Weighted composite |
| `eval --provider mock` | Offline eval using MockProvider (no agent runtime needed) | Deterministic CI pattern |
| `eval --judge-model` | LLM-as-judge semantic scoring (3 metrics) | DeepEval LLM-as-judge |
| `eval --executor async` | Concurrent evaluation via asyncio.gather | regokan/evalh |
| `eval --ab config_a config_b` | A/B compare two agent configs | victorwhale |
| `eval --version` | List all test case versions | EleutherAI lm-eval |
| `inspect` | Per-case test case details and failure debugging | regokan/evalh inspect |
| `kappa` | Cohen's Kappa inter-rater agreement for dataset quality | mpuodziukas-labs |
| `list-strategies` | List all 24 improvement strategies with descriptions | HyperAgents |
| `strategies` | Show strategy effectiveness scores from logged applications | Metacognitive tracking |

### Usage Examples

```bash
# Run full evaluation with pass threshold
python3 -m opencode_improvement eval --fail-under 0.8

# Offline eval with scorecard visualization
python3 -m opencode_improvement eval --provider mock --scorecard

# Compare against baseline and generate report
python3 -m opencode_improvement eval --compare --output results.json

# Debug a specific test case
python3 -m opencode_improvement inspect --agent web-browser --case web-browser-001

# Validate dataset quality with Cohen's Kappa
python3 -m opencode_improvement kappa

# A/B compare two versions of an agent config
python3 -m opencode_improvement eval --agent web-browser --ab config_v1.yaml config_v2.yaml

# Check strategy effectiveness
python3 -m opencode_improvement strategies
```

### Key Metrics

- **53 test cases**: 46 behavioral (per-agent, 7 categories) + 7 property-based (universal invariants)
- **24 strategies** in the strategy library with effectiveness tracking
- **23 agents** evaluated against structural, behavioral, and property-based tests
- **CI integration**: Weekly cron + push/PR triggers auto-commit trend data to `reports/trends/`
- **Baseline comparison**: Detect regressions before they ship

### Agent Catalog Updates

The system now manages **23 agents** (up from 18), including:

| New Agent | File | Purpose |
|-----------|------|---------|
| **meta-agent** | `agents/meta-agent.md` | Self-improvement — audits, patches, transfers capabilities |
| **platform-manager** | `agents/platform-manager.md` | Social media management across 11 platforms |
| **content-creator** | `agents/content-creator.md` | AI image/video/text content generation |
| **human** | `agents/human.md` | Human analysis — reads code like a senior engineer |
| **heartbeat** | `agents/heartbeat.md` | Periodic health monitoring and proactive insights |

## Configuration

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SUPABASE_ACCESS_TOKEN` | For Supabase MCP | Supabase project access |
| `FIRECRAWL_API_KEY` | For Firecrawl MCP | Web crawling quota |
| `OPENCODE_CONFIG_DIR` | Optional | Point to a different config directory |
| `PLAYWRIGHT_BROWSERS_PATH` | Optional | Custom Playwright browsers cache path |

### Customizing Permissions

Edit `opencode.jsonc` to grant or restrict agent access. This uses OpenCode's permission syntax:

```jsonc
"permission": {
    "edit": {
        "packages/opencode/migration/*": "ask",   // Ask before editing migration files
        "*": "allow"                               // Allow everything else
    },
    "mcp_filesystem_*": "allow",                   // Allow filesystem MCP tools
    "mcp_imagine-mcp_*": "ask"                     // Ask before AI image generation
}
```

See [OpenCode Configuration Docs](https://opencode.ai/docs/configuration) for the full specification.

## Knowledge Graph

The toolkit includes a knowledge graph (`knowledge-graph/graph.json`) that OpenCode uses to understand agent capabilities and workflow patterns.

### What's Registered

- **23 agents** with capabilities, permissions, and shared context rules
- **14 workflow patterns** from simple code edits to complex multimodal file processing
- **17 population rules** controlling how agents appear in the roster
- **11 domain considerations** including media_tasks, document_tasks, security_audit, data_migration
- **10 quality gates** enforcing standards across workflows

### Multi-Agent Workflows

The knowledge graph enables complex multi-agent patterns like:

```
Multimodal File Processing:
  1. Orchestrator receives a file
  2. Routes to media-agent (image/audio) or document-agent (PDF/DOCX)
  3. Agent processes file, writes findings to shared context
  4. Orchestrator evaluates results, continues with context
```

## Workflows

14 built-in workflow patterns are defined in `WORKFLOWS.md`. Key workflows:

| ID | Name | Agents Involved |
|----|------|-----------------|
| 01 | Simple Code Change | build |
| 02 | Test-Back Change | test → build |
| 03 | Plan-then-Build | plan → build |
| 04 | Review Pipeline | build → review |
| 05 | Security-Aware | security → build → review |
| 06 | Documented Feature | plan → build → docs |
| 07 | Full Quality Gate | plan → build → test → review |
| 08 | Architecture-First | architect → plan → build |
| 09 | Bug Hunt | debug → build → test |
| 10 | Documentation Pass | docs → review |
| 11 | Research-Led Feature | pioneer → plan → build |
| 12 | Multimodal File Processing | media-agent/document-agent → orchestrator |
| 13 | Web Automation | web-browser → display-agent |
| 14 | Video Production | video-creator → display-agent |

## Development

### Python Modules

```bash
# Install in development mode
pip3 install -e opencode_media
pip3 install -e opencode_video
pip3 install -e opencode_web
pip3 install -e opencode_display

# Run tests
python3 -m opencode_media --help
python3 -c "from opencode_video import create_video; print('video OK')"
python3 -c "from opencode_web import Browser; print('web OK')"
python3 -c "from opencode_display import Display; print('display OK')"
```

### Adding a New Agent

1. Create `agents/your-agent.md` following the [agent schema](https://opencode.ai/docs/agents)
2. Add the agent entry to `knowledge-graph/graph.json` with capabilities, permissions, and shared context rules
3. If agent handles a new workflow pattern, add it to `WORKFLOWS.md` and `graph.json`
4. If the agent routes from user intents, add routing rules to `AGENT_ROUTER.md`

## Sharing Strategies

This toolkit can be shared four ways:

| # | Strategy | Best For | Effort |
|---|----------|----------|--------|
| 1 | **GitHub Template** | Individuals, teams | Low |
| 2 | **npm Plugin** (`opencode-starter-kit`) | OpenCode plugin ecosystem | Medium |
| 3 | **pip Packages** (PyPI) | Python module distribution | Medium |
| 4 | **MCP Registry** | Enterprise team deployment | High |

## License

MIT — use freely, fork, customize, and share.

# OpenCode Configuration Toolkit

A production-ready [OpenCode](https://opencode.ai) configuration with **18 agents**, multimodal file processing, web automation, video creation, virtual display management, and MCP server integration.

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
├── agents/                 # 18 OpenCode agent definitions
│   ├── orchestrator.md
│   ├── build.md
│   ├── plan.md
│   ├── pioneer.md          # Research & innovation
│   ├── media-agent.md      # Multimodal file processing
│   ├── document-agent.md   # Document parsing
│   ├── web-browser.md      # Full browser automation
│   ├── video-creator.md    # Programmatic video
│   ├── display-agent.md    # Virtual display manager
│   └── ... (9 more)
├── knowledge-graph/
│   └── graph.json          # Agent registry & workflow patterns
├── opencode_media/         # Python module for multimodal processing
├── opencode_video/         # Python module for video creation
├── opencode_web/           # Python module for web automation
├── opencode_display/       # Python module for virtual display
└── shared/
    ├── README.md           # Shared context usage guide
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

## MCP Servers: What They Do and How to Enable

### Currently Enabled

- **Supabase** (`remote`): Direct access to your Supabase project's database, auth, storage, and edge functions. Requires `SUPABASE_ACCESS_TOKEN` env var. Configured for project `reewcfpjlnufktvahtii`.
- **Context7** (`npx`): Context-aware code search and understanding. No env vars needed.
- **Firecrawl** (`npx`): Website crawling and content extraction. Set `FIRECRAWL_API_KEY` for premium features.
- **Filesystem** (`npx`): Read/write files, search, and read media files (images/audio as base64). Scoped to: `~/.config/opencode`, `/public`, and the Acode cache directory.

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

- **18 agents** with capabilities, permissions, and shared context rules
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

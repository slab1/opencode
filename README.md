# OpenCode AI for Acode

Bring AI-powered code assistance to [Acode](https://acode.app/) — the powerful code editor for Android.

## What It Does

OpenCode for Acode connects your editor to [OpenCode](https://opencode.ai), an open-source AI coding assistant. Select code, press a shortcut, and get AI-powered responses directly in your editor.

| Command | Shortcut | What It Does |
|---------|----------|-------------|
| **Ask OpenCode** | `Ctrl+Shift+A` | Ask anything about your code |
| **Fix with OpenCode** | `Ctrl+Shift+F` | Fix bugs or improve selected code |
| **Explain Code** | `Ctrl+Shift+E` | Get an explanation of selected code |
| **Generate Code** | `Ctrl+Shift+G` | Generate code from a description |
| **Multi-File Ask** | `Ctrl+Shift+M` | Ask about multiple open files at once |
| **Chat History** | `Ctrl+Shift+H` | View past conversations and re-ask |
| **Check Status** | — | Check if the OpenCode server is running |

## Architecture

```
┌─────────────────────────────┐     ┌───────────────────────────────────┐
│  Acode App (Android)        │     │  Terminal (Alpine/Termux)          │
│                             │     │                                   │
│  ┌───────────────────────┐  │     │  ┌─────────────────────────────┐  │
│  │ OpenCode Acode Plugin │  │     │  │ opencode serve              │  │
│  │                       │  │     │  │ http://127.0.0.1:9876       │  │
│  │ • Ctrl+Shift+A prompt │  │     │  │ (no CORS headers — bug)     │  │
│  │ • Streaming response  │  │     │  └──────────┬──────────────────┘  │
│  │ • Apply diffs to code │  │     │             │                     │
│  └──────────┬────────────┘  │     │  ┌──────────▼──────────────────┐  │
│             │               │     │  │ CORS Proxy (cors-proxy.js)  │  │
│             │ fetch()       │     │  │ http://127.0.0.1:9878       │  │
│             │ CORS allowed  │     │  │ Adds Access-Control-Allow-*  │  │
│             ▼               │     │  └──────────┬──────────────────┘  │
│  ┌───────────────────────┐  │     │             │                     │
│  │ Plugin connects to    │  │     │  ┌──────────▼──────────────────┐  │
│  │ http://127.0.0.1:9878 │  │─────┼──│ opencode-server.sh          │  │
│  │ (CORS proxy)          │  │     │  │ (auto-start manager)        │  │
│  └───────────────────────┘  │     │  └─────────────────────────────┘  │
└─────────────────────────────┘     └───────────────────────────────────┘
```

## Installation

### 1. Install OpenCode in your terminal

**Alpine Linux (inside Acode terminal):**
```bash
apk add --no-cache nodejs npm curl
npm install -g opencode-ai
```

**Termux (Android):**
```bash
pkg update && pkg upgrade -y
pkg install nodejs curl -y
npm install -g opencode-ai
```

**Other distros:**
```bash
# Debian/Ubuntu
apt update && apt install -y nodejs npm curl
npm install -g opencode-ai
```

### 2. Install the Acode Plugin

**Option A: From ZIP (easiest)**
1. Download the plugin ZIP from the [releases page](https://github.com/opencode/acode-plugin/releases)
2. Open Acode → Settings → Plugins → Install from ZIP
3. Select the downloaded ZIP file

**Option B: Build from source**
```bash
git clone https://github.com/opencode/acode-plugin
cd acode-plugin
npm install
npm run build
# dist/acode-oc.zip is generated
```
Then install the ZIP in Acode as above.

### 3. Start the Server

```bash
# For convenience, use the management script (recommended — starts both server and CORS proxy):
bash ~/.opencode/opencode-server.sh start

# Or manually:
opencode serve --port 9876
# Then in a second terminal:
node ~/.opencode/cors-proxy.js --target-port 9876 --proxy-port 9878
```

**Note about Android WebView security:** Android's WebView blocks `fetch()` requests from `file://` origins to `http://` URLs due to CORS. The `server.sh` script automatically starts a CORS proxy on port **9878** to work around this. The plugin defaults to port **9878** (the proxy). If you run the server manually, you need to also start the proxy, or change the plugin port to **9876** in Settings.

### 4. Use It

Open a file in Acode, select some code, and press:

- **`Ctrl+Shift+A`** — Ask OpenCode about your code
- **`Ctrl+Shift+F`** — Fix the selected code
- **`Ctrl+Shift+E`** — Explain the selected code
- **`Ctrl+Shift+G`** — Generate new code
- **`Ctrl+Shift+M`** — Ask with multiple open files as context
- **`Ctrl+Shift+H`** — View and re-run past conversations

## Auto-Start (Optional)

The server script can auto-start when you open your terminal:

```bash
curl -sL https://raw.githubusercontent.com/opencode/acode-plugin/main/scripts/install.sh | sh
```

This adds `opencode-server.sh auto-start` to your shell profile (`.bashrc`, `.profile`, etc.).

## Configuration

In Acode, go to Plugins → OpenCode AI → Settings:

| Setting | Default | Description |
|---------|---------|-------------|
| Server Port | `9878` | Port to connect to (default: CORS proxy port). Set to `9876` if running server directly |
| Default Agent | `build` | Agent to use for prompts |

**Port notes:**
- `9876` — Direct OpenCode server (use if running `opencode serve --port 9876` manually)
- `9878` — CORS proxy (use with `server.sh` which starts both server and proxy)
- The proxy adds `Access-Control-Allow-Origin: *` headers needed by Android WebView

## Agent Selection

OpenCode supports specialized agents. Change the "Default Agent" in settings:

| Agent | Best For |
|-------|----------|
| `build` | General coding tasks (default) |
| `debug` | Finding and fixing bugs |
| `plan` | Architecture and planning |
| `architect` | System design decisions |
| `orchestrator` | Complex multi-step tasks |

## Development

```bash
# Clone and install
git clone https://github.com/opencode/acode-plugin
cd acode-plugin
npm install

# Build the plugin ZIP
npm run build          # One-time build
npm run dev            # Watch mode (auto-rebuild on changes)

# Output: dist/acode-oc.zip
```

## Files

```
acode-opencode-plugin/
├── plugin.json          # Plugin manifest
├── main.js              # Full plugin code (single file, no build needed)
├── package.json         # Dev tooling
├── scripts/
│   ├── cors-proxy.js    # CORS proxy (works around Android WebView CORS bug)
│   ├── server.sh        # Terminal server bootstrap (starts server + proxy)
│   ├── install.sh       # One-command installer
│   └── zip.js           # ZIP packager
├── src/                 # Source files (reference)
│   ├── client.js
│   ├── commands.js
│   ├── panel.js
│   └── index.js
└── README.md            # This file
```

## Troubleshooting

**"Cannot reach OpenCode server"**
→ Make sure the server is running: `opencode serve --port 9876` in your terminal
→ Check the plugin port setting: default is 9878 (CORS proxy), try 9876 (direct)
→ If using `server.sh`, verify both server and proxy started: `bash ~/.opencode/opencode-server.sh status`
→ If using Android, ensure your terminal app is not background-killed
→ Android WebView CORS: The plugin needs the CORS proxy (port 9878) to work from `file://` origin

**Plugin doesn't show up in Acode**
→ Verify the ZIP contains `plugin.json` and `main.js`
→ Acode version must be 1.10.0 or higher

**"Timed out waiting for AI response"**
→ The LLM provider might be slow. Try a simpler prompt
→ Check your internet connection
→ The default timeout is 120 seconds

## License

MIT

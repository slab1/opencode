# OpenCode AI for Acode v3.1

AI-powered coding assistance inside [Acode](https://acode.app/) — the powerful code editor for Android.

## Commands

| Shortcut | Command | Description |
|----------|---------|-------------|
| `Ctrl+Shift+A` | Ask | Ask OpenCode about selected code |
| `Ctrl+Shift+F` | Fix | Fix bugs in selected code |
| `Ctrl+Shift+E` | Explain | Explain selected code |
| `Ctrl+Shift+G` | Generate | Generate code from description |
| `Ctrl+Shift+S` | Status | Check OpenCode CLI status |
| `Ctrl+Shift+D` | Debug | Show diagnostic info |

## How It Works

```
Select code → press shortcut → terminal opens → opencode run --agent <agent> --message "..."
```

**No server setup needed.** Just install OpenCode and the plugin, then use keyboard shortcuts.

## Installation

### 1. Install OpenCode

```bash
# In Termux
pkg update && pkg upgrade -y
pkg install nodejs curl -y
npm install -g opencode-ai

# Or Alpine (inside Acode terminal)
apk add --no-cache nodejs npm curl
npm install -g opencode-ai
```

Verify:
```bash
opencode --version
```

### 2. Install the Acode Plugin

1. Download `dist/acode-oc.zip`
2. Open Acode → Settings → Plugins → Install from ZIP
3. Select the ZIP file

### 3. Use It

Open a file, select some code, and press `Ctrl+Shift+A`.

## Files

```
acode-plugin/
├── plugin.json
├── main.js
├── icon.png
├── README.md
└── scripts/
    └── zip.js
```

## License

MIT

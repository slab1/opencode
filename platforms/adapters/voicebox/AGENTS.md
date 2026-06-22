# Voicebox Adapter

Local-first AI voice I/O for OpenCode agents. Wraps the Voicebox REST API + MCP server.

**Repo:** [github.com/slab1/voicebox](https://github.com/slab1/voicebox) (fork of jamiepine/voicebox, 31K ⭐)
**Homepage:** [voicebox.sh](https://voicebox.sh)

## Capabilities

| Function | Description | API Endpoint |
|----------|-------------|--------------|
| `speak()` | Make any agent speak in a cloned voice | `POST /speak` |
| `transcribe()` | Transcribe audio via Whisper STT | `POST /transcribe` |
| `generate_audio()` | Generate speech from text (TTS) | `POST /generate` |
| `list_profiles()` | List available voice profiles | `GET /profiles` |
| `list_captures()` | List past recordings/transcriptions | `GET /captures` |
| `post()` | Text-to-speech generation (adapter interface) | `POST /generate` |
| `speak_report()` | Speak analytics/status reports aloud | `POST /speak` |
| `validate_credentials()` | Check Voicebox is running | `GET /` |

## Integration with OpenCode Agents

| Agent | Use Case |
|-------|----------|
| **orchestrator** | Announces workflow completions and quality gate results |
| **platform-manager** | Speaks analytics reports, post-performance summaries |
| **content-creator** | Generates audio versions of posts, podcast episodes |
| **video-creator** | Provides voiceovers for programmatic videos |
| **debug** | Reads error traces and root cause analysis aloud |
| **security** | Verbally reports critical vulnerabilities |
| **meta-agent** | Announces improvement results and strategy effectiveness |
| **heartbeat** | Periodic health status audio readouts |

## Setup

1. Install Voicebox: [voicebox.sh/download](https://voicebox.sh/download) or `docker compose up`
2. Voicebox runs on `http://127.0.0.1:17493` by default
3. Create voice profiles in the Voicebox app (Settings → Profiles)
4. Optionally set `export VOICEBOX_HOST=http://127.0.0.1:17493` for custom ports

### Docker (headless / CI)

```bash
docker compose up -d
# Voicebox API available at http://127.0.0.1:17493
```

## MCP Server

Voicebox ships a built-in MCP server at `http://127.0.0.1:17493/mcp` with 4 tools:
`voicebox.speak`, `voicebox.transcribe`, `voicebox.list_captures`, `voicebox.list_profiles`.

To connect an OpenCode agent to Voicebox via MCP, add to your `opencode.jsonc`:

```jsonc
"voicebox": {
    "type": "local",
    "command": ["curl", "-s", "-X", "POST",
        "http://127.0.0.1:17493/mcp",
        "-H", "Content-Type: application/json",
        "-d", "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}"],
    "enabled": true,
    "env": {}
}
```

Or use the HTTP MCP transport (if your OpenCode version supports it):

```jsonc
"voicebox": {
    "type": "remote",
    "url": "http://127.0.0.1:17493/mcp",
    "enabled": true,
    "headers": {
        "X-Voicebox-Client-Id": "opencode"
    }
}
```

## Usage Examples

```python
# Platform manager speaks an analytics report
from adapters.voicebox import speak_report
speak_report("Posted 5 times this week. Engagement up 12%.", profile="Morgan")

# Content creator generates audio for a post
from adapters.voicebox import generate_audio
result = generate_audio(
    text="Welcome to our latest podcast episode!",
    profile="Jade",
    language="en"
)
print(f"Generated: {result.get('id')}")

# Any agent speaks on the fly
from adapters.voicebox import speak
speak("Deploy complete. All tests passing.", profile="Morgan", client_id="orchestrator")

# Transcribe a recording
from adapters.voicebox import transcribe
result = transcribe("recording.wav", model="whisper-turbo")
print(f"Transcript: {result.get('text')}")

# Dry-run via post.sh
python3 -c "from adapters import post_to_platform; print(post_to_platform('voicebox', text='Hello world', dry_run=True))"
```

## Dependencies

- Voicebox app running (desktop or Docker)
- Python 3 standard library only (`urllib`, `json`, `subprocess`)
- `curl` for file upload transcription (optional — falls back gracefully)

## Voice Profiles

Pre-configure profiles in Voicebox app:
- **Morgan** — authoritative, precise (good for orchestrator)
- **Scarlett** — analytical, thorough (good for debug)
- **Jade** — creative, expressive (good for content-creator)
- **Kokoro presets** — 50+ curated voices available

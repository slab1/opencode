"""
Voicebox Adapter — local-first AI voice I/O for OpenCode agents.
================================================================
Wraps the Voicebox REST API + MCP server for agent voice output,
transcription, and audio generation from text content.

Voicebox is a local-first AI voice studio (alternative to ElevenLabs + WisprFlow).
It runs a REST API on http://127.0.0.1:17493 and an MCP server on /mcp.

Uses:
  - speak()       — Make any agent speak in a cloned voice
  - transcribe()  — Transcribe audio via Whisper STT
  - generate_audio() — Generate speech from text (for podcasts, video voiceovers)
  - list_profiles() — List available voice profiles
  - list_captures() — List past transcriptions/recordings

Integration with OpenCode agents:
  - Platform-manager speaks analytics reports
  - Content-creator generates audio versions of posts
  - Orchestrator announces workflow completions
  - Debug reads error traces aloud

Requires: Voicebox desktop app running (voicebox.sh) or Docker.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError

PLATFORM = "voicebox"

# Voicebox REST API — runs on localhost when the app or Docker is running
VOICEBOX_HOST = os.environ.get("VOICEBOX_HOST", "http://127.0.0.1:17493")
VOICEBOX_MCP_URL = f"{VOICEBOX_HOST}/mcp"
VOICEBOX_REST_URL = VOICEBOX_HOST

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"
TOKENS_DIR = PLATFORMS_DIR / "tokens"


# ─────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────

def _api_get(path: str) -> dict:
    """GET request to Voicebox REST API."""
    url = f"{VOICEBOX_REST_URL}{path}"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": f"Cannot reach Voicebox at {url}: {e}"}
    except json.JSONDecodeError:
        return {"error": f"Non-JSON response from {url}"}


def _api_post(path: str, data: dict) -> dict:
    """POST request to Voicebox REST API."""
    url = f"{VOICEBOX_REST_URL}{path}"
    body = json.dumps(data).encode()
    try:
        req = Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        return {"error": f"Cannot reach Voicebox at {url}: {e}"}
    except json.JSONDecodeError:
        return {"error": f"Non-JSON response from {url}"}


# ─────────────────────────────────────────────────────────
# Core Voicebox API functions
# ─────────────────────────────────────────────────────────

def is_running() -> bool:
    """Check if Voicebox is running and reachable."""
    result = _api_get("/")
    return "error" not in result


def list_profiles() -> list:
    """List all available voice profiles.

    Returns:
        list of dicts with profile id, name, language, etc.
    """
    result = _api_get("/profiles")
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "error" in result:
        return []
    return result.get("profiles", [])


def list_captures() -> list:
    """List past captures (recordings/transcriptions).

    Returns:
        list of dicts with capture id, transcript, audio info, etc.
    """
    result = _api_get("/captures")
    if isinstance(result, list):
        return result
    return result.get("captures", [])


def speak(text: str, profile: str = "", client_id: str = "opencode",
          personality: bool = False) -> dict:
    """Make Voicebox speak text in a cloned voice.

    This is the agent voice output function. Any OpenCode agent
    can call this to speak results, errors, or notifications.

    Args:
        text: Text to speak aloud
        profile: Voice profile name (case-insensitive) or id.
                 Defaults to per-client binding or system default.
        client_id: Identifier for the calling agent/client.
        personality: If True, rewrites text through the profile's
                     personality LLM before TTS.

    Returns:
        dict with success status and any error message.
    """
    payload = {
        "text": text,
        "client_id": client_id,
    }
    if profile:
        payload["profile"] = profile
    if personality:
        payload["personality"] = True

    return _api_post("/speak", payload)


def transcribe(audio_path: str, model: str = "whisper-turbo") -> dict:
    """Transcribe an audio file using Whisper STT.

    Args:
        audio_path: Path to audio file (wav, mp3, m4a, etc.)
        model: Whisper model size: whisper-turbo (default),
               whisper-base, whisper-small, whisper-medium, whisper-large

    Returns:
        dict with transcript text and metadata.
    """
    # Voicebox REST API may support multipart upload for /transcribe
    # Fallback: use curl for file upload
    import subprocess
    audio_file = Path(audio_path)
    if not audio_file.exists():
        return {"error": f"Audio file not found: {audio_path}"}

    try:
        # Try multipart POST via subprocess (curl) since urlopen
        # doesn't easily do multipart
        cmd = [
            "curl", "-s", "-X", "POST",
            f"{VOICEBOX_REST_URL}/transcribe",
            "-F", f"audio=@{audio_file.resolve()}",
            "-F", f"model={model}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        return {"error": f"Transcription failed: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"error": "Transcription timed out (60s)"}
    except Exception as e:
        return {"error": str(e)}


def generate_audio(text: str, profile: str = "", language: str = "en",
                   effects: str = "") -> dict:
    """Generate speech audio from text using Voicebox TTS.

    This is the content-generation function. Useful for:
    - Creating audio versions of social media posts
    - Generating voiceovers for videos (video-creator agent)
    - Producing podcast episodes
    - Multi-voice narratives via the Stories editor

    Args:
        text: Text to synthesize (up to 50,000 chars)
        profile: Voice profile name or id to use
        language: Language code (e.g. 'en', 'ar', 'ja', 'hi', 'sw')
        effects: Named effects preset or JSON effects chain

    Returns:
        dict with generation id, audio file path, and metadata.
    """
    payload = {
        "text": text,
        "language": language,
    }
    if profile:
        payload["profile_id"] = profile
    if effects:
        payload["effects"] = effects

    return _api_post("/generate", payload)


def validate_credentials() -> bool:
    """Test if Voicebox is running and reachable.

    Voicebox doesn't use API keys — it's a local app.
    This checks that the service is running on localhost:17493.
    """
    return is_running()


# ─────────────────────────────────────────────────────────
# OpenCode Adapter Interface — post() for text-to-audio
# ─────────────────────────────────────────────────────────

def post(text: str = "", media: str = "", schedule: str = "",
         hashtags: list = None, first_comment: str = "",
         dry_run: bool = False) -> dict:
    """Generate audio from text content (Voicebox-equivalent of 'posting').

    Unlike social media adapters which post to external platforms,
    Voicebox generates spoken audio from text. This function bridges
    the content pipeline: text → speech → audio file.

    The generated audio can then be used by:
    - post.sh as media for video/social posts
    - video-creator agent as voiceover tracks
    - content-gen.py for podcast episodes

    Args:
        text: Text content to convert to speech
        media: Not used (Voicebox generates audio, doesn't post media)
        schedule: Not used (generation is instant)
        hashtags: Not used
        first_comment: Not used
        dry_run: If True, show what would be generated

    Returns:
        dict with success, post_url (path to audio file), post_id (generation id), error
    """
    if not text:
        return {"success": False, "post_url": None, "post_id": None,
                "error": "No text provided for speech generation"}

    if dry_run:
        return {
            "success": True,
            "post_url": None,
            "post_id": None,
            "error": None,
            "preview": {
                "text": text[:200] + "..." if len(text) > 200 else text,
                "engine": "voicebox",
                "char_count": len(text),
            }
        }

    result = generate_audio(text=text)

    if "error" in result:
        return {"success": False, "post_url": None, "post_id": None,
                "error": result["error"]}

    return {
        "success": True,
        "post_url": result.get("audio_url", result.get("file_path", "")),
        "post_id": result.get("id", ""),
        "error": None,
        "duration_s": result.get("duration_s", 0),
        "language": result.get("language", "en"),
    }


# ─────────────────────────────────────────────────────────
# Convenience: speak a platform manager report
# ─────────────────────────────────────────────────────────

def speak_report(report_text: str, profile: str = "Morgan",
                 client_id: str = "platform-manager") -> dict:
    """Speak a platform manager analytics report aloud.

    Shorthand for platform-manager to read analytics results.

    Args:
        report_text: Report text to speak
        profile: Voice profile to use
        client_id: Client identifier

    Returns:
        dict from speak()
    """
    return speak(text=report_text, profile=profile, client_id=client_id)

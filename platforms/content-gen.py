#!/usr/bin/env python3
"""
AI Content Generator — Platform Manager
=========================================
Generates images, videos, and captions using either a local AI API
(localhost:7777) or Google Gemini (for text: captions, hashtags).

Usage:
  python3 content-gen.py image --prompt "A sunset over mountains" --output sunset.png
  python3 content-gen.py video --prompt "A dog running on a beach" --output dog.mp4
  python3 content-gen.py caption --topic "AI automation" --platform twitter
  python3 content-gen.py hashtags --topic "vegan recipes" --platform instagram
"""

import json
import os
import sys
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"
TOKENS_DIR = PLATFORMS_DIR / "tokens"
POOL_FILE = TOKENS_DIR / "pool.json"
API_ENDPOINT = os.environ.get("AI_API_ENDPOINT", "http://localhost:7777/v1")
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.1-flash-lite")

# ─── Credential Pool ───
def load_pool() -> dict:
    """Load credential pool from disk."""
    if POOL_FILE.exists():
        return json.loads(POOL_FILE.read_text())
    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "providers": {
            "ai_api": [
                {
                    "id": "local",
                    "label": "Local AI",
                    "base_url": API_ENDPOINT,
                    "priority": 0,
                    "last_status": None,
                    "last_error_at": None,
                    "unhealthy_until": None,
                    "request_count": 0,
                    "error_count": 0,
                }
            ]
        },
        "settings": {
            "unhealthy_timeout_seconds": 60,
            "max_retries": 2,
            "request_timeout": 300,
        },
    }


def save_pool(pool: dict):
    """Save credential pool state (health tracking) to disk."""
    pool["updated_at"] = datetime.now(timezone.utc).isoformat()
    POOL_FILE.write_text(json.dumps(pool, indent=2))


def get_healthy_endpoints(pool: dict) -> list:
    """Return sorted list of healthy endpoints (by priority)."""
    now = datetime.now(timezone.utc).isoformat()
    healthy = []
    for ep in pool["providers"].get("ai_api", []):
        if ep.get("unhealthy_until") and ep["unhealthy_until"] > now:
            continue  # Skip unhealthy endpoints
        healthy.append(ep)
    return sorted(healthy, key=lambda e: e.get("priority", 999))


def mark_unhealthy(pool: dict, ep_id: str):
    """Mark an endpoint as unhealthy for the configured timeout."""
    timeout = pool["settings"].get("unhealthy_timeout_seconds", 60)
    for ep in pool["providers"].get("ai_api", []):
        if ep["id"] == ep_id:
            ep["error_count"] = ep.get("error_count", 0) + 1
            ep["last_error_at"] = datetime.now(timezone.utc).isoformat()
            unhealthy_until = (datetime.now(timezone.utc) + timedelta(seconds=timeout)).isoformat()
            ep["unhealthy_until"] = unhealthy_until
            save_pool(pool)
            return


def mark_healthy(pool: dict, ep_id: str):
    """Mark an endpoint as healthy after successful request."""
    for ep in pool["providers"].get("ai_api", []):
        if ep["id"] == ep_id:
            ep["last_status"] = "ok"
            ep["unhealthy_until"] = None
            ep["request_count"] = ep.get("request_count", 0) + 1
            save_pool(pool)
            return

# ─── Colors ───
class C:
    R = "\033[0;31m"
    G = "\033[0;32m"
    Y = "\033[1;33m"
    B = "\033[0;34m"
    CY = "\033[0;36m"
    M = "\033[0;35m"
    N = "\033[0m"


# ─── Gemini Text Backend ───
def gemini_text_request(system_prompt: str, user_prompt: str,
                        max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """Generate text using Google Gemini API via direct HTTP call.

    Falls back gracefully if the API key is missing or the request fails.
    """
    if not GEMINI_API_KEY:
        print(f"{C.Y}⚠ GOOGLE_API_KEY not set. Gemini backend unavailable.{C.N}")
        print(f"{C.Y}  Set it in your .env or export GOOGLE_API_KEY=...{C.N}")
        return ""

    combined = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

    # Build request body as proper JSON to avoid escape issues
    request_body = json.dumps({
        "contents": [{"parts": [{"text": combined}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        }
    })
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    try:
        req = urllib.request.Request(
            url,
            data=request_body.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            output = json.loads(resp.read())

        candidates = output.get("candidates", [])
        if not candidates:
            reason = output.get("promptFeedback", {}).get("blockReason", "unknown")
            print(f"{C.Y}⚠ Gemini blocked: {reason}{C.N}")
            return ""

        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return text.strip()

    except subprocess.TimeoutExpired:
        print(f"{C.Y}⚠ Gemini request timed out after 30s{C.N}")
        return ""
    except json.JSONDecodeError:
        print(f"{C.Y}⚠ Gemini returned invalid JSON{C.N}")
        return ""
    except Exception as e:
        print(f"{C.Y}⚠ Gemini error: {e}{C.N}")
        return ""


# ─── Image Generation Models ───
IMAGE_MODELS = {
    "z-image-turbo": {"desc": "Fast, 6B params, Apache 2.0", "vram": "16GB"},
    "qwen-image": {"desc": "Text-heavy designs, 20B params", "vram": "24GB"},
    "hidream": {"desc": "Top quality, 8B params", "vram": "24GB"},
    "flux-klein": {"desc": "Real-time, 9B params", "vram": "13GB"},
    "sd-3.5": {"desc": "Community LoRAs, 8B params", "vram": "8GB"},
}

# ─── Video Generation Models ───
VIDEO_MODELS = {
    "wan-2.1": {"desc": "Best quality, 14B, Apache 2.0", "vram": "16GB"},
    "ltx-2.3": {"desc": "Fast, 1080p, OpenRAIL-M", "vram": "8GB"},
    "hunyuan-video": {"desc": "Cinematic, 13B params", "vram": "24GB"},
}


def api_request(endpoint: str, payload: dict, pool_provider: str = "ai_api") -> dict:
    """Make a request with credential pool failover.

    Tries endpoints in priority order, skipping unhealthy ones.
    Marks endpoints unhealthy on failure, retries next endpoint.
    """
    pool = load_pool()
    healthy = get_healthy_endpoints(pool)
    max_retries = pool["settings"].get("max_retries", 2)
    last_error = None

    if not healthy:
        print(f"{C.Y}⚠ No healthy AI API endpoints{C.N}")
        print(f"{C.Y}  For image/video: run setup-free-models.sh (needs GPU){C.N}")
        print(f"{C.Y}  Or use --backend gemini for captions/hashtags{C.N}")
        return None  # Return None instead of crashing

    for attempt in range(max_retries + 1):
        for ep in healthy:
            base_url = ep.get("base_url", API_ENDPOINT)
            url = f"{base_url}/{endpoint.lstrip('/')}"
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=pool["settings"].get("request_timeout", 300)) as resp:
                    result = json.loads(resp.read())
                mark_healthy(pool, ep["id"])
                return result
            except urllib.error.URLError as e:
                last_error = e
                if isinstance(e.reason, ConnectionRefusedError):
                    print(f"{C.Y}⚠ Endpoint '{ep['id']}' not reachable ({ep['base_url']}){C.N}")
                else:
                    print(f"{C.Y}⚠ Endpoint '{ep['id']}' error: {e}{C.N}")
                mark_unhealthy(pool, ep["id"])
                continue
            except json.JSONDecodeError as e:
                last_error = e
                print(f"{C.Y}⚠ Endpoint '{ep['id']}' returned invalid JSON{C.N}")
                mark_unhealthy(pool, ep["id"])
                continue
            except Exception as e:
                last_error = e
                print(f"{C.Y}⚠ Endpoint '{ep['id']}' exception: {e}{C.N}")
                mark_unhealthy(pool, ep["id"])
                continue

        # All endpoints failed this attempt — reload pool for fresh health data
        pool = load_pool()
        healthy = get_healthy_endpoints(pool)
        if not healthy:
            break

    print(f"{C.Y}⚠ Local AI API unavailable — no GPU backend running{C.N}")
    if last_error:
        print(f"  Last error: {last_error}")
    return None  # Return None instead of crashing


def generate_image(prompt: str, output: str, model: str = "z-image-turbo",
                   size: str = "1024x1024") -> str:
    """Generate an image using a free local model."""
    print(f"{C.CY}Generating image...{C.N}")
    print(f"  Model: {C.Y}{model}{C.N}")
    print(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"  Size: {size}")

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
    }

    result = api_request("images/generations", payload)

    if result is None:
        print(f"{C.R}✗ Image generation unavailable — no local GPU server running{C.N}")
        print(f"{C.Y}  Run setup-free-models.sh if you have an NVIDIA GPU{C.N}")
        return output

    # Extract image data (format depends on API)
    image_url = None
    if "data" in result and len(result["data"]) > 0:
        item = result["data"][0]
        image_url = item.get("url") or item.get("b64_json")

    if image_url and image_url.startswith("http"):
        try:
            urllib.request.urlretrieve(image_url, output)
            print(f"{C.G}✓ Image saved: {output}{C.N}")
            return output
        except Exception as e:
            print(f"{C.R}Failed to download: {e}{C.N}")
    elif image_url and image_url.startswith("data:"):
        import base64
        b64_data = image_url.split(",")[1]
        with open(output, "wb") as f:
            f.write(base64.b64decode(b64_data))
        print(f"{C.G}✓ Image saved: {output}{C.N}")
        return output
    else:
        debug_file = output + ".json"
        with open(debug_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"{C.Y}Raw response saved to: {debug_file}{C.N}")
        print(f"{C.Y}Image URL: {image_url}{C.N}")

    return output


def generate_video(prompt: str, output: str, model: str = "wan-2.1",
                   duration: int = 5) -> str:
    """Generate a video using a free local model."""
    print(f"{C.CY}Generating video...{C.N}")
    print(f"  Model: {C.Y}{model}{C.N}")
    print(f"  Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"  Duration: {duration}s")

    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
    }

    result = api_request("videos/generations", payload)

    if result is None:
        print(f"{C.R}✗ Video generation unavailable — no local GPU server running{C.N}")
        print(f"{C.Y}  Run setup-free-models.sh if you have an NVIDIA GPU{C.N}")
        return output

    if "data" in result and len(result["data"]) > 0:
        video_url = result["data"][0].get("url")
        if video_url and video_url.startswith("http"):
            try:
                urllib.request.urlretrieve(video_url, output)
                print(f"{C.G}✓ Video saved: {output}{C.N}")
                return output
            except Exception as e:
                print(f"{C.R}Failed to download: {e}{C.N}")

    debug_file = output + ".json"
    with open(debug_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"{C.Y}Raw response saved to: {debug_file}{C.N}")
    return output


# ─── Caption Templates ───
CAPTION_TEMPLATES = {
    "twitter": {
        "style": "concise, witty, use emojis sparingly",
        "max_length": 280,
        "hashtag_count": "1-2",
        "tone": "conversational",
    },
    "linkedin": {
        "style": "professional, thought-leadership, story-driven",
        "max_length": 3000,
        "hashtag_count": "3-5",
        "tone": "authoritative but approachable",
    },
    "instagram": {
        "style": "emotional, visual-descriptive, use line breaks",
        "max_length": 2200,
        "hashtag_count": "10-20",
        "tone": "inspiring, personal",
    },
    "facebook": {
        "style": "engaging, question-based, community-focused",
        "max_length": 63206,
        "hashtag_count": "1-3",
        "tone": "friendly, conversational",
    },
    "tiktok": {
        "style": "short, punchy, trend-aware, hook in first 2 seconds",
        "max_length": 2200,
        "hashtag_count": "3-5",
        "tone": "casual, energetic",
    },
    "threads": {
        "style": "casual, conversational, opinion-driven",
        "max_length": 500,
        "hashtag_count": "1-3",
        "tone": "personal, authentic",
    },
    "bluesky": {
        "style": "direct, conversational, link-friendly",
        "max_length": 300,
        "hashtag_count": "1-2",
        "tone": "authentic, professional",
    },
    "mastodon": {
        "style": "thoughtful, community-oriented, content-warning-aware",
        "max_length": 500,
        "hashtag_count": "2-4",
        "tone": "respectful, informative",
    },
    "pinterest": {
        "style": "descriptive, keyword-rich, actionable",
        "max_length": 500,
        "hashtag_count": "5-10",
        "tone": "helpful, inspirational",
    },
    "youtube": {
        "style": "descriptive, keyword-optimized, include timestamps",
        "max_length": 5000,
        "hashtag_count": "2-3",
        "tone": "informative, engaging",
    },
}


def generate_caption(topic: str, platform: str = "twitter",
                     tone: str = None, include_cta: bool = True,
                     backend: str = "gemini") -> str:
    """Generate a caption for a specific platform."""
    plat = platform.lower()
    template = CAPTION_TEMPLATES.get(plat, CAPTION_TEMPLATES["twitter"])

    style = template["style"]
    max_len = template["max_length"]
    tags = template["hashtag_count"]
    default_tone = template["tone"]
    tone_str = tone or default_tone

    system_prompt = (
        f"You are a social media copywriter. Write a {tone_str} post for {plat.capitalize()}.\n"
        f"Style: {style}\n"
        f"Max length: {max_len} characters\n"
        f"Hashtags: {tags}\n"
    )
    if include_cta:
        system_prompt += "Include a call-to-action.\n"
    system_prompt += "\nReturn ONLY the post text, no explanations."

    user_prompt = f"Write a post about: {topic}"

    print(f"{C.CY}Generating caption for {plat}...{C.N}")

    if backend == "gemini":
        caption = gemini_text_request(system_prompt, user_prompt, min(max_len, 1024))
        if caption:
            if len(caption) > max_len:
                caption = caption[: max_len - 3] + "..."
            print(f"{C.G}✓ Caption generated via Gemini ({len(caption)} chars){C.N}")
            return caption.strip()
        print(f"{C.Y}Gemini failed, falling back to local API...{C.N}")

    # Fallback to local API
    payload = {
        "model": "qwen-image",
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "max_tokens": min(max_len, 1024),
    }
    result = api_request("chat/completions", payload)
    if result and "choices" in result and len(result["choices"]) > 0:
        caption = result["choices"][0].get("message", {}).get("content", "")
        if len(caption) > max_len:
            caption = caption[: max_len - 3] + "..."
        print(f"{C.G}✓ Caption generated ({len(caption)} chars){C.N}")
        return caption.strip()

    print(f"{C.Y}Could not generate caption, using template{C.N}")
    return f"Check out this {topic}! # {topic.replace(' ', '')}"


def generate_hashtags(topic: str, platform: str = "instagram", count: int = 10,
                      backend: str = "gemini") -> list:
    """Generate relevant hashtags for a topic and platform."""
    plat = platform.lower()
    tags = CAPTION_TEMPLATES.get(plat, CAPTION_TEMPLATES["instagram"])
    max_tags = tags["hashtag_count"]
    if isinstance(max_tags, str) and "-" in max_tags:
        max_tags = int(max_tags.split("-")[1])

    prompt = (
        f"Generate {min(count, int(max_tags))} relevant hashtags for a {plat} post about: {topic}\n"
        f"Return ONLY the hashtags, one per line, starting with #.\n"
        f"Make them specific, not generic."
    )

    print(f"{C.CY}Generating hashtags for {plat}...{C.N}")

    hashtags = []

    if backend == "gemini":
        result = gemini_text_request("", prompt, max_tokens=200, temperature=0.5)
        if result:
            for line in result.strip().split("\n"):
                line = line.strip().strip("#")
                if line and not line.startswith("```"):
                    hashtags.append(f"#{line.replace(' ', '')}")
            if hashtags:
                print(f"{C.G}✓ {len(hashtags)} hashtags generated via Gemini{C.N}")
                return hashtags
        print(f"{C.Y}Gemini failed, falling back to local API...{C.N}")

    # Fallback to local API
    payload = {
        "model": "qwen-image",
        "prompt": prompt,
        "max_tokens": 200,
    }
    result = api_request("chat/completions", payload)
    if "choices" in result and len(result["choices"]) > 0:
        content = result["choices"][0].get("message", {}).get("content", "")
        for line in content.strip().split("\n"):
            line = line.strip().strip("#")
            if line and not line.startswith("```"):
                hashtags.append(f"#{line.replace(' ', '')}")

    if not hashtags:
        # Fallback
        keywords = topic.lower().split()
        hashtags = [f"#{kw}" for kw in keywords[:count]]

    print(f"{C.G}✓ {len(hashtags)} hashtags generated{C.N}")
    return hashtags


def list_models(model_type: str = "all"):
    """List available models."""
    if model_type in ("image", "all"):
        print(f"\n{C.CY}Image Models:{C.N}")
        for name, info in IMAGE_MODELS.items():
            print(f"  {C.Y}{name:<18}{C.N} {info['desc']} ({info['vram']})")

    if model_type in ("video", "all"):
        print(f"\n{C.CY}Video Models:{C.N}")
        for name, info in VIDEO_MODELS.items():
            print(f"  {C.Y}{name:<18}{C.N} {info['desc']} ({info['vram']})")


def main():
    parser = argparse.ArgumentParser(
        description="AI Content Generator — Platform Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", help="Command")

    # image
    img = sub.add_parser("image", help="Generate an image (needs local GPU server)")
    img.add_argument("--prompt", required=True, help="Image description")
    img.add_argument("--output", "-o", default="output.png", help="Output file path")
    img.add_argument("--model", choices=list(IMAGE_MODELS.keys()) + ["auto"],
                     default="z-image-turbo", help="AI model to use")
    img.add_argument("--size", default="1024x1024",
                     help="Image size (e.g. 1024x1024, 1920x1080)")

    # video
    vid = sub.add_parser("video", help="Generate a video (needs local GPU server)")
    vid.add_argument("--prompt", required=True, help="Video description")
    vid.add_argument("--output", "-o", default="output.mp4", help="Output file path")
    vid.add_argument("--model", choices=list(VIDEO_MODELS.keys()) + ["auto"],
                     default="wan-2.1", help="AI model to use")
    vid.add_argument("--duration", type=int, default=5, help="Duration in seconds")

    # caption
    cap = sub.add_parser("caption", help="Generate a caption")
    cap.add_argument("--topic", required=True, help="Topic or description")
    cap.add_argument("--platform", default="twitter",
                     choices=list(CAPTION_TEMPLATES.keys()) + ["auto"],
                     help="Target platform")
    cap.add_argument("--tone", help="Override tone (e.g. 'humorous', 'professional')")
    cap.add_argument("--no-cta", action="store_true", help="Skip call-to-action")
    cap.add_argument("--backend", default="gemini", choices=["gemini", "local"],
                     help="AI backend (gemini = Google Gemini, no setup needed)")

    # hashtags
    ht = sub.add_parser("hashtags", help="Generate hashtags")
    ht.add_argument("--topic", required=True, help="Topic")
    ht.add_argument("--platform", default="instagram",
                     choices=list(CAPTION_TEMPLATES.keys()) + ["auto"])
    ht.add_argument("--count", type=int, default=10, help="Number of hashtags")
    ht.add_argument("--backend", default="gemini", choices=["gemini", "local"],
                     help="AI backend (gemini = free, local = needs GPU server)")

    # models
    sub.add_parser("models", help="List available models")

    # test (health check)
    test = sub.add_parser("test", help="Test API connectivity")
    test.add_argument("--endpoint", default=API_ENDPOINT, help="API endpoint to test")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "image":
        generate_image(args.prompt, args.output, args.model, args.size)
    elif args.cmd == "video":
        generate_video(args.prompt, args.output, args.model, args.duration)
    elif args.cmd == "caption":
        backend = getattr(args, "backend", "gemini")
        caption = generate_caption(args.topic, args.platform,
                                   args.tone, not args.no_cta,
                                   backend=backend)
        print(f"\n{C.CY}{'─' * 50}{C.N}")
        print(caption)
        print(f"{C.CY}{'─' * 50}{C.N}")
    elif args.cmd == "hashtags":
        backend = getattr(args, "backend", "gemini")
        hashtags = generate_hashtags(args.topic, args.platform, args.count,
                                     backend=backend)
        print(f"\n{' '.join(hashtags)}")
    elif args.cmd == "models":
        list_models()
    elif args.cmd == "test":
        print(f"{C.CY}═══ Credential Pool Health ═══{C.N}")
        pool = load_pool()
        healthy = get_healthy_endpoints(pool)
        for ep in pool["providers"].get("ai_api", []):
            status = "🟢 healthy" if ep in healthy else "🔴 unhealthy"
            if ep.get("unhealthy_until"):
                status += f" (until {ep['unhealthy_until']})"
            print(f"  {status}  {ep.get('id','?')}:{ep.get('base_url','?')}")
            print(f"         requests={ep.get('request_count',0)}  errors={ep.get('error_count',0)}")

        print(f"\n{C.CY}═══ Testing Endpoints ═══{C.N}")
        for ep in healthy:
            try:
                req = urllib.request.Request(f"{ep['base_url']}/models")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    models = data.get("data", [])
                    print(f"  {C.G}✓{C.N} {ep['id']}: connected ({len(models)} models)")
            except Exception as e:
                print(f"  {C.R}✗{C.N} {ep['id']}: {e}")
                mark_unhealthy(pool, ep["id"])

        if not healthy:
            print(f"{C.R}✗ No healthy endpoints{C.N}")
            print(f"{C.Y}Start one with: ~/.config/opencode/scripts/setup-free-models.sh{C.N}")
            sys.exit(1)


if __name__ == "__main__":
    main()

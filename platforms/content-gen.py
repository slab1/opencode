#!/usr/bin/env python3
"""
AI Content Generator — Platform Manager
=========================================
Generates images, videos, and captions using free local AI models
running at localhost:7777 (or configurable endpoint).

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
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"
API_ENDPOINT = os.environ.get("AI_API_ENDPOINT", "http://localhost:7777/v1")

# ─── Colors ───
class C:
    R = "\033[0;31m"
    G = "\033[0;32m"
    Y = "\033[1;33m"
    B = "\033[0;34m"
    CY = "\033[0;36m"
    M = "\033[0;35m"
    N = "\033[0m"


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


def api_request(endpoint: str, payload: dict) -> dict:
    """Make a request to the AI API at localhost:7777."""
    url = f"{API_ENDPOINT}/{endpoint.lstrip('/')}"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        if isinstance(e.reason, ConnectionRefusedError):
            print(f"{C.R}Error: AI API not running at {API_ENDPOINT}{C.N}")
            print(f"{C.Y}Start it with: ~/.config/opencode/scripts/setup-free-models.sh{C.N}")
            sys.exit(1)
        print(f"{C.R}API Error: {e}{C.N}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"{C.R}Error: Invalid JSON response from API{C.N}")
        sys.exit(1)


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

    # Extract image data (format depends on API)
    image_url = None
    if "data" in result and len(result["data"]) > 0:
        item = result["data"][0]
        image_url = item.get("url") or item.get("b64_json")

    if image_url and image_url.startswith("http"):
        # Download the image
        try:
            urllib.request.urlretrieve(image_url, output)
            print(f"{C.G}✓ Image saved: {output}{C.N}")
            return output
        except Exception as e:
            print(f"{C.R}Failed to download: {e}{C.N}")
    elif image_url and image_url.startswith("data:"):
        # Base64 encoded
        import base64
        b64_data = image_url.split(",")[1]
        with open(output, "wb") as f:
            f.write(base64.b64decode(b64_data))
        print(f"{C.G}✓ Image saved: {output}{C.N}")
        return output
    else:
        # Save the raw response for debugging
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
                     tone: str = None, include_cta: bool = True) -> str:
    """Generate a caption for a specific platform."""
    plat = platform.lower()
    template = CAPTION_TEMPLATES.get(plat, CAPTION_TEMPLATES["twitter"])

    style = template["style"]
    max_len = template["max_length"]
    tags = template["hashtag_count"]
    default_tone = template["tone"]
    tone_str = tone or default_tone

    prompt = (
        f"Write a {tone_str} social media post for {plat.capitalize()} about: {topic}\n\n"
        f"Style: {style}\n"
        f"Max length: {max_len} characters\n"
        f"Hashtags: {tags}\n"
    )
    if include_cta:
        prompt += "Include a call-to-action.\n"

    print(f"{C.CY}Generating caption for {plat}...{C.N}")

    payload = {
        "model": "qwen-image",  # Use the text-capable model
        "prompt": prompt,
        "max_tokens": min(max_len, 1024),
    }

    result = api_request("chat/completions", payload)

    if "choices" in result and len(result["choices"]) > 0:
        caption = result["choices"][0].get("message", {}).get("content", "")
        # Truncate to max length
        if len(caption) > max_len:
            caption = caption[: max_len - 3] + "..."
        print(f"{C.G}✓ Caption generated ({len(caption)} chars){C.N}")
        return caption.strip()

    print(f"{C.Y}Could not generate caption, using template{C.N}")
    return f"Check out this {topic}! # {topic.replace(' ', '')}"


def generate_hashtags(topic: str, platform: str = "instagram", count: int = 10) -> list:
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

    payload = {
        "model": "qwen-image",
        "prompt": prompt,
        "max_tokens": 200,
    }

    result = api_request("chat/completions", payload)

    hashtags = []
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
    img = sub.add_parser("image", help="Generate an image")
    img.add_argument("--prompt", required=True, help="Image description")
    img.add_argument("--output", "-o", default="output.png", help="Output file path")
    img.add_argument("--model", choices=list(IMAGE_MODELS.keys()) + ["auto"],
                     default="z-image-turbo", help="AI model to use")
    img.add_argument("--size", default="1024x1024",
                     help="Image size (e.g. 1024x1024, 1920x1080)")

    # video
    vid = sub.add_parser("video", help="Generate a video")
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

    # hashtags
    ht = sub.add_parser("hashtags", help="Generate hashtags")
    ht.add_argument("--topic", required=True, help="Topic")
    ht.add_argument("--platform", default="instagram",
                    choices=list(CAPTION_TEMPLATES.keys()) + ["auto"])
    ht.add_argument("--count", type=int, default=10, help="Number of hashtags")

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
        caption = generate_caption(args.topic, args.platform,
                                   args.tone, not args.no_cta)
        print(f"\n{C.CY}{'─' * 50}{C.N}")
        print(caption)
        print(f"{C.CY}{'─' * 50}{C.N}")
    elif args.cmd == "hashtags":
        hashtags = generate_hashtags(args.topic, args.platform, args.count)
        print(f"\n{' '.join(hashtags)}")
    elif args.cmd == "models":
        list_models()
    elif args.cmd == "test":
        try:
            req = urllib.request.Request(f"{args.endpoint}/models")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = data.get("data", [])
                print(f"{C.G}✓ API connected at {args.endpoint}{C.N}")
                print(f"{C.B}Available models: {len(models)}{C.N}")
        except Exception as e:
            print(f"{C.R}✗ API not reachable at {args.endpoint}{C.N}")
            print(f"  {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

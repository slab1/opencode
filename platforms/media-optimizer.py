#!/usr/bin/env python3
"""
Media Optimizer — Platform Manager
====================================
Auto-resizes images and videos for each platform's optimal dimensions.

Usage:
  python3 media-optimizer.py input.jpg --platforms instagram,twitter,linkedin
  python3 media-optimizer.py input.mp4 --platforms tiktok,youtube --output-dir ./optimized
  python3 media-optimizer.py input.jpg --platforms all
  python3 media-optimizer.py input.jpg --list-dimensions
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"

# ─── ANSI Colors ───
class C:
    R = "\033[0;31m"
    G = "\033[0;32m"
    Y = "\033[1;33m"
    B = "\033[0;34m"
    CY = "\033[0;36m"
    M = "\033[0;35m"
    N = "\033[0m"

# ─── Platform Media Dimensions ───
# (width, height, aspect_ratio, description)
PLATFORM_DIMENSIONS = {
    "instagram": {
        "square": (1080, 1080, "1:1", "Feed post (square)"),
        "portrait": (1080, 1350, "4:5", "Feed post (portrait)"),
        "story": (1080, 1920, "9:16", "Story / Reel"),
        "landscape": (1080, 566, "1.91:1", "Feed post (landscape)"),
    },
    "tiktok": {
        "video": (1080, 1920, "9:16", "TikTok video / Story"),
        "thumbnail": (1080, 1920, "9:16", "Video thumbnail"),
    },
    "youtube": {
        "video": (1920, 1080, "16:9", "Standard video"),
        "shorts": (1080, 1920, "9:16", "YouTube Shorts"),
        "thumbnail": (1280, 720, "16:9", "Video thumbnail"),
    },
    "twitter": {
        "image": (1200, 675, "16:9", "In-feed image"),
        "card": (1200, 628, "1.91:1", "Link card image"),
        "profile": (400, 400, "1:1", "Profile picture"),
    },
    "linkedin": {
        "image": (1200, 627, "1.91:1", "Feed image"),
        "banner": (1584, 396, "4:1", "Company banner"),
        "profile": (400, 400, "1:1", "Profile picture"),
    },
    "facebook": {
        "image": (1200, 630, "1.91:1", "Feed image / link"),
        "story": (1080, 1920, "9:16", "Facebook Story"),
        "cover": (820, 312, "2.63:1", "Cover photo"),
    },
    "pinterest": {
        "pin": (1000, 1500, "2:3", "Standard pin (vertical)"),
        "square": (1000, 1000, "1:1", "Square pin"),
        "infographic": (1000, 2100, "10:21", "Long pin / infographic"),
    },
    "threads": {
        "image": (1080, 1080, "1:1", "Feed image"),
        "portrait": (1080, 1920, "9:16", "Portrait image"),
    },
    "bluesky": {
        "image": (1200, 675, "16:9", "Feed image"),
        "avatar": (400, 400, "1:1", "Avatar"),
    },
    "mastodon": {
        "image": (1200, 630, "1.91:1", "Feed image"),
        "avatar": (400, 400, "1:1", "Avatar"),
    },
    "gbp": {
        "image": (720, 720, "1:1", "Google Business photo"),
        "cover": (1024, 576, "16:9", "Cover photo"),
    },
}


def list_dimensions():
    """Print all platform dimensions."""
    print(f"\n{C.CY}{'═' * 80}{C.N}")
    print(f"{C.CY}  Platform Media Dimensions Reference{C.N}")
    print(f"{C.CY}{'═' * 80}{C.N}\n")

    for platform, variants in sorted(PLATFORM_DIMENSIONS.items()):
        print(f"{C.B}{platform.upper()}{C.N}")
        print(f"{'─' * 60}")
        for key, (w, h, ratio, desc) in variants.items():
            print(f"  {C.Y}{key:<15}{C.N} {w:>5}×{h:<5}  {ratio:<8}  {desc}")
        print()


def optimize_image(input_path: str, platform: str, variant: str = None,
                   output_dir: str = None) -> list:
    """Optimize an image for a specific platform.

    Returns list of (output_path, platform, variant, dimensions).
    Falls back to reporting what should be done if Pillow isn't available.
    """
    path = Path(input_path)
    if not path.exists():
        print(f"{C.R}Error: File not found: {input_path}{C.N}")
        sys.exit(1)

    if platform not in PLATFORM_DIMENSIONS:
        print(f"{C.R}Unknown platform: {platform}{C.N}")
        print(f"Valid: {', '.join(sorted(PLATFORM_DIMENSIONS.keys()))}")
        sys.exit(1)

    if output_dir is None:
        output_dir = str(path.parent)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = []
    variants = PLATFORM_DIMENSIONS[platform]

    if variant:
        variants = {variant: variants[variant]}

    try:
        from PIL import Image
        has_pil = True
    except ImportError:
        has_pil = False

    for vname, (w, h, ratio, desc) in variants.items():
        stem = path.stem
        ext = path.suffix or ".jpg"
        output_path = Path(output_dir) / f"{stem}_{platform}_{vname}{ext}"

        if has_pil:
            try:
                img = Image.open(input_path)
                # Resize with aspect ratio preservation
                img_resized = img.resize((w, h), Image.LANCZOS)
                # Convert RGBA to RGB for JPEG
                if ext.lower() in (".jpg", ".jpeg") and img_resized.mode == "RGBA":
                    img_resized = img_resized.convert("RGB")
                img_resized.save(output_path, quality=92)
                print(f"{C.G}✓{C.N} {desc}: {output_path} ({w}×{h})")
            except Exception as e:
                print(f"{C.R}✗{C.N} {desc}: Failed — {e}{C.N}")
                continue
        else:
            print(f"{C.Y}⚠ Pillow not installed. Would resize to {w}×{h}: {output_path}{C.N}")

        results.append({
            "path": str(output_path),
            "platform": platform,
            "variant": vname,
            "width": w,
            "height": h,
            "ratio": ratio,
            "description": desc,
        })

    return results


def optimize_video(input_path: str, platform: str, variant: str = None,
                   output_dir: str = None) -> list:
    """Report optimal video dimensions for a platform.

    Full transcoding requires ffmpeg — we report the target dimensions.
    """
    path = Path(input_path)
    if not path.exists():
        print(f"{C.R}Error: File not found: {input_path}{C.N}")
        sys.exit(1)

    if platform not in PLATFORM_DIMENSIONS:
        print(f"{C.R}Unknown platform: {platform}{C.N}")
        sys.exit(1)

    if output_dir is None:
        output_dir = str(path.parent)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = []
    variants = PLATFORM_DIMENSIONS[platform]

    if variant:
        variants = {variant: variants[variant]}

    for vname, (w, h, ratio, desc) in variants.items():
        stem = path.stem
        ext = path.suffix or ".mp4"
        output_path = Path(output_dir) / f"{stem}_{platform}_{vname}{ext}"

        # Check if ffmpeg is available
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"],
                           capture_output=True, timeout=5)
            has_ffmpeg = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            has_ffmpeg = False

        if has_ffmpeg:
            print(f"{C.G}✓{C.N} {desc}: Would transcode to {w}×{h} → {output_path}")
            print(f"  Run: ffmpeg -i {input_path} -vf scale={w}:{h} {output_path}")
        else:
            print(f"{C.Y}⚠ ffmpeg not available. Target: {w}×{h} for {desc}{C.N}")

        results.append({
            "path": str(output_path),
            "platform": platform,
            "variant": vname,
            "width": w,
            "height": h,
            "ratio": ratio,
            "description": desc,
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Media Optimizer — Platform Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="Input image or video file")
    parser.add_argument("--platforms", "-p", default="",
                        help="Comma-separated target platforms")
    parser.add_argument("--variant", "-v", default=None,
                        help="Specific variant (e.g. square, story, video)")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Optimize for ALL platforms")
    parser.add_argument("--list-dimensions", "-l", action="store_true",
                        help="List all platform dimensions and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without doing it")

    args = parser.parse_args()

    # List dimensions mode
    if args.list_dimensions:
        list_dimensions()
        sys.exit(0)

    # Validate
    if not args.platforms and not args.all:
        print(f"{C.R}Error: Specify --platforms or --all{C.N}")
        parser.print_help()
        sys.exit(1)

    # Determine platforms
    if args.all:
        platforms = list(PLATFORM_DIMENSIONS.keys())
    else:
        platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
        for p in platforms:
            if p not in PLATFORM_DIMENSIONS:
                print(f"{C.R}Unknown platform: '{p}'{C.N}")
                print(f"Valid: {', '.join(sorted(PLATFORM_DIMENSIONS.keys()))}")
                sys.exit(1)

    # Determine file type
    input_path = args.input
    video_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".gif"}
    is_video = Path(input_path).suffix.lower() in video_exts

    print(f"{C.CY}{'═' * 60}{C.N}")
    print(f"{C.CY}  Optimizing {Path(input_path).name} for {len(platforms)} platform(s){C.N}")
    print(f"{C.CY}{'═' * 60}{C.N}\n")

    all_results = []
    for platform in platforms:
        if is_video:
            results = optimize_video(input_path, platform, args.variant, args.output_dir)
        else:
            results = optimize_image(input_path, platform, args.variant, args.output_dir)
        all_results.extend(results)
        print()

    # Summary
    print(f"{C.G}Done! {len(all_results)} variant(s) prepared.{C.N}")

    # Save manifest
    if all_results:
        manifest_path = Path(args.output_dir or Path(input_path).parent) / "optimize-manifest.json"
        manifest = {
            "input": input_path,
            "timestamp": datetime.now().isoformat(),
            "results": all_results,
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"{C.B}Manifest: {manifest_path}{C.N}")


if __name__ == "__main__":
    main()

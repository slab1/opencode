"""
CLI entry point for quick video creation.

Usage:
    python -m opencode_video --help
    python -m opencode_video create --text "Hello World" --platform tiktok --output hello.mp4
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description="OpenCode Video Creator - Programmatic video generation"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a video")
    create_parser.add_argument("--output", "-o", default="output.mp4", help="Output file")
    create_parser.add_argument("--text", "-t", nargs="+", help="Text scenes to include")
    create_parser.add_argument(
        "--images", "-i", nargs="*", help="Image paths for slideshow"
    )
    create_parser.add_argument("--audio", "-a", help="Background music path")
    create_parser.add_argument(
        "--platform", "-p", default="youtube",
        choices=["youtube", "youtube_shorts", "tiktok", "instagram_reel",
                 "instagram_post", "twitter", "linkedin", "facebook"],
        help="Target platform",
    )
    create_parser.add_argument(
        "--duration", "-d", type=float, default=5.0, help="Duration per scene (seconds)"
    )
    create_parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    create_parser.add_argument("--bg-color", default="#1a1a2e", help="Background hex color")
    create_parser.add_argument(
        "--font-size", type=int, default=48, help="Text font size"
    )
    create_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # presets command
    subparsers.add_parser("presets", help="List available platform presets")

    # compose command
    compose_parser = subparsers.add_parser("compose", help="Compose video with overlays")
    compose_parser.add_argument("main", help="Main video file")
    compose_parser.add_argument("--output", "-o", default="composed.mp4")
    compose_parser.add_argument("--platform", "-p", default="youtube")
    compose_parser.add_argument("--text", nargs="*", help="Text overlays")
    compose_parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.command == "presets":
        from .presets import list_presets

        for p in list_presets():
            print(f"  {p}")
        return

    if args.command == "create":
        from .core import create_video as cv

        texts = None
        if args.text:
            texts = [
                {
                    "text": " ".join(args.text),
                    "font_size": args.font_size,
                    "color": "white",
                }
            ]

        result = cv(
            output=args.output,
            texts=texts,
            images=args.images,
            audio=args.audio,
            platform=args.platform,
            fps=args.fps,
            duration_per_clip=args.duration,
            background_color=args.bg_color,
            verbose=args.verbose,
        )
        print(f"Video created: {result}")
        return

    if args.command == "compose":
        from .core import compose_video as comp

        overlays = []
        if args.text:
            for t in args.text:
                overlays.append({"type": "text", "source": t, "position": "center"})

        result = comp(
            main_clip=args.main,
            overlays=overlays or None,
            output=args.output,
            platform=args.platform,
            verbose=args.verbose,
        )
        print(f"Composed video: {result}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

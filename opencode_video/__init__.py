"""
OpenCode Video Creation Module
================================
Programmatic video creation across platforms using MoviePy + FFmpeg.
Supports: YouTube, TikTok, Instagram (Reels/Posts), Twitter/X.

Usage:
    from opencode_video import create_video, PlatformPreset

    # Quick video from images
    create_video(
        output="my_video.mp4",
        clips=[...],
        platform="youtube"
    )
"""

from .core import (
    create_video,
    VideoClip,
    TextClip,
    ImageClip,
    AudioClip,
    compose_video,
)
from .presets import PlatformPreset, get_preset
from .effects import fade_in, fade_out, cross_fade, zoom_in, slide_in
from .scripts import VideoScript, script_to_video, render_with_ffmpeg_crossfade
from .workflows import (
    create_tiktok_from_urls,
    create_tiktok_from_search,
    capture_web_screenshot,
)

__version__ = "1.2.0"
__all__ = [
    "create_video",
    "VideoClip",
    "TextClip",
    "ImageClip",
    "AudioClip",
    "compose_video",
    "PlatformPreset",
    "get_preset",
    "fade_in",
    "fade_out",
    "cross_fade",
    "zoom_in",
    "slide_in",
    "VideoScript",
    "script_to_video",
    "render_with_ffmpeg_crossfade",
    "create_tiktok_from_urls",
    "create_tiktok_from_search",
    "capture_web_screenshot",
]

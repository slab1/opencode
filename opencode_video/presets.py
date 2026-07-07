"""
Platform presets for video creation.
Each preset defines resolution, aspect ratio, FPS, and guidelines
for a target platform.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PlatformPreset:
    """Defines video parameters for a target platform."""

    name: str
    width: int
    height: int
    fps: int = 30
    aspect_ratio: str = "16:9"
    description: str = ""
    max_duration_seconds: Optional[int] = None
    recommended_bitrate: str = "10M"
    codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    vertical: bool = False
    square: bool = False

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def is_vertical(self) -> bool:
        return self.height > self.width

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.width}x{self.height} @ {self.fps}fps "
            f"({self.aspect_ratio})"
        )


# ---------------------------------------------------------------------------
# Platform presets
# ---------------------------------------------------------------------------

YOUTUBE_LANDSCAPE = PlatformPreset(
    name="YouTube (Landscape)",
    width=1920,
    height=1080,
    fps=30,
    aspect_ratio="16:9",
    description="Standard YouTube video in landscape 1080p",
    max_duration_seconds=None,
    recommended_bitrate="10M",
)

YOUTUBE_SHORTS = PlatformPreset(
    name="YouTube Shorts",
    width=1080,
    height=1920,
    fps=30,
    aspect_ratio="9:16",
    description="Vertical YouTube Shorts format",
    max_duration_seconds=60,
    recommended_bitrate="8M",
    vertical=True,
)

TIKTOK = PlatformPreset(
    name="TikTok",
    width=1080,
    height=1920,
    fps=30,
    aspect_ratio="9:16",
    description="TikTok vertical video",
    max_duration_seconds=180,
    recommended_bitrate="8M",
    vertical=True,
)

INSTAGRAM_REEL = PlatformPreset(
    name="Instagram Reel",
    width=1080,
    height=1920,
    fps=30,
    aspect_ratio="9:16",
    description="Instagram Reel vertical format",
    max_duration_seconds=90,
    recommended_bitrate="8M",
    vertical=True,
)

INSTAGRAM_POST = PlatformPreset(
    name="Instagram Post (Square)",
    width=1080,
    height=1080,
    fps=30,
    aspect_ratio="1:1",
    description="Instagram square post video",
    max_duration_seconds=60,
    recommended_bitrate="6M",
    square=True,
)

INSTAGRAM_LANDSCAPE = PlatformPreset(
    name="Instagram Landscape",
    width=1920,
    height=1080,
    fps=30,
    aspect_ratio="16:9",
    description="Instagram landscape video",
    max_duration_seconds=60,
    recommended_bitrate="8M",
)

TWITTER = PlatformPreset(
    name="Twitter/X",
    width=1280,
    height=720,
    fps=30,
    aspect_ratio="16:9",
    description="Twitter/X video (max 512MB, 2min 20s for most)",
    max_duration_seconds=140,
    recommended_bitrate="6M",
)

LINKEDIN = PlatformPreset(
    name="LinkedIn",
    width=1920,
    height=1080,
    fps=30,
    aspect_ratio="16:9",
    description="LinkedIn video",
    max_duration_seconds=600,
    recommended_bitrate="8M",
)

FACEBOOK = PlatformPreset(
    name="Facebook",
    width=1920,
    height=1080,
    fps=30,
    aspect_ratio="16:9",
    description="Facebook video",
    max_duration_seconds=240,
    recommended_bitrate="8M",
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PRESETS: dict[str, PlatformPreset] = {
    "youtube": YOUTUBE_LANDSCAPE,
    "youtube_shorts": YOUTUBE_SHORTS,
    "tiktok": TIKTOK,
    "instagram_reel": INSTAGRAM_REEL,
    "instagram_post": INSTAGRAM_POST,
    "instagram_landscape": INSTAGRAM_LANDSCAPE,
    "twitter": TWITTER,
    "linkedin": LINKEDIN,
    "facebook": FACEBOOK,
}


def get_preset(name: str) -> PlatformPreset:
    """Look up a platform preset by key name (case-insensitive)."""
    key = name.lower().replace(" ", "_").replace("-", "_")
    if key in _PRESETS:
        return _PRESETS[key]
    raise KeyError(
        f"Unknown preset '{name}'. Available: {', '.join(sorted(_PRESETS))}"
    )


def list_presets() -> list[PlatformPreset]:
    """Return all available platform presets."""
    return list(_PRESETS.values())

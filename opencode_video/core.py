"""
Core video creation functions for OpenCode.
Provides the main API for creating, composing, and rendering videos.
"""

import os
import logging
from typing import Optional, Union

from moviepy import (
    VideoFileClip as MpyVideoFileClip,
    ImageClip as MpyImageClip,
    TextClip as MpyTextClip,
    AudioFileClip as MpyAudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from .presets import PlatformPreset, get_preset

logger = logging.getLogger("opencode-video")


# ---------------------------------------------------------------------------
# Public helper types (thin wrappers for type hints / documentation)
# ---------------------------------------------------------------------------

class VideoClip:
    """Represents a video clip source (file path or already-loaded clip)."""
    pass


class TextClip:
    """Represents a text overlay to be composited onto a video."""
    pass


class ImageClip:
    """Represents an image overlay."""
    pass


class AudioClip:
    """Represents an audio track (background music / voiceover)."""
    pass


# ---------------------------------------------------------------------------
# Composition helpers
# ---------------------------------------------------------------------------


def _resolve_clip(
    source: Union[str, "MpyVideoFileClip", "MpyImageClip"],
) -> Union["MpyVideoFileClip", "MpyImageClip"]:
    """Load a clip from a file path if needed."""
    if isinstance(source, str):
        if source.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
            return MpyImageClip(source)
        else:
            return MpyVideoFileClip(source)
    return source


# ---------------------------------------------------------------------------
# Main creation API
# ---------------------------------------------------------------------------


def create_video(
    output: str = "output.mp4",
    clips: Optional[list] = None,
    texts: Optional[list[dict]] = None,
    images: Optional[list[str]] = None,
    audio: Optional[str] = None,
    audio_volume: float = 1.0,
    platform: Union[str, PlatformPreset] = "youtube",
    fps: int = 30,
    background_color: str = "#000000",
    transitions: Optional[list[str]] = None,
    duration_per_clip: float = 5.0,
    verbose: bool = False,
) -> str:
    """
    Create a video from various input sources.

    Args:
        output: Output file path (e.g., "my_video.mp4").
        clips: List of video file paths to concatenate.
        texts: List of dicts with keys: 'text', 'color', 'font_size', 'position'.
        images: List of image file paths to create a slideshow.
        audio: Path to audio file for background music or voiceover.
        audio_volume: Volume multiplier for the audio (0.0 - 1.0).
        platform: Target platform name or PlatformPreset object.
        fps: Frames per second.
        background_color: Hex color for backgrounds (e.g. "#1a1a2e").
        transitions: List of transition names between clips.
        duration_per_clip: Duration in seconds for images / static clips.
        verbose: If True, print progress.

    Returns:
        Path to the rendered video file.
    """
    # Resolve preset
    if isinstance(platform, str):
        preset = get_preset(platform)
    else:
        preset = platform

    w, h = preset.width, preset.height

    # Collect visual elements
    visual_clips = []

    # Add video clips
    if clips:
        for i, clip_path in enumerate(clips):
            if os.path.exists(clip_path):
                vc = MpyVideoFileClip(clip_path)
                # Resize to preset dimensions
                if vc.size != (w, h):
                    vc = vc.resized((w, h))
                visual_clips.append(vc)

    # Add image slideshow
    if images:
        for img_path in images:
            if os.path.exists(img_path):
                ic = MpyImageClip(img_path).with_duration(duration_per_clip)
                ic = ic.resized((w, h))
                visual_clips.append(ic)

    # If nothing visual was provided, create a background color clip
    if not visual_clips:
        # Create a solid color background
        def make_frame(t):
            import numpy as np

            rgb = tuple(
                int(background_color.lstrip("#")[i : i + 2], 16)
                for i in (0, 2, 4)
            )
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = rgb
            return frame

        from moviepy import VideoClip as MpyVideoClip

        bg_clip = MpyVideoClip(make_frame, duration=duration_per_clip)
        visual_clips.append(bg_clip)

    # Concatenate visual elements
    if len(visual_clips) == 1:
        final_video = visual_clips[0]
    else:
        final_video = concatenate_videoclips(visual_clips, method="chain")

    # Add text overlays
    if texts:
        text_clips_to_add = []
        for t in texts:
            try:
                txt = MpyTextClip(
                    text=t.get("text", ""),
                    color=t.get("color", "white"),
                    font_size=t.get("font_size", 48),
                    font=t.get("font", "Arial"),
                    size=(int(w * 0.9), None),
                    method="caption",
                )
                txt = txt.with_position(
                    t.get("position", "center")
                ).with_duration(final_video.duration)
                text_clips_to_add.append(txt)
            except Exception as e:
                if verbose:
                    logger.warning(f"Failed to create text overlay: {e}")

        if text_clips_to_add:
            all_clips = [final_video] + text_clips_to_add
            final_video = CompositeVideoClip(all_clips, size=(w, h))

    # Add audio
    if audio and os.path.exists(audio):
        try:
            audio_clip = MpyAudioFileClip(audio)
            if audio_volume != 1.0:
                audio_clip = audio_clip.with_volume_scaled(audio_volume)

            # Loop or trim audio to match video duration
            if audio_clip.duration < final_video.duration:
                from moviepy.audio.fx import AudioLoop
                audio_clip = AudioLoop(duration=final_video.duration).apply(audio_clip)
            else:
                audio_clip = audio_clip.with_duration(final_video.duration)
            final_video = final_video.with_audio(audio_clip)
        except Exception as e:
            if verbose:
                logger.warning(f"Failed to add audio: {e}")

    # Render
    logger_func = None if not verbose else "bar"
    final_video.write_videofile(
        output,
        fps=fps,
        codec=preset.codec,
        audio_codec=preset.audio_codec,
        preset="medium",
        bitrate=preset.recommended_bitrate,
        logger=logger_func,
    )

    # Preview via display if not already on a display
    if not os.environ.get("DISPLAY"):
        try:
            from opencode_display import ensure_display
            disp = ensure_display()
            disp.launch_video_preview(output)
        except (ImportError, Exception):
            pass

    return output


# ---------------------------------------------------------------------------
# Composite video from multiple tracks / layers
# ---------------------------------------------------------------------------


def compose_video(
    main_clip: str,
    overlays: Optional[list[dict]] = None,
    output: str = "composed.mp4",
    platform: Union[str, PlatformPreset] = "youtube",
    fps: int = 30,
    verbose: bool = False,
) -> str:
    """
    Compose a video with layered overlays (text, images, picture-in-picture).

    Args:
        main_clip: Path to the main video file.
        overlays: List of overlay dicts:
            - 'type': 'text' | 'image' | 'video'
            - 'source': text string or file path
            - 'position': (x, y) or 'center'/'top'/'bottom'
            - 'size': (width, height) for images/videos
            - 'start_time': seconds (default 0)
            - 'duration': seconds (default full duration)
        output: Output file path.
        platform: Target platform.
        fps: Frames per second.

    Returns:
        Path to the rendered video.
    """
    if isinstance(platform, str):
        preset = get_preset(platform)
    else:
        preset = platform

    w, h = preset.width, preset.height

    # Load main clip
    main = MpyVideoFileClip(main_clip)
    if main.size != (w, h):
        main = main.resized((w, h))

    layers = [main]

    if overlays:
        for ov in overlays:
            ov_type = ov.get("type", "text")
            start_time = ov.get("start_time", 0)
            duration = ov.get("duration", main.duration - start_time)
            position = ov.get("position", "center")

            try:
                if ov_type == "text":
                    clip = MpyTextClip(
                        text=ov.get("source", ""),
                        color=ov.get("color", "white"),
                        font_size=ov.get("font_size", 36),
                        font=ov.get("font", "Arial"),
                        size=(int(w * 0.9), None),
                        method="caption",
                    ).with_duration(duration).with_start(start_time).with_position(position)
                    layers.append(clip)

                elif ov_type == "image":
                    src = ov.get("source", "")
                    if os.path.exists(src):
                        clip = MpyImageClip(src).with_duration(duration).with_start(
                            start_time
                        ).with_position(position)
                        if "size" in ov:
                            clip = clip.resized(ov["size"])
                        layers.append(clip)

                elif ov_type == "video":
                    src = ov.get("source", "")
                    if os.path.exists(src):
                        pip = MpyVideoFileClip(src).with_duration(duration).with_start(
                            start_time
                        ).with_position(position)
                        if "size" in ov:
                            pip = pip.resized(ov["size"])
                        elif pip.size[0] > w // 2:
                            pip = pip.resized(width=w // 3)
                        layers.append(pip)

            except Exception as e:
                if verbose:
                    logger.warning(f"Failed to add overlay: {e}")

    final = CompositeVideoClip(layers, size=(w, h))

    final.write_videofile(
        output,
        fps=fps,
        codec=preset.codec,
        audio_codec=preset.audio_codec,
        preset="medium",
        bitrate=preset.recommended_bitrate,
        logger=None if not verbose else "bar",
    )

    return output

"""
Transition effects and clip modifiers for video creation.

Uses MoviePy 2.x API: clips use `with_effects([EffectClass(params)])`.
"""

from moviepy import (
    VideoClip,
    CompositeVideoClip,
)
from moviepy.video.fx import FadeIn, FadeOut


def fade_in(clip: VideoClip, duration: float = 0.5) -> VideoClip:
    """Apply a fade-in effect to a clip."""
    return clip.with_effects([FadeIn(duration)])


def fade_out(clip: VideoClip, duration: float = 0.5) -> VideoClip:
    """Apply a fade-out effect to a clip."""
    return clip.with_effects([FadeOut(duration)])


def cross_fade(clip1: VideoClip, clip2: VideoClip, duration: float = 0.5) -> VideoClip:
    """Cross-fade between two clips of potentially different durations."""
    clip1_faded = clip1.with_effects([FadeOut(duration)])
    clip2_faded = clip2.with_effects([FadeIn(duration)])

    # Offset clip2 to start fading in before clip1 ends
    overlap_start = clip1.duration - duration
    clip2_shifted = clip2_faded.with_start(overlap_start)

    total_duration = clip1.duration + clip2.duration - duration
    return CompositeVideoClip(
        [clip1_faded, clip2_shifted], size=clip1.size
    ).with_duration(total_duration)


def zoom_in(
    clip: VideoClip, start_zoom: float = 1.0, end_zoom: float = 1.15
) -> VideoClip:
    """Ken Burns style slow zoom in effect.

    Uses PIL for image resizing. The transform function scales up
    and center-crops the frame to create a zoom effect.
    """
    from PIL import Image
    import numpy as np

    def zoom_effect(get_frame, t):
        progress = t / clip.duration if clip.duration > 0 else 0
        zoom = start_zoom + (end_zoom - start_zoom) * progress
        frame = get_frame(t)

        h, w = frame.shape[:2]
        new_h, new_w = int(h * zoom), int(w * zoom)

        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)

        pil_img = Image.fromarray(frame)
        try:
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        except AttributeError:
            resized = pil_img.resize((new_w, new_h), Image.LAZCS)

        left = (new_w - w) // 2
        top = (new_h - h) // 2
        cropped = resized.crop((left, top, left + w, top + h))
        return np.array(cropped)

    return clip.transform(zoom_effect)


def ken_burns(clip: VideoClip, zoom_amount: float = 0.05) -> VideoClip:
    """Smooth Ken Burns slow zoom effect optimized for image backgrounds.

    Applies a subtle continuous zoom (default 5% over clip duration).
    This creates motion that forces libx264 to use higher bitrate.

    Args:
        clip: The image/video clip to animate.
        zoom_amount: Fraction to zoom over duration (0.05 = 5%).

    Returns:
        Animated clip with Ken Burns effect.
    """
    return zoom_in(clip, start_zoom=1.0, end_zoom=1.0 + zoom_amount)


def slide_in(clip: VideoClip, direction: str = "left", duration: float = 0.5) -> VideoClip:
    """Slide a clip in from a direction ('left', 'right', 'top', 'bottom')."""
    w, h = clip.size

    def pos_func(t):
        progress = min(t / duration, 1) if duration > 0 else 1
        if direction == "left":
            return (int(-w * (1 - progress)), 0)
        elif direction == "right":
            return (int(w * (1 - progress)), 0)
        elif direction == "top":
            return (0, int(-h * (1 - progress)))
        elif direction == "bottom":
            return (0, int(h * (1 - progress)))
        return (0, 0)

    return clip.with_position(pos_func)

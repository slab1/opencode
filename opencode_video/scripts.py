"""
High-level script-based video generation.
Allows defining a video as a series of "scenes" with text, images, and audio.

Supports image backgrounds (for high-bitrate content), animated backgrounds,
image overlays, and browser screenshot capture.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from moviepy import (
    TextClip as MpyTextClip,
    ImageClip as MpyImageClip,
    AudioFileClip as MpyAudioClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx import FadeIn, CrossFadeIn

from .effects import ken_burns
from .presets import PlatformPreset, get_preset


# ---------------------------------------------------------------------------
# Script data structures
# ---------------------------------------------------------------------------


@dataclass
class Scene:
    """A single scene in a video script.

    For high-bitrate content (4+ Mbps), use ``background_image`` or
    ``image_overlays`` instead of relying solely on animated gradients.
    """

    text: str = ""
    image_path: Optional[str] = None        # single centered image overlay
    background_image: Optional[str] = None  # fill-frame background image
    image_overlays: list[dict] = field(default_factory=list)
    background_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    duration: float = 5.0
    font_size: int = 48
    animation: str = "fade_in"
    background_animation: str = "none"
    sound_effect: Optional[str] = None


@dataclass
class VideoScript:
    """A complete video script with scenes, music, and platform settings."""

    title: str = "Untitled Video"
    scenes: list[Scene] = field(default_factory=list)
    background_music: Optional[str] = None
    music_volume: float = 0.3
    voiceover: Optional[str] = None
    intro_scene: Optional[Scene] = None
    outro_scene: Optional[Scene] = None
    platform: str = "youtube"
    fps: int = 30
    output_path: str = "output.mp4"
    transition_duration: float = 0.0
    threads: int = 0
    ffmpeg_preset: str = "ultrafast"
    ffmpeg_params: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Browser screenshot capture utility
# ---------------------------------------------------------------------------


def capture_browser_screenshot(
    url: str,
    output_path: str = "/tmp/video_screenshot.png",
    width: int = 1920,
    height: int = 1080,
    wait_ms: int = 2000,
) -> str:
    """Capture a full-page screenshot of a URL for use as video background.

    Uses the ``opencode_web`` browser module.  Falls back to generating a
    simple gradient placeholder if the browser is unavailable.

    Returns the path to the saved screenshot.
    """
    try:
        from opencode_web import Browser

        with Browser(headless=True) as b:
            b.navigate(url)
            b.wait(wait_ms)
            b.screenshot(output_path)
        return output_path
    except (ImportError, Exception):
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            r = int(20 + (y / height) * 60)
            g = int(20 + (y / height) * 40)
            b_val = int(60 + (y / height) * 80)
            draw.line([(0, y), (width, y)], fill=(r, g, b_val))
        img.save(output_path)
        return output_path


# ---------------------------------------------------------------------------
# Script to video conversion
# ---------------------------------------------------------------------------


def _create_scene_clip(scene: Scene, preset: PlatformPreset):
    """Create a video clip for a single scene."""
    import numpy as np
    from moviepy import VideoClip as MpyVideoClip

    w, h = preset.width, preset.height

    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i: i + 2], 16) for i in (0, 2, 4))

    bg_rgb = hex_to_rgb(scene.background_color)

    bg_clip = None

    if scene.background_image and os.path.exists(scene.background_image):
        img_bg = MpyImageClip(scene.background_image).with_duration(scene.duration)
        iw, ih = img_bg.size
        scale = max(w / iw, h / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)
        img_bg = img_bg.resized((new_w, new_h))
        x_off = (new_w - w) // 2
        y_off = (new_h - h) // 2
        img_bg = img_bg.cropped(x1=x_off, y1=y_off, x2=x_off + w, y2=y_off + h)
        bg_clip = img_bg
        if scene.background_animation in ("ken_burns", "none"):
            bg_clip = ken_burns(bg_clip, zoom_amount=0.04)

    elif scene.background_animation == "gradient_shift":
        r1, g1, b1 = bg_rgb
        r2, g2, b2 = [min(255, c + 40) for c in bg_rgb]

        def make_frame(t):
            progress = (t / scene.duration) % 1.0
            factor = 0.5 + 0.5 * np.sin(progress * 2 * np.pi)
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = (
                int(r1 + (r2 - r1) * factor),
                int(g1 + (g2 - g1) * factor),
                int(b1 + (b2 - b1) * factor),
            )
            return frame

        bg_clip = MpyVideoClip(make_frame, duration=scene.duration)

    elif scene.background_animation == "pulse":
        r1, g1, b1 = bg_rgb
        r2, g2, b2 = [max(0, c - 30) for c in bg_rgb]

        def make_frame(t):
            progress = (t / scene.duration) % 1.0
            factor = 0.5 + 0.5 * np.sin(progress * 4 * np.pi)
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = (
                int(r1 + (r2 - r1) * factor),
                int(g1 + (g2 - g1) * factor),
                int(b1 + (b2 - b1) * factor),
            )
            return frame

        bg_clip = MpyVideoClip(make_frame, duration=scene.duration)

    else:
        def make_frame(t):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = bg_rgb
            return frame

        bg_clip = MpyVideoClip(make_frame, duration=scene.duration)

    overlay_clips = []
    if scene.image_overlays:
        for ov in scene.image_overlays:
            ov_path = ov.get("path", "")
            if not os.path.exists(ov_path):
                continue
            try:
                ov_clip = MpyImageClip(ov_path).with_duration(scene.duration)
                ov_scale = ov.get("scale", 1.0)
                if ov_scale != 1.0:
                    iw2, ih2 = ov_clip.size
                    ov_clip = ov_clip.resized(
                        (int(iw2 * ov_scale), int(ih2 * ov_scale))
                    )
                ov_pos = ov.get("position", "center")
                ov_clip = ov_clip.with_position(ov_pos)
                overlay_clips.append(ov_clip)
            except Exception:
                pass

    txt_clip = None
    if scene.text:
        try:
            txt_clip = MpyTextClip(
                text=scene.text,
                color=scene.text_color,
                font_size=scene.font_size,
                font="Arial",
                size=(int(w * 0.85), None),
                method="caption",
            )
            txt_clip = txt_clip.with_position("center").with_duration(scene.duration)

            if scene.animation == "fade_in":
                txt_clip = txt_clip.with_effects([FadeIn(0.5)])
            elif scene.animation == "slide_in":
                start_y = int(h * 0.5)
                txt_clip = txt_clip.with_position(
                    lambda t: (
                        "center",
                        start_y * (1 - min(t / 0.5, 1)) if t < 0.5 else "center",
                    )
                )
            elif scene.animation == "bounce_in":
                def bounce_pos(t):
                    if t > 1.0:
                        return "center"
                    x = t / 1.0
                    y = -4 * x * (x - 1)
                    return ("center", int(h * 0.3 * (1 - y)))

                txt_clip = txt_clip.with_position(bounce_pos)
        except Exception:
            txt_clip = None

    legacy_img_clip = None
    if scene.image_path and os.path.exists(scene.image_path) and not scene.image_overlays:
        try:
            legacy_img_clip = MpyImageClip(scene.image_path).with_duration(scene.duration)
            iw2, ih2 = legacy_img_clip.size
            scale = min(w * 0.6 / iw2, h * 0.6 / ih2)
            legacy_img_clip = legacy_img_clip.resized(
                (int(iw2 * scale), int(ih2 * scale))
            )
            legacy_img_clip = legacy_img_clip.with_position("center")
        except Exception:
            legacy_img_clip = None

    layers = [bg_clip]

    if legacy_img_clip:
        layers.append(legacy_img_clip)
    if overlay_clips:
        layers.extend(overlay_clips)
    if txt_clip:
        layers.append(txt_clip)

    if len(layers) == 1:
        return bg_clip
    return CompositeVideoClip(layers, size=(w, h))


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i: i + 2], 16) for i in (0, 2, 4))


def hex_to_scene(color: str) -> tuple:
    """Alias for hex_to_rgb."""
    return hex_to_rgb(color)


# ---------------------------------------------------------------------------
# FFmpeg-native crossfade concatenation (fast path)
# ---------------------------------------------------------------------------


def _render_scenes_to_temp(
    script: VideoScript, preset: PlatformPreset, temp_dir: str
) -> list[str]:
    """Render each scene to an individual temp video file."""
    import logging

    logger = logging.getLogger("opencode-video")
    scene_paths = []

    all_scenes = []
    if script.intro_scene:
        all_scenes.append(script.intro_scene)
    all_scenes.extend(script.scenes)
    if script.outro_scene:
        all_scenes.append(script.outro_scene)

    for idx, scene in enumerate(all_scenes):
        clip = _create_scene_clip(scene, preset)
        out_path = os.path.join(temp_dir, f"scene_{idx:04d}.mp4")
        logger.debug(f"Rendering scene {idx + 1}/{len(all_scenes)} -> {out_path}")

        clip.write_videofile(
            out_path,
            fps=script.fps,
            codec=preset.codec,
            audio=False,
            preset="ultrafast",
            bitrate=preset.recommended_bitrate,
            logger=None,
        )
        scene_paths.append(out_path)
        clip.close()

    return scene_paths


def _ffmpeg_concat_with_crossfade(
    scene_paths: list[str],
    output_path: str,
    transition_duration: float,
    audio_path: Optional[str] = None,
    audio_volume: float = 1.0,
    final_duration: Optional[float] = None,
    scene_durations: Optional[list[float]] = None,
) -> str:
    """Concatenate pre-rendered scene files using FFmpeg xfade filter."""
    import subprocess
    import logging

    logger = logging.getLogger("opencode-video")
    n = len(scene_paths)

    if n == 1:
        cmd = ["ffmpeg", "-y", "-i", scene_paths[0]]
        if audio_path:
            cmd += ["-i", audio_path]
            cmd += ["-c:v", "copy", "-c:a", "aac", "-shortest", output_path]
        else:
            cmd += ["-c", "copy", output_path]
        subprocess.run(cmd, capture_output=True)
        return output_path

    td = transition_duration
    filter_parts = []

    current_label = "[0:v]"
    running_offset = (scene_durations[0] if scene_durations else 2.0) - td
    for i in range(1, n):
        next_label = f"[xf_v{i}]"
        filter_parts.append(
            f"{current_label}[{i}:v]"
            f"xfade=duration={td}:offset={running_offset}{next_label}"
        )
        current_label = next_label
        if scene_durations and i < n:
            running_offset += scene_durations[i] - td

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    for sp in scene_paths:
        cmd += ["-i", sp]

    cmd += ["-map", current_label]

    if audio_path:
        cmd += ["-i", audio_path]
        if final_duration:
            cmd += [
                "-map", f"{n}:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-af", f"volume={audio_volume},atrim=duration={final_duration},adelay=1s|1s",
                "-shortest",
            ]
        else:
            cmd += [
                "-map", f"{n}:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-af", f"volume={audio_volume}",
            ]
    else:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18"]

    cmd += ["-filter_complex", filter_complex, output_path]

    logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg xfade failed:\n{result.stderr[:1000]}"
        )
    return output_path


def render_with_ffmpeg_crossfade(script: VideoScript) -> str:
    """Render a VideoScript using FFmpeg-native xfade for maximum speed."""
    import tempfile
    import logging

    logger = logging.getLogger("opencode-video")
    preset = get_preset(script.platform)

    with tempfile.TemporaryDirectory(prefix="opencode_xfade_") as tmpdir:
        logger.info("Rendering individual scenes...")
        scene_paths = _render_scenes_to_temp(script, preset, tmpdir)

        if not scene_paths:
            raise ValueError("No scenes to render.")

        total_dur = sum(
            _get_video_duration(p) for p in scene_paths
        )
        if script.transition_duration > 0 and len(scene_paths) > 1:
            total_dur -= script.transition_duration * (len(scene_paths) - 1)

        logger.info(f"Concatenating {len(scene_paths)} scenes with crossfade...")
        scene_durations = [s.duration for s in script.scenes]
        _ffmpeg_concat_with_crossfade(
            scene_paths,
            script.output_path,
            transition_duration=script.transition_duration,
            audio_path=script.background_music if (
                script.background_music and os.path.exists(script.background_music)
            ) else None,
            audio_volume=script.music_volume,
            final_duration=total_dur,
            scene_durations=scene_durations,
        )

    logger.info(f"Video rendered with FFmpeg crossfade: {script.output_path}")
    return script.output_path


def _get_video_duration(path: str) -> float:
    """Get duration of a video file using ffprobe."""
    import subprocess
    import json

    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", path],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


def script_to_video(script: VideoScript) -> str:
    """
    Convert a VideoScript into a video file.

    Supports image backgrounds (highest bitrate), animated gradients,
    crossfade transitions between scenes, and proper platform-specific bitrate.

    Returns the path to the rendered video.
    """
    preset = get_preset(script.platform)

    scene_clips = []
    if script.intro_scene:
        scene_clips.append(_create_scene_clip(script.intro_scene, preset))

    for scene in script.scenes:
        scene_clips.append(_create_scene_clip(scene, preset))

    if script.outro_scene:
        scene_clips.append(_create_scene_clip(script.outro_scene, preset))

    if not scene_clips:
        raise ValueError("No scenes defined in the video script.")

    if script.transition_duration > 0 and len(scene_clips) > 1:
        td = script.transition_duration
        clips_with_xfade = []
        for i, clip in enumerate(scene_clips):
            effective_td = min(td, clip.duration / 2)
            if i > 0:
                effective_td = min(effective_td, scene_clips[i - 1].duration / 2)

            if i > 0:
                c = clip.with_effects([CrossFadeIn(effective_td)])
            else:
                c = clip
            clips_with_xfade.append(c)

        final = concatenate_videoclips(clips_with_xfade, method="compose")
    else:
        final = concatenate_videoclips(scene_clips, method="chain")

    if script.background_music and os.path.exists(script.background_music):
        try:
            audio = MpyAudioClip(script.background_music)
            audio = audio.with_volume_scaled(script.music_volume)

            if audio.duration < final.duration:
                from moviepy.audio.fx import AudioLoop
                audio = AudioLoop(duration=final.duration).apply(audio)
            else:
                audio = audio.with_duration(final.duration)
            final = final.with_audio(audio)
        except Exception as e:
            import logging
            logging.getLogger("opencode-video").warning(f"Failed to add audio: {e}")

    import logging
    logger = logging.getLogger("opencode-video")

    bitrate_str = preset.recommended_bitrate
    try:
        if bitrate_str.endswith("M"):
            int(float(bitrate_str[:-1]) * 1000000)
        elif bitrate_str.endswith("k"):
            int(float(bitrate_str[:-1]) * 1000)
        else:
            int(bitrate_str)
    except (ValueError, AttributeError):
        bitrate_str = "4M"

    write_kwargs = dict(
        fps=script.fps,
        codec=preset.codec,
        audio_codec=preset.audio_codec,
        preset=script.ffmpeg_preset,
        bitrate=bitrate_str if script.ffmpeg_params is None else None,
        logger="bar" if logger.isEnabledFor(logging.DEBUG) else None,
    )
    if script.threads > 0:
        write_kwargs["threads"] = script.threads
    if script.ffmpeg_params:
        write_kwargs["ffmpeg_params"] = script.ffmpeg_params

    final.write_videofile(
        script.output_path,
        **write_kwargs,
    )

    return script.output_path

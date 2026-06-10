"""
Comprehensive tests for the opencode_video module.

Tests cover:
- Platform presets (lookup, properties, validation)
- Scene/VideoScript dataclasses
- Utility functions (hex_to_rgb)
- Scene clip creation with various background animations
- script_to_video rendering pipeline
- core.create_video() and compose_video()
- Effects (fade_in, fade_out, cross_fade, zoom_in, slide_in)

Run: python3 -m pytest test_video_module.py -v
  or: python3 -m unittest test_video_module.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from opencode_video.presets import PlatformPreset, get_preset, list_presets
from opencode_video.scripts import Scene, VideoScript, hex_to_rgb, script_to_video
from opencode_video.effects import fade_in, fade_out, cross_fade, zoom_in, slide_in


class TestPlatformPresets(unittest.TestCase):
    """Test platform preset definitions and lookup."""

    def test_get_preset_youtube(self):
        preset = get_preset("youtube")
        self.assertEqual(preset.width, 1920)
        self.assertEqual(preset.height, 1080)
        self.assertEqual(preset.aspect_ratio, "16:9")
        self.assertEqual(preset.fps, 30)
        self.assertEqual(preset.recommended_bitrate, "10M")
        self.assertFalse(preset.is_vertical)

    def test_get_preset_tiktok(self):
        preset = get_preset("tiktok")
        self.assertEqual(preset.width, 1080)
        self.assertEqual(preset.height, 1920)
        self.assertEqual(preset.aspect_ratio, "9:16")
        self.assertTrue(preset.is_vertical)
        self.assertTrue(preset.vertical)

    def test_get_preset_youtube_shorts(self):
        preset = get_preset("youtube_shorts")
        self.assertEqual(preset.width, 1080)
        self.assertEqual(preset.height, 1920)
        self.assertTrue(preset.is_vertical)

    def test_get_preset_instagram_reel(self):
        preset = get_preset("instagram_reel")
        self.assertEqual(preset.width, 1080)
        self.assertEqual(preset.height, 1920)
        self.assertTrue(preset.is_vertical)

    def test_get_preset_instagram_post(self):
        preset = get_preset("instagram_post")
        self.assertEqual(preset.width, 1080)
        self.assertEqual(preset.height, 1080)
        self.assertTrue(preset.square)
        self.assertFalse(preset.is_vertical)

    def test_get_preset_case_insensitive(self):
        preset1 = get_preset("YouTube Shorts")
        preset2 = get_preset("youtube_shorts")
        preset3 = get_preset("YOUTUBE_SHORTS")
        self.assertEqual(preset1.name, preset2.name)
        self.assertEqual(preset2.name, preset3.name)

    def test_get_preset_twitter(self):
        preset = get_preset("twitter")
        self.assertEqual(preset.width, 1280)
        self.assertEqual(preset.height, 720)

    def test_get_preset_linkedin(self):
        preset = get_preset("linkedin")
        self.assertEqual(preset.width, 1920)
        self.assertEqual(preset.height, 1080)

    def test_get_preset_facebook(self):
        preset = get_preset("facebook")
        self.assertEqual(preset.width, 1920)
        self.assertEqual(preset.height, 1080)

    def test_invalid_preset_raises_keyerror(self):
        with self.assertRaises(KeyError):
            get_preset("nonexistent_platform")

    def test_list_presets(self):
        presets = list_presets()
        self.assertGreaterEqual(len(presets), 8)
        names = [p.name for p in presets]
        self.assertIn("TikTok", names)
        self.assertIn("YouTube (Landscape)", names)
        self.assertIn("YouTube Shorts", names)

    def test_preset_resolution_property(self):
        preset = get_preset("tiktok")
        self.assertEqual(preset.resolution, (1080, 1920))

    def test_preset_str_representation(self):
        preset = get_preset("youtube")
        s = str(preset)
        self.assertIn("1920", s)
        self.assertIn("1080", s)
        self.assertIn("16:9", s)

    def test_instagram_landscape(self):
        preset = get_preset("instagram_landscape")
        self.assertEqual(preset.width, 1920)
        self.assertEqual(preset.height, 1080)
        self.assertFalse(preset.vertical)

    def test_all_presets_have_bitrate(self):
        for preset in list_presets():
            self.assertIsNotNone(preset.recommended_bitrate)
            self.assertGreater(len(preset.recommended_bitrate), 0)

    def test_all_presets_have_codec(self):
        for preset in list_presets():
            self.assertEqual(preset.codec, "libx264")
            self.assertEqual(preset.audio_codec, "aac")

    def test_max_duration_shorts(self):
        preset = get_preset("youtube_shorts")
        self.assertEqual(preset.max_duration_seconds, 60)

    def test_max_duration_tiktok(self):
        preset = get_preset("tiktok")
        self.assertEqual(preset.max_duration_seconds, 180)


class TestSceneAndScript(unittest.TestCase):
    """Test Scene and VideoScript dataclasses."""

    def test_scene_defaults(self):
        scene = Scene()
        self.assertEqual(scene.text, "")
        self.assertEqual(scene.background_color, "#1a1a2e")
        self.assertEqual(scene.text_color, "#ffffff")
        self.assertEqual(scene.duration, 5.0)
        self.assertEqual(scene.font_size, 48)
        self.assertEqual(scene.animation, "fade_in")
        self.assertEqual(scene.background_animation, "none")
        self.assertIsNone(scene.image_path)
        self.assertIsNone(scene.sound_effect)

    def test_scene_custom_values(self):
        scene = Scene(
            text="Hello World",
            background_color="#ff0000",
            text_color="#00ff00",
            duration=3.0,
            font_size=72,
            animation="bounce_in",
            background_animation="gradient_shift",
        )
        self.assertEqual(scene.text, "Hello World")
        self.assertEqual(scene.background_color, "#ff0000")
        self.assertEqual(scene.text_color, "#00ff00")
        self.assertEqual(scene.duration, 3.0)
        self.assertEqual(scene.font_size, 72)
        self.assertEqual(scene.animation, "bounce_in")
        self.assertEqual(scene.background_animation, "gradient_shift")

    def test_video_script_defaults(self):
        script = VideoScript()
        self.assertEqual(script.title, "Untitled Video")
        self.assertEqual(script.scenes, [])
        self.assertIsNone(script.background_music)
        self.assertEqual(script.music_volume, 0.3)
        self.assertIsNone(script.intro_scene)
        self.assertIsNone(script.outro_scene)
        self.assertEqual(script.platform, "youtube")
        self.assertEqual(script.fps, 30)
        self.assertEqual(script.output_path, "output.mp4")
        self.assertEqual(script.transition_duration, 0.0)

    def test_video_script_with_scenes(self):
        scenes = [
            Scene(text="Scene 1", duration=3.0),
            Scene(text="Scene 2", duration=4.0),
            Scene(text="Scene 3", duration=5.0),
        ]
        script = VideoScript(
            title="Test Video",
            scenes=scenes,
            platform="tiktok",
            fps=30,
            output_path="/tmp/test_video.mp4",
            transition_duration=0.5,
        )
        self.assertEqual(script.title, "Test Video")
        self.assertEqual(len(script.scenes), 3)
        self.assertEqual(script.platform, "tiktok")
        self.assertEqual(script.transition_duration, 0.5)
        self.assertEqual(script.scenes[1].text, "Scene 2")
        self.assertEqual(script.scenes[2].duration, 5.0)

    def test_video_script_with_intro_outro(self):
        intro = Scene(text="Intro", duration=2.0)
        outro = Scene(text="Outro", duration=2.0)
        scenes = [Scene(text="Main", duration=5.0)]
        script = VideoScript(
            title="Test",
            scenes=scenes,
            intro_scene=intro,
            outro_scene=outro,
        )
        self.assertEqual(script.intro_scene.text, "Intro")
        self.assertEqual(script.outro_scene.text, "Outro")


class TestUtils(unittest.TestCase):
    """Test utility functions."""

    def test_hex_to_rgb_red(self):
        self.assertEqual(hex_to_rgb("#ff0000"), (255, 0, 0))

    def test_hex_to_rgb_green(self):
        self.assertEqual(hex_to_rgb("#00ff00"), (0, 255, 0))

    def test_hex_to_rgb_blue(self):
        self.assertEqual(hex_to_rgb("#0000ff"), (0, 0, 255))

    def test_hex_to_rgb_white(self):
        self.assertEqual(hex_to_rgb("#ffffff"), (255, 255, 255))

    def test_hex_to_rgb_black(self):
        self.assertEqual(hex_to_rgb("#000000"), (0, 0, 0))

    def test_hex_to_rgb_without_hash(self):
        self.assertEqual(hex_to_rgb("ff0000"), (255, 0, 0))
        self.assertEqual(hex_to_rgb("00ff00"), (0, 255, 0))

    def test_hex_to_rgb_custom_color(self):
        self.assertEqual(hex_to_rgb("#1a1a2e"), (26, 26, 46))
        self.assertEqual(hex_to_rgb("#e94560"), (233, 69, 96))
        self.assertEqual(hex_to_rgb("#16213e"), (22, 33, 62))

    def test_hex_to_rgb_short_hex(self):
        with self.assertRaises(ValueError):
            hex_to_rgb("#fff")


class TestSceneClipCreation(unittest.TestCase):
    """Test _create_scene_clip with various background animations.
    
    These tests require MoviePy and FFmpeg to be installed.
    """

    def setUp(self):
        try:
            from moviepy import VideoClip as MpyVideoClip
            self.moviepy_available = True
        except ImportError:
            self.moviepy_available = False

    def _check_deps(self):
        if not self.moviepy_available:
            self.skipTest("MoviePy not installed")

    def test_static_background_clip(self):
        self._check_deps()
        from opencode_video.scripts import _create_scene_clip
        preset = get_preset("youtube")
        scene = Scene(text="Test", duration=2.0, background_animation="none")
        clip = _create_scene_clip(scene, preset)
        self.assertIsNotNone(clip)
        self.assertAlmostEqual(clip.duration, 2.0, places=1)

    def test_gradient_shift_background(self):
        self._check_deps()
        from opencode_video.scripts import _create_scene_clip
        preset = get_preset("youtube")
        scene = Scene(
            text="Gradient", duration=2.0,
            background_animation="gradient_shift",
        )
        clip = _create_scene_clip(scene, preset)
        self.assertIsNotNone(clip)
        self.assertAlmostEqual(clip.duration, 2.0, places=1)

    def test_pulse_background(self):
        self._check_deps()
        from opencode_video.scripts import _create_scene_clip
        preset = get_preset("youtube")
        scene = Scene(
            text="Pulse", duration=2.0,
            background_animation="pulse",
        )
        clip = _create_scene_clip(scene, preset)
        self.assertIsNotNone(clip)
        self.assertAlmostEqual(clip.duration, 2.0, places=1)

    def test_scene_without_text(self):
        self._check_deps()
        from opencode_video.scripts import _create_scene_clip
        preset = get_preset("youtube")
        scene = Scene(text="", duration=2.0)
        clip = _create_scene_clip(scene, preset)
        self.assertIsNotNone(clip)
        self.assertAlmostEqual(clip.duration, 2.0, places=1)


class TestScriptToVideo(unittest.TestCase):
    """Integration tests for script_to_video.
    
    Renders actual short videos and verifies the output.
    Requires FFmpeg.
    """

    def setUp(self):
        self.ffmpeg_available = os.system("ffmpeg -version > /dev/null 2>&1") == 0
        self.tmpdir = tempfile.mkdtemp(prefix="opencode_video_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _check_deps(self):
        if not self.ffmpeg_available:
            self.skipTest("FFmpeg not installed")

    def test_render_basic_video(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "basic_test.mp4")
        script = VideoScript(
            title="Basic Test",
            scenes=[Scene(text="Hello World", duration=2.0)],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 100)

    def test_render_multi_scene_video(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "multi_scene.mp4")
        script = VideoScript(
            title="Multi Scene",
            scenes=[
                Scene(text="Scene 1", duration=1.0, background_color="#ff0000"),
                Scene(text="Scene 2", duration=1.0, background_color="#00ff00"),
                Scene(text="Scene 3", duration=1.0, background_color="#0000ff"),
            ],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 200)

    def test_render_with_intro_outro(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "intro_outro.mp4")
        script = VideoScript(
            title="Intro Outro",
            intro_scene=Scene(text="Intro", duration=1.0, background_color="#000000"),
            scenes=[Scene(text="Main Content", duration=2.0, background_color="#1a1a2e")],
            outro_scene=Scene(text="Outro", duration=1.0, background_color="#000000"),
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))

    def test_render_with_crossfade(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "crossfade.mp4")
        script = VideoScript(
            title="Crossfade Test",
            scenes=[
                Scene(text="Scene A", duration=2.0, background_color="#ff0000"),
                Scene(text="Scene B", duration=2.0, background_color="#00ff00"),
            ],
            platform="youtube",
            fps=5,
            output_path=output,
            transition_duration=0.5,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 200)

    def test_render_with_animated_background(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "animated_bg.mp4")
        script = VideoScript(
            title="Animated BG",
            scenes=[Scene(
                text="Animated!",
                duration=2.0,
                background_animation="gradient_shift",
            )],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))

    def test_render_with_pulse_background(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "pulse_bg.mp4")
        script = VideoScript(
            title="Pulse BG",
            scenes=[Scene(
                text="Pulsing!",
                duration=2.0,
                background_animation="pulse",
            )],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))

    def test_render_with_bounce_in_animation(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "bounce_in.mp4")
        script = VideoScript(
            title="Bounce In",
            scenes=[Scene(
                text="Bounce!",
                duration=2.0,
                animation="bounce_in",
            )],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))

    def test_render_tiktok_vertical(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "tiktok_test.mp4")
        script = VideoScript(
            title="TikTok Test",
            scenes=[Scene(
                text="TikTok Vertical Test",
                duration=2.0,
                font_size=36,
            )],
            platform="tiktok",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 100)

    def test_empty_scenes_raises_error(self):
        self._check_deps()
        script = VideoScript(
            title="Empty",
            scenes=[],
            output_path=os.path.join(self.tmpdir, "empty.mp4"),
        )
        with self.assertRaises(ValueError):
            script_to_video(script)

    def test_audio_loop_short_music(self):
        self._check_deps()
        import numpy as np
        import wave

        wav_path = os.path.join(self.tmpdir, "test_music.wav")
        sample_rate = 22050
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        samples = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())

        output = os.path.join(self.tmpdir, "audio_loop.mp4")
        script = VideoScript(
            title="Audio Loop",
            scenes=[Scene(text="Audio Test", duration=3.0)],
            background_music=wav_path,
            music_volume=0.5,
            platform="youtube",
            fps=5,
            output_path=output,
        )
        result = script_to_video(script)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 500)


class TestCreateVideo(unittest.TestCase):
    """Test the core.create_video() function."""

    def setUp(self):
        self.ffmpeg_available = os.system("ffmpeg -version > /dev/null 2>&1") == 0
        self.tmpdir = tempfile.mkdtemp(prefix="opencode_create_video_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _check_deps(self):
        if not self.ffmpeg_available:
            self.skipTest("FFmpeg not installed")

    def test_create_basic_video(self):
        self._check_deps()
        from opencode_video.core import create_video
        output = os.path.join(self.tmpdir, "basic_create.mp4")
        result = create_video(
            output=output,
            platform="youtube",
            fps=5,
            background_color="#1a1a2e",
        )
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 100)

    def test_create_with_text_overlay(self):
        self._check_deps()
        from opencode_video.core import create_video
        output = os.path.join(self.tmpdir, "with_text.mp4")
        result = create_video(
            output=output,
            texts=[{"text": "Hello World", "color": "white", "font_size": 48}],
            platform="youtube",
            fps=5,
            duration_per_clip=2.0,
        )
        self.assertTrue(os.path.exists(result))

    def test_create_with_audio(self):
        self._check_deps()
        from opencode_video.core import create_video
        import numpy as np
        import wave

        wav_path = os.path.join(self.tmpdir, "test_audio.wav")
        sample_rate = 22050
        t = np.linspace(0, 1.0, sample_rate, endpoint=False)
        samples = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())

        output = os.path.join(self.tmpdir, "with_audio.mp4")
        result = create_video(
            output=output,
            audio=wav_path,
            audio_volume=0.5,
            platform="youtube",
            fps=5,
            duration_per_clip=2.0,
        )
        self.assertTrue(os.path.exists(result))

    def test_create_with_tiktok_preset(self):
        self._check_deps()
        from opencode_video.core import create_video
        output = os.path.join(self.tmpdir, "tiktok_create.mp4")
        result = create_video(
            output=output,
            platform="tiktok",
            fps=5,
            background_color="#ff0000",
            duration_per_clip=2.0,
        )
        self.assertTrue(os.path.exists(result))

    def test_create_with_image(self):
        self._check_deps()
        from opencode_video.core import create_video
        img_path = os.path.join(self.tmpdir, "test_img.png")
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)

        output = os.path.join(self.tmpdir, "with_image.mp4")
        result = create_video(
            output=output,
            images=[img_path],
            platform="youtube",
            fps=5,
            duration_per_clip=2.0,
        )
        self.assertTrue(os.path.exists(result))


class TestEffects(unittest.TestCase):
    """Test transition effects."""

    def setUp(self):
        self.moviepy_available = True
        try:
            from moviepy import ColorClip
        except ImportError:
            self.moviepy_available = False

    def _check_deps(self):
        if not self.moviepy_available:
            self.skipTest("MoviePy not installed")

    def test_fade_in(self):
        self._check_deps()
        from moviepy import ColorClip
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=2.0)
        result = fade_in(clip, duration=0.5)
        self.assertIsNotNone(result)

    def test_fade_out(self):
        self._check_deps()
        from moviepy import ColorClip
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=2.0)
        result = fade_out(clip, duration=0.5)
        self.assertIsNotNone(result)

    def test_cross_fade(self):
        self._check_deps()
        from moviepy import ColorClip
        clip1 = ColorClip(size=(100, 100), color=(255, 0, 0), duration=2.0)
        clip2 = ColorClip(size=(100, 100), color=(0, 255, 0), duration=2.0)
        result = cross_fade(clip1, clip2, duration=0.5)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.duration, 3.5, places=1)

    def test_slide_in_left(self):
        self._check_deps()
        from moviepy import ColorClip
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=2.0)
        result = slide_in(clip, direction="left", duration=0.5)
        self.assertIsNotNone(result)

    def test_slide_in_right(self):
        self._check_deps()
        from moviepy import ColorClip
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=2.0)
        result = slide_in(clip, direction="right", duration=0.5)
        self.assertIsNotNone(result)

    def test_zoom_in(self):
        self._check_deps()
        from moviepy import ColorClip
        clip = ColorClip(size=(100, 100), color=(255, 0, 0), duration=2.0)
        result = zoom_in(clip, start_zoom=1.0, end_zoom=1.15)
        self.assertIsNotNone(result)


class TestModuleImports(unittest.TestCase):
    """Test that the module's public API is accessible."""

    def test_import_core(self):
        from opencode_video import create_video, compose_video
        from opencode_video import VideoClip, TextClip, ImageClip, AudioClip
        self.assertTrue(callable(create_video))

    def test_import_presets(self):
        from opencode_video import PlatformPreset, get_preset
        self.assertTrue(callable(get_preset))

    def test_import_effects(self):
        from opencode_video import fade_in, fade_out, cross_fade, zoom_in, slide_in
        self.assertTrue(callable(fade_in))
        self.assertTrue(callable(fade_out))

    def test_import_scripts(self):
        from opencode_video import VideoScript, script_to_video
        self.assertTrue(issubclass(VideoScript, object))
        self.assertTrue(callable(script_to_video))

    def test_version(self):
        import opencode_video
        self.assertTrue(hasattr(opencode_video, "__version__"))


class TestVideoQuality(unittest.TestCase):
    """Test that rendered videos meet quality standards."""

    def setUp(self):
        self.ffmpeg_available = os.system("ffprobe -version > /dev/null 2>&1") == 0
        self.tmpdir = tempfile.mkdtemp(prefix="opencode_quality_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _check_deps(self):
        if not self.ffmpeg_available:
            self.skipTest("FFprobe not installed")

    def _get_video_info(self, path):
        import subprocess
        import json
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_video_resolution_youtube(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "quality_youtube.mp4")
        script = VideoScript(
            title="Quality Test",
            scenes=[Scene(text="Resolution Test", duration=1.0)],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        script_to_video(script)

        info = self._get_video_info(output)
        streams = info.get("streams", [])
        video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
        self.assertIsNotNone(video_stream)
        self.assertEqual(video_stream["width"], 1920)
        self.assertEqual(video_stream["height"], 1080)

    def test_video_resolution_tiktok(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "quality_tiktok.mp4")
        script = VideoScript(
            title="TikTok Quality",
            scenes=[Scene(text="TikTok Test", duration=1.0)],
            platform="tiktok",
            fps=5,
            output_path=output,
        )
        script_to_video(script)

        info = self._get_video_info(output)
        streams = info.get("streams", [])
        video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
        self.assertIsNotNone(video_stream)
        self.assertEqual(video_stream["width"], 1080)
        self.assertEqual(video_stream["height"], 1920)

    def test_video_duration(self):
        self._check_deps()
        output = os.path.join(self.tmpdir, "quality_duration.mp4")
        script = VideoScript(
            title="Duration Test",
            scenes=[
                Scene(text="A", duration=2.0),
                Scene(text="B", duration=2.0),
            ],
            platform="youtube",
            fps=5,
            output_path=output,
            transition_duration=0.5,
        )
        script_to_video(script)

        info = self._get_video_info(output)
        format_info = info.get("format", {})
        duration = float(format_info.get("duration", 0))
        self.assertAlmostEqual(duration, 3.5, delta=1.0)

    def test_video_has_audio_stream(self):
        self._check_deps()
        import numpy as np
        import wave

        wav_path = os.path.join(self.tmpdir, "quality_music.wav")
        sample_rate = 22050
        t = np.linspace(0, 0.5, int(sample_rate * 0.5), endpoint=False)
        samples = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())

        output = os.path.join(self.tmpdir, "quality_audio.mp4")
        script = VideoScript(
            title="Audio Test",
            scenes=[Scene(text="Audio Check", duration=2.0)],
            background_music=wav_path,
            platform="youtube",
            fps=5,
            output_path=output,
        )
        script_to_video(script)

        info = self._get_video_info(output)
        streams = info.get("streams", [])
        audio_streams = [s for s in streams if s["codec_type"] == "audio"]
        self.assertGreaterEqual(len(audio_streams), 1)


class TestComposeVideo(unittest.TestCase):
    """Test the compose_video function."""

    def setUp(self):
        self.ffmpeg_available = os.system("ffmpeg -version > /dev/null 2>&1") == 0
        self.tmpdir = tempfile.mkdtemp(prefix="opencode_compose_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _check_deps(self):
        if not self.ffmpeg_available:
            self.skipTest("FFmpeg not installed")

    def _create_base_video(self):
        output = os.path.join(self.tmpdir, "base_video.mp4")
        script = VideoScript(
            title="Base",
            scenes=[Scene(text="Base Video", duration=2.0)],
            platform="youtube",
            fps=5,
            output_path=output,
        )
        script_to_video(script)
        return output

    def test_compose_text_overlay(self):
        self._check_deps()
        from opencode_video.core import compose_video
        base = self._create_base_video()
        output = os.path.join(self.tmpdir, "composed_text.mp4")
        result = compose_video(
            main_clip=base,
            overlays=[{
                "type": "text",
                "source": "Overlay Text",
                "position": "center",
                "color": "white",
                "font_size": 48,
            }],
            output=output,
            platform="youtube",
            fps=5,
        )
        self.assertTrue(os.path.exists(result))

    def test_compose_without_overlays(self):
        self._check_deps()
        from opencode_video.core import compose_video
        base = self._create_base_video()
        output = os.path.join(self.tmpdir, "composed_plain.mp4")
        result = compose_video(
            main_clip=base,
            output=output,
            platform="youtube",
        )
        self.assertTrue(os.path.exists(result))


def run_smoke_test():
    """Quick smoke test: render a tiny video and verify output exists & has duration."""
    print("=" * 60)
    print("Smoke Test: Quick video render")
    print("=" * 60)

    script = VideoScript(
        title="Smoke Test",
        scenes=[
            Scene(text="Smoke Test OK", duration=2, background_animation="gradient_shift"),
        ],
        platform="tiktok",
        fps=10,
        output_path="/tmp/opencode_smoke_test.mp4",
    )

    from opencode_video.scripts import script_to_video
    result = script_to_video(script)

    assert os.path.exists(result), f"Output file not found: {result}"
    size_kb = os.path.getsize(result) / 1024
    print(f"  Output: {result} ({size_kb:.0f} KB)")

    import json, subprocess
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", result],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        dur = float(json.loads(r.stdout)["format"]["duration"])
        print(f"  Duration: {dur:.1f}s")
        assert dur >= 1.5, f"Video too short: {dur}s"
    else:
        print("  Warning: ffprobe unavailable, skipping duration check")

    print("Smoke test PASSED")
    return 0


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        sys.exit(run_smoke_test())
    unittest.main(verbosity=2)

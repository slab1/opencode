"""
End-to-end video creation workflows combining browser + video modules.

Provides high-level functions to:
- Capture web content and turn it into TikTok/Shorts/Reel videos
- Create social media videos from URLs, search results, or scripts
"""

import os
import logging
from typing import Optional

from .scripts import VideoScript, Scene, script_to_video
from .presets import get_preset

logger = logging.getLogger("opencode-video")


def capture_web_screenshot(
    url: str,
    output_path: str = "/tmp/video_screenshot.png",
    width: int = 1080,
    height: int = 1920,
    wait_ms: int = 3000,
) -> str:
    """Capture a web page screenshot for use as video background.

    Falls back to generating a gradient placeholder if browser is unavailable.
    """
    try:
        from opencode_web import Browser

        with Browser(headless=True) as b:
            b.navigate(url)
            b.wait(wait_ms)
            b.screenshot(output_path)
        logger.info(f"Captured screenshot: {url} -> {output_path}")
        return output_path
    except (ImportError, Exception) as exc:
        logger.warning(f"Browser unavailable ({exc}), generating placeholder")
        return _generate_placeholder(output_path, width, height, url)


def _generate_placeholder(
    path: str, w: int, h: int, text: str = ""
) -> str:
    """Generate a gradient placeholder image when browser is unavailable."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        r = int(20 + (y / h) * 60)
        g = int(20 + (y / h) * 40)
        b = int(60 + (y / h) * 80)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    if text:
        draw.text((w // 4, h // 2), text[:50], fill=(255, 255, 255))
    img.save(path)
    return path


def create_tiktok_from_urls(
    urls: list[str],
    texts: list[str],
    output_path: str = "/tmp/tiktok_from_web.mp4",
    platform: str = "tiktok",
    scene_duration: float = 4.0,
    background_music: Optional[str] = None,
    music_volume: float = 0.3,
    fps: int = 30,
    threads: int = 0,
    transition_duration: float = 0.0,
    screenshot_wait_ms: int = 3000,
) -> str:
    """Create a TikTok/Shorts video from a list of URLs.

    Each URL is screenshot-captured and used as a scene background
    with the corresponding text overlay.
    """
    preset = get_preset(platform)
    w, h = preset.width, preset.height

    screenshot_dir = "/tmp/video_web_screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)

    scenes = []
    for i, url in enumerate(urls):
        shot_path = os.path.join(screenshot_dir, f"scene_{i:03d}.png")
        capture_web_screenshot(
            url, output_path=shot_path,
            width=w, height=h,
            wait_ms=screenshot_wait_ms,
        )

        text = texts[i] if i < len(texts) else f"Scene {i + 1}"

        scenes.append(Scene(
            text=text,
            background_image=shot_path,
            background_color="#1a1a2e",
            font_size=48 if platform in ("tiktok", "youtube_shorts", "instagram_reel") else 56,
            animation="fade_in",
            duration=scene_duration,
        ))

    if not scenes:
        raise ValueError("At least one URL is required.")

    script = VideoScript(
        title="Web to Video",
        scenes=scenes,
        platform=platform,
        fps=fps,
        output_path=output_path,
        transition_duration=transition_duration,
        background_music=background_music,
        music_volume=music_volume,
        threads=threads,
        ffmpeg_preset="ultrafast",
        ffmpeg_params=["-crf", "18"],
    )

    result = script_to_video(script)
    logger.info(f"TikTok from web created: {result}")
    return result


def create_tiktok_from_search(
    query: str,
    num_screenshots: int = 5,
    output_path: str = "/tmp/tiktok_search.mp4",
    platform: str = "tiktok",
    scene_duration: float = 4.0,
    search_engine: str = "google",
    **kwargs,
) -> str:
    """Search the web and create a TikTok video from the results.

    Searches for the given query, captures screenshots of the top results,
    and creates a video with each result as a scene.
    """
    search_urls = {
        "google": f"https://www.google.com/search?q={query.replace(' ', '+')}",
        "bing": f"https://www.bing.com/search?q={query.replace(' ', '+')}",
    }
    search_url = search_urls.get(search_engine, search_urls["google"])

    texts = [
        f"Search: {query}",
        *[f"Result {i + 1}" for i in range(num_screenshots - 1)],
    ]

    urls = [search_url] + [
        f"https://www.google.com/search?q={query}&start={i * 10}"
        for i in range(1, num_screenshots)
    ]

    return create_tiktok_from_urls(
        urls=urls[:num_screenshots],
        texts=texts[:num_screenshots],
        output_path=output_path,
        platform=platform,
        scene_duration=scene_duration,
        **kwargs,
    )

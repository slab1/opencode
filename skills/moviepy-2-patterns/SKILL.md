---
name: moviepy-2-patterns
description: MoviePy 2.x API patterns for the video-creator agent. Use when creating, editing, or composing videos programmatically. MoviePy 2.x has significant breaking changes from 1.x — this skill prevents the most common pitfalls.
license: MIT
compatibility: opencode>=1.16.0
---

# MoviePy 2.x Patterns

The video-creator agent uses **MoviePy 2.1.2** (not 1.x). The 2.x API is significantly different and most online tutorials are for 1.x. This skill captures the patterns that actually work in 2.x.

## Key API changes from 1.x to 2.x

### 1. Effects use `with_effects([...])`, not `with_effect(string)`

```python
# WRONG (1.x style):
clip.with_effect("fadein", duration=1)

# CORRECT (2.x):
from moviepy.video.fx import FadeIn, FadeOut
clip.with_effects([FadeIn(duration=1)])
clip.with_effects([FadeIn(duration=1), FadeOut(duration=1)])
```

### 2. Timing uses `with_start()` / `with_duration()`, not `set_start()` / `set_duration()`

```python
# WRONG (1.x style):
clip.set_start(2.0)
clip.set_duration(5.0)

# CORRECT (2.x):
clip.with_start(2.0)
clip.with_duration(5.0)
```

### 3. `CompositeVideoClip` takes a list directly

```python
# WRONG:
CompositeVideoClip([clip1, clip2], size=(1920, 1080))

# CORRECT (2.x):
from moviepy import CompositeVideoClip
CompositeVideoClip([clip1, clip2], size=(1920, 1080))
# Or set bg color via:
from moviepy.video.VideoClip import ColorClip
bg = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=10)
CompositeVideoClip([bg, clip1, clip2])
```

### 4. Text clips use `TextClip` with `font=` parameter

```python
from moviepy import TextClip
# CORRECT (2.x):
txt = TextClip(
    text="Hello world",
    font_size=70,
    color="white",
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # REQUIRED in 2.x
    duration=3,
)
```

**Common pitfall**: 2.x requires an explicit `font` path. If you get font errors, use DejaVu Sans which is in apk's `font-dejavu` package.

### 5. Concatenation

```python
from moviepy import concatenate_videoclips
final = concatenate_videoclips([clip1, clip2, clip3])
# Add crossfade transitions:
final = concatenate_videoclips([clip1, clip2], method="compose", padding=-0.5)
```

### 6. Audio handling

```python
from moviepy import AudioFileClip
audio = AudioFileClip("music.mp3")
video = video.with_audio(audio)
# Or set audio of a composite:
final = CompositeVideoClip([clip, ...]).with_audio(audio)
```

### 7. Writing output

```python
video.write_videofile(
    "output.mp4",
    fps=24,
    codec="libx264",
    audio_codec="aac",
    threads=4,        # parallel processing
    preset="medium",  # encoding speed vs compression
)
```

## Common patterns

### Text-on-color video (most common)

```python
from moviepy import TextClip, ColorClip, CompositeVideoClip
from moviepy.video.fx import FadeIn, FadeOut

W, H = 1920, 1080
duration = 5

bg = ColorClip(size=(W, H), color=(0, 0, 0), duration=duration)
txt = (
    TextClip(
        text="Your message here",
        font_size=80,
        color="white",
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        duration=duration,
    )
    .with_position("center")
    .with_effects([FadeIn(duration=0.5), FadeOut(duration=0.5)])
)

video = CompositeVideoClip([bg, txt])
video.write_videofile("output.mp4", fps=24)
```

### Slideshow with crossfades

```python
from moviepy import ImageClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut

images = ["img1.jpg", "img2.jpg", "img3.jpg"]
durations = [3, 4, 3]

clips = [
    ImageClip(img).with_duration(dur)
    for img, dur in zip(images, durations)
]

# Add fade effects
clips_with_fades = [
    c.with_effects([FadeIn(duration=0.5), FadeOut(duration=0.5)])
    for c in clips
]

final = concatenate_videoclips(clips_with_fades, method="compose", padding=-0.5)
final.write_videofile("slideshow.mp4", fps=24)
```

### Script-based video (preferred for long content)

Use the `VideoScript` API at `/home/.config/opencode/opencode_video/scripts/`:

```python
from opencode_video.scripts import VideoScript, Scene, script_to_video

script = VideoScript(
    title="My Video",
    scenes=[
        Scene(text="Scene 1 content", duration=3, bg_color=(20, 30, 50)),
        Scene(text="Scene 2 content", duration=3, bg_color=(50, 30, 20)),
    ],
    output_path="output.mp4",
)
script_to_video(script)
```

## Alpine-specific gotchas

- **ffmpeg is required** — `apk add ffmpeg`
- **libx264 may not be available** — try `mpeg4` codec as fallback
- **Memory**: rendering long videos can OOM on Android (use `ulimit -v 800000`)
- **Threads**: limit to 2-4 on Alpine/musl, more may cause instability
- **Fonts**: `apk add font-dejavu` for the standard font

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `AttributeError: 'VideoClip' object has no attribute 'set_start'` | Using 1.x API | Use `.with_start(t)` instead |
| `AttributeError: module 'moviepy' has no attribute 'TextClip'` | Wrong import | `from moviepy import TextClip` |
| `OSError: font file not found` | No font specified | Pass `font=` with absolute path |
| `RuntimeError: no ffmpeg` | ffmpeg not installed | `apk add ffmpeg` |
| `MemoryError` during render | OOM | Lower resolution, fewer threads, or split into clips |

## When to use

- Creating any video programmatically
- The user asks for a video, animation, slideshow, or render
- The video-creator agent is invoked

## When NOT to use

- The user wants a YouTube link (use web-browser instead)
- Image-only manipulation (use media-agent)
- The video module isn't installed (check first)

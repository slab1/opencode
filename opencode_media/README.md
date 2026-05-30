# OpenCode Media Module

Multimodal file processing for AI agents — images, audio, video, documents.

```
opencode_media/
├── __init__.py     # Core processing pipeline
├── README.md       # This file
└── examples/
    └── usage.py    # Usage examples
```

## Quick Start

```bash
# Analyze an image
python3 -m opencode_media screenshot.png --summary

# Transcribe audio
python3 -m opencode_media meeting.mp3 --summary

# Analyze video
python3 -m opencode_media demo.mp4 --summary

# Parse a document
python3 -m opencode_media report.pdf --summary

# Get full JSON output
python3 -m opencode_media image.png --json
```

## Using with Agents

Agents process files through the Python module when direct vision is unavailable:

```python
from opencode_media import process_file, summarize_results

result = process_file("screenshot.png")
summary = summarize_results(result)
# summary is ready for LLM consumption
```

## Architecture

```
User shares file
      │
      ▼
Modality Detection
      │
      ├── image    → PIL + pytesseract OCR
      ├── audio    → Whisper transcription + ffprobe
      ├── video    → ffmpeg frames + whisper audio
      ├── document → pdftotext / pandoc conversion
      └── text/code → direct read
      │
      ▼
Structured Result (JSON)
      │
      ▼
Summary for LLM (text)
```

## Dependencies

Optional — the module degrades gracefully if tools are missing:

| Capability | Tool | Install |
|-----------|------|---------|
| Image metadata | Pillow | `pip install Pillow` |
| OCR | pytesseract + tesseract | `pip install pytesseract` + system tesseract |
| Audio transcription | whisper | `pip install openai-whisper` |
| Video keyframes | ffmpeg | system `ffmpeg` |
| Audio duration | ffprobe | system `ffprobe` (comes with ffmpeg) |
| PDF text | pdftotext | system `poppler-utils` |
| DOCX/HTML/EPUB | pandoc | system `pandoc` |

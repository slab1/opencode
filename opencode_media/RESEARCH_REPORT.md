# OpenCode Multimodal Agent File Processing — Research Report

**Date**: May 30, 2026  
**Author**: Pioneer Agent  
**Status**: Complete  

---

## Executive Summary

This research investigates how OpenCode AI agents can read, understand, and manipulate images, videos, audio, documents, and other file types shared through prompts or attachments. The result is a **Three-Pillar Architecture** that extends agents with multimodal capabilities without requiring changes to the core OpenCode engine.

---

## 1. Current State Assessment

### What Already Works

| Capability | How | Status |
|-----------|-----|--------|
| **Images via drag-drop/paste** | `@image.png` syntax, clipboard paste | ✅ Working |
| **Images via Read tool** | `read()` returns as file attachment to vision models | ✅ Working (with some bugs reported) |
| **PDF drag-drop** | PR #16926 — added PDF attachment support | ✅ Merged |
| **Video/audio attachments** | PR #22258 — `read_media_file` support for audio/video MIME | ✅ Merged |
| **Vision-capable model detection** | `modalities.input` config flag | ✅ Working |
| **@modelcontextprotocol/server-filesystem** | `read_media_file` tool for images/audio | Available |

### Key Gaps Identified

| Gap | Impact | Current Workaround |
|-----|--------|-------------------|
| No audio transcription | Agents can't process voice notes/meetings | None — audio is opaque |
| No video understanding | Agents can't analyze screen recordings/demos | None — video is opaque |
| No document OCR pipeline | Scanned PDFs can't be read | Manual conversion |
| No image manipulation | Can't resize/crop/convert images | External tools only |
| No cross-modal reasoning | Can't correlate image+audio+text together | Requires manual multi-step |
| Vision-to-text fallback | Text-only models can't use images | Error message |
| Limited MCP integration | Media MCP servers not configured | None |

---

## 2. The Ecosystem: MCP Servers for File/Media Processing

After thorough research, here are the most promising MCP servers organized by capability:

### 📄 Document Processing

| Server | Formats | Key Features | Install |
|--------|---------|-------------|---------|
| **[go-docs-mcp](https://github.com/drolosoft/go-docs-mcp)** | PDF, DOCX, TXT, MD, CSV, Images | 13 tools, OCR, table extraction, search, format conversion | `go install` |
| **[pdf-mcp](https://github.com/jztan/pdf-mcp)** | PDF | 8 tools, hybrid search, OCR, table extraction, image extraction, render pages as PNG | `uvx pdf-mcp` |
| **[mcp-docs](https://github.com/michaelkrauty/mcp-docs)** | PDF, DOCX, PPTX, XLSX, CSV, EPUB, HTML, XML | 25+ tools, semantic search, vector DB, OCR, batch processing | Python |
| **[PaddleOCR MCP](https://www.paddleocr.ai/)** | Images, PDF | OCR, layout analysis, table extraction, formula recognition | `uvx paddleocr-mcp` |

### 🖼️ Image & Video Understanding

| Server | Capabilities | Key Features | Install |
|--------|-------------|-------------|---------|
| **[imagine-mcp](https://github.com/n24q02m/imagine-mcp)** | Image/video understanding + generation | Multi-provider (Gemini/OpenAI/Grok), describe, classify, generate | `uvx imagine-mcp` |
| **[artificer-mcp](https://github.com/bthurlow/artificer-mcp)** | Full media pipeline | Image gen, video gen, audio gen, ImageMagick (57 tools), FFmpeg (25 tools) | `npx artificer-mcp` |
| **[ocr-mcp](https://github.com/sandraschi/ocr-mcp)** | OCR | 10+ engines (DeepSeek-OCR, Florence-2, PP-OCRv5), WIA scanner, batch | Python |
| **[mistral-mcp](https://github.com/swih/mistral-mcp)** | OCR + Audio + Code | Mistral OCR, Voxtral transcription, Codestral FIM | `uvx mistral-mcp` |

### 🎵 Audio Processing

| Server | Capabilities | Install |
|--------|-------------|---------|
| **mistral-mcp** (Voxtral) | Speech transcription with diarization | `uvx mistral-mcp` |
| **artificer-mcp** | TTS, music generation, audio post-processing | `npx artificer-mcp` |

### 📁 Filesystem with Media Support

| Server | Key Tool | Description |
|--------|----------|-------------|
| **@modelcontextprotocol/server-filesystem** | `read_media_file` | Read images/audio files, returns base64 with MIME type |

### Key Insight
**go-docs-mcp** is the standout for document processing — single binary, multi-format, OCR built-in.  
**imagine-mcp** is the best for image/video understanding — unified API across providers.

---

## 3. Architecture: Three-Pillar Design

```
                    ┌─────────────────────────────────────┐
                    │     User Shares File via Prompt       │
                    │  (drag-drop, @file, clipboard, URL)   │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │       Orchestrator / Agent            │
                    │  Detects task involves file/media     │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │  PILLAR 1    │  │  PILLAR 2    │  │  PILLAR 3    │
            │ Native Tools │  │ MCP Servers  │  │ Subagents    │
            └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                   │                 │                 │
                   ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ read tool     │  │ go-docs-mcp  │  │ media-agent   │
            │ (images,PDFs, │  │ pdf-mcp      │  │ (images,audio,│
            │  audio,video) │  │ imagine-mcp  │  │  video)       │
            │ analyze tool  │  │ artificer-mcp│  │              │
            │ (proposed)    │  │ filesystem   │  │document-agent │
            └──────────────┘  └──────────────┘  │ (documents)   │
                                                └──────────────┘
```

### Pillar 1: Native Tooling (Built-in Agent Tools)
- Extend the existing `read` tool to support more media types
- Add new agent tools: `analyze_image`, `transcribe_audio`, `parse_document`
- Use the model's `modalities` config to detect vision/audio capabilities

### Pillar 2: MCP Server Integration (Pluggable)
- Register media-processing MCP servers in `opencode.jsonc`
- Tools become available to all agents automatically
- Modular — enable only what you need

### Pillar 3: Specialized Subagents (Orchestrated)
- **media-agent**: Handles images, audio, video — describes, transcribes, analyzes
- **document-agent**: Handles PDFs, DOCX, spreadsheets — extracts, searches, converts
- Invoked via `task` tool from primary agents

---

## 4. Prototype: opencode_media Module

Created at `/home/.config/opencode/opencode_media/`

**Core capabilities** (all degrade gracefully if tools are missing):
- **Image analysis**: metadata extraction, OCR (tesseract)
- **Audio transcription**: Whisper-based speech-to-text
- **Video analysis**: ffmpeg keyframe extraction + audio transcription
- **Document parsing**: PDF (pdftotext), DOCX/HTML/EPUB (pandoc), CSV/TXT/MD (native)
- **Unified pipeline**: `process_file()` auto-detects modality and routes accordingly
- **LLM-ready output**: `summarize_results()` produces clean text summaries

**Agent usage patterns** (8 patterns documented in `examples/agent_usage.py`):
1. Process any file type
2. OCR text from screenshots
3. Transcribe meeting recordings
4. Analyze video demos
5. Parse PDFs and documents
6. Batch process multiple files
7. Router pattern for orchestration
8. Generate LLM-ready media descriptions

---

## 5. Recommended MCP Configuration

Add to `opencode.jsonc` `mcp` section:

```jsonc
"mcp": {
  "go-docs-mcp": {
    "type": "local",
    "command": ["go-docs-mcp"],
    "enabled": true,
    "env": { "DOCS_MCP_DIR": "/path/to/docs" }
  },
  "imagine-mcp": {
    "type": "local",
    "command": ["uvx", "imagine-mcp"],
    "enabled": false,
    "env": { "GEMINI_API_KEY": "" }
  }
}
```

---

## 6. Priority Recommendations

### Immediate (0-2 weeks)
1. **✅ DONE**: Agent configs for `media-agent` and `document-agent`
2. **✅ DONE**: Python media processor module (`opencode_media`)
3. **☐ Install go-docs-mcp** for multi-format document access
4. **☐ Add permission rules** for new agents to `opencode.jsonc`

### Short-term (2-6 weeks)
5. **☐ Install imagine-mcp** for image/video understanding
6. **☐ Add new tools to agent system** (analyze, transcribe, parse)
7. **☐ Create multimodal workflow** in WORKFLOWS.md
8. **☐ Add vision-to-text fallback** for text-only models

### Medium-term (6-18 weeks)
9. **☐ Implement `read_media` tool** wrapping the opencode_media module
10. **☐ Build MCP auto-discovery** — detect and suggest configuration
11. **☐ Add speaker diarization** for multi-speaker audio
12. **☐ Add real-time streaming** for video/audio processing

---

## 7. Key References

### MCP Servers
- [go-docs-mcp](https://github.com/drolosoft/go-docs-mcp) — Multi-format document server
- [imagine-mcp](https://github.com/n24q02m/imagine-mcp) — Image/video understanding + generation
- [artificer-mcp](https://github.com/bthurlow/artificer-mcp) — Full creative media pipeline
- [ocr-mcp](https://github.com/sandraschi/ocr-mcp) — Multi-engine OCR server
- [mistral-mcp](https://github.com/swih/mistral-mcp) — OCR, transcription, code
- [pdf-mcp](https://github.com/jztan/pdf-mcp) — Advanced PDF processing
- [PaddleOCR MCP](https://www.paddleocr.ai/) — Document layout analysis
- [@modelcontextprotocol/server-filesystem](https://github.com/modelcontextprotocol/servers) — Filesystem with media support

### OpenCode Issues/PRs
- [#22258](https://github.com/anomalyco/opencode/pull/22258) — Media attachments in read tool
- [#16926](https://github.com/anomalyco/opencode/pull/16926) — PDF drag and drop
- [#26160](https://github.com/anomalyco/opencode/issues/26160) — Auto Image Read feature request
- [#22828](https://github.com/anomalyco/opencode/issues/22828) — Auto image-to-text transcription

### Architecture References
- [Multimodal Agent Architecture Guide](https://callsphere.ai/blog/multimodal-agent-architecture-text-images-audio-video-processing.md)
- [Multi-Agent Multi-Modal AI Systems](https://medium.com/@prklipi/multi-agent-multi-modal-ai-systems-architecture-design-patterns-and-implementation-8b606da1c9b5)
- [Building Multimodal AI Agents That See, Read, and Talk](https://www.gocodeo.com/post/building-multimodal-ai-agents-that-see-read-and-talk)
- [The 2026 Python Stack for Real-Time Multimodal Agents](https://github.com/argotdev/multimodal-python-stack)

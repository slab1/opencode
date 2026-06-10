"""
Example: How agents can use the opencode_media module for file processing.

This demonstrates the patterns agents would follow when asked to
process images, audio, video, or documents.
"""

import sys
import os

# Add parent to path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opencode_media import (
    process_file,
    summarize_results,
    analyze_image,
    transcribe_audio,
    analyze_video,
    parse_document,
    detect_modality,
    get_file_info,
)


# ── Pattern 1: Agent receives a file to process ────────────────────

def pattern_agent_processes_any_file(file_path: str):
    """Agent pattern: Process any file type and return text summary."""
    print(f"\n{'='*60}")
    print(f"PATTERN 1: Process any file")
    print(f"{'='*60}")
    
    result = process_file(file_path)
    summary = summarize_results(result)
    
    print(summary)
    return summary


# ── Pattern 2: Agent needs to extract text from a screenshot ───────

def pattern_ocr_screenshot(screenshot_path: str):
    """Agent pattern: Extract text from a UI screenshot."""
    print(f"\n{'='*60}")
    print(f"PATTERN 2: Extract text from screenshot")
    print(f"{'='*60}")
    
    analysis = analyze_image(screenshot_path)
    
    # Check if OCR extracted text
    if analysis.get('ocr_text'):
        print(f"✅ Found text in screenshot:")
        print(f"```\n{analysis['ocr_text'][:1000]}\n```")
    else:
        print(f"⚠️  No text extracted from screenshot")
        if analysis.get('warnings'):
            for w in analysis['warnings']:
                print(f"  - {w}")
    
    print(f"\n📏 Dimensions: {analysis.get('basic_info', {}).get('width', '?')}x"
          f"{analysis.get('basic_info', {}).get('height', '?')}")
    
    return analysis


# ── Pattern 3: Agent transcribes a meeting recording ───────────────

def pattern_transcribe_meeting(audio_path: str):
    """Agent pattern: Transcribe a meeting recording."""
    print(f"\n{'='*60}")
    print(f"PATTERN 3: Transcribe meeting recording")
    print(f"{'='*60}")
    
    result = transcribe_audio(audio_path, model='base')
    
    if result.get('text'):
        print(f"📝 Transcription ({result.get('duration', '?')}s):")
        print(f"```\n{result['text'][:2000]}\n```")
        if result.get('language'):
            print(f"🌐 Language: {result['language']}")
    else:
        print(f"⚠️  Could not transcribe audio")
    
    return result


# ── Pattern 4: Agent analyzes a video demo ─────────────────────────

def pattern_analyze_video_demo(video_path: str):
    """Agent pattern: Analyze a demo/educational video."""
    print(f"\n{'='*60}")
    print(f"PATTERN 4: Analyze video demo")
    print(f"{'='*60}")
    
    result = analyze_video(video_path, max_frames=3)
    
    info = result.get('basic_info', {})
    print(f"⏱️  Duration: {info.get('duration', '?')}s")
    print(f"🎬 Resolution: {info.get('width', '?')}x{info.get('height', '?')}")
    print(f"🎥 Codec: {info.get('video_codec', '?')}")
    
    frames = result.get('frames', [])
    if frames:
        print(f"🖼️  Extracted {len(frames)} keyframes:")
        for f in frames:
            print(f"  - {f}")
    
    if result.get('transcription', {}).get('text'):
        print(f"\n📝 Audio from video:")
        print(f"```\n{result['transcription']['text'][:1000]}\n```")
    
    return result


# ── Pattern 5: Agent parses a PDF document ─────────────────────────

def pattern_parse_document(document_path: str):
    """Agent pattern: Parse a PDF or document file."""
    print(f"\n{'='*60}")
    print(f"PATTERN 5: Parse document")
    print(f"{'='*60}")
    
    result = parse_document(document_path)
    
    meta = result.get('metadata', {})
    pages = result.get('page_count')
    
    print(f"📄 Type: {result.get('file', {}).get('extension', '?')}")
    if pages:
        print(f"📄 Pages: {pages}")
    if meta.get('title'):
        print(f"📌 Title: {meta['title']}")
    if meta.get('author'):
        print(f"✍️  Author: {meta['author']}")
    
    content = result.get('content')
    if content:
        print(f"\n📝 Content ({len(content)} chars):")
        preview = content[:1500]
        if len(content) > 1500:
            preview += "\n\n[...truncated...]"
        print(f"```\n{preview}\n```")
    else:
        print(f"⚠️  Could not extract content")
        if result.get('warnings'):
            for w in result['warnings']:
                print(f"  - {w}")
    
    return result


# ── Pattern 6: Agent processes a batch of files ────────────────────

def pattern_batch_process(file_paths: list):
    """Agent pattern: Process multiple files of different types."""
    print(f"\n{'='*60}")
    print(f"PATTERN 6: Batch process {len(file_paths)} files")
    print(f"{'='*60}")
    
    all_results = []
    for path in file_paths:
        info = get_file_info(path)
        print(f"\n📁 [{info['modality'].upper()}] {info['filename']} ({info['size_human']})")
        
        result = process_file(path)
        all_results.append(result)
        
        # Quick summary per file
        if result['modality'] == 'image':
            dims = result.get('basic_info', {})
            print(f"  📏 {dims.get('width', '?')}x{dims.get('height', '?')}")
            if result.get('ocr_text'):
                print(f"  ✅ OCR text: {len(result['ocr_text'])} chars")
        elif result['modality'] == 'audio':
            dur = result.get('duration', 0)
            print(f"  ⏱️  {dur}s", end='')
            if result.get('text'):
                print(f", 📝 {len(result['text'])} chars transcribed")
            else:
                print()
        elif result['modality'] == 'document':
            print(f"  📄 {result.get('page_count', '?')} pages", end='')
            content = result.get('content', '')
            print(f", 📝 {len(content) if content else 0} chars")
        elif result['modality'] == 'video':
            info = result.get('basic_info', {})
            frames = len(result.get('frames', []))
            print(f"  ⏱️  {info.get('duration', '?')}s, 🖼️  {frames} frames")
    
    print(f"\n{'─'*40}")
    print(f"✅ Processed {len(file_paths)} files")
    
    # If a document has content, summarize across all files
    combined_texts = []
    for r in all_results:
        if r['modality'] == 'document' and r.get('content'):
            combined_texts.append(r['content'][:500])
        if r['modality'] == 'image' and r.get('ocr_text'):
            combined_texts.append(f"[Image OCR]: {r['ocr_text'][:500]}")
    
    if combined_texts:
        print(f"📋 Combined context: {sum(len(t) for t in combined_texts)} chars")
    
    return all_results


# ── Pattern 7: Router pattern for agent orchestration ──────────────

def pattern_media_router(file_path: str, task_description: str):
    """Agent pattern: Route a task to the right processing approach based on file type."""
    modality = detect_modality(file_path)
    info = get_file_info(file_path)
    
    print(f"\n{'='*60}")
    print(f"PATTERN 7: Media Router")
    print(f"{'='*60}")
    print(f"📁 {info['filename']}")
    print(f"🏷️  Detected modality: {modality}")
    print(f"🎯 Task: {task_description}")
    print(f"{'─'*40}")
    
    # Routing logic
    if modality == 'image':
        print("🔀 Routing to: Image Analyzer")
        print("   Approach: Analyze with vision model or OCR")
        print("   Tools: read (native), pytesseract, imagine-mcp")
        print("   Strategy: Extract scene description + text via OCR")
    
    elif modality == 'audio':
        print("🔀 Routing to: Audio Transcriber")
        print("   Approach: Transcribe speech to text")
        print("   Tools: whisper, ffprobe")
        print("   Strategy: Transcribe → segment → summarize")
    
    elif modality == 'video':
        print("🔀 Routing to: Video Analyzer")
        print("   Approach: Extract keyframes + transcribe audio")
        print("   Tools: ffmpeg, whisper, imagine-mcp")
        print("   Strategy: Sample frames → describe scenes → transcribe audio → synthesize")
    
    elif modality == 'document':
        print("🔀 Routing to: Document Parser")
        print("   Approach: Extract text, tables, and structure")
        print("   Tools: pdftotext, pandoc, go-docs-mcp, pdf-mcp")
        print("   Strategy: Get metadata → extract content → extract tables → convert format")
    
    elif modality in ('code', 'text'):
        print("🔀 Routing to: Text Reader")
        print("   Approach: Direct read")
        print("   Tools: read tool")
        print("   Strategy: Read content directly")
    
    else:
        print("🔀 Routing to: Unknown")
        print("   Approach: Basic file info only")
        print("   Strategy: Report file type not supported")
    
    return modality


# ── Pattern 8: Agent generates media description for context ───────

def pattern_describe_for_context(file_path: str) -> str:
    """Agent pattern: Generate a rich text description of a media file
    so it can be used as context by a text-only LLM."""
    print(f"\n{'='*60}")
    print(f"PATTERN 8: Describe for LLM Context")
    print(f"{'='*60}")
    
    result = process_file(file_path)
    summary = summarize_results(result)
    
    # Wrap in structured context block
    context_block = f"""<media_context>
{summary}
</media_context>"""
    
    print(context_block[:500])
    print(f"\n📊 Total context size: {len(context_block)} chars")
    print(f"   (vs. raw file: {result.get('file', {}).get('size_human', '?')})")
    
    return context_block


# ── Main ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║  OpenCode Media Processing - Agent Usage Examples        ║
║                                                          ║
║  Run with: python examples/agent_usage.py <file_path>    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            print(f"\n🔍 Processing: {file_path}")
            
            # Run all patterns on the file
            pattern_agent_processes_any_file(file_path)
            pattern_media_router(file_path, "Analyze this file")
            summary = pattern_describe_for_context(file_path)
            
            # Run modality-specific pattern
            modality = detect_modality(file_path)
            if modality == 'image':
                pattern_ocr_screenshot(file_path)
            elif modality == 'audio':
                pattern_transcribe_meeting(file_path)
            elif modality == 'video':
                pattern_analyze_video_demo(file_path)
            elif modality == 'document':
                pattern_parse_document(file_path)
        else:
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
    else:
        print("📋 8 agent usage patterns defined:")
        print("  1. process_file()        → Auto-detect and process any file")
        print("  2. analyze_image()        → Extract text from screenshots")
        print("  3. transcribe_audio()     → Transcribe meeting recordings")
        print("  4. analyze_video()        → Analyze video demos")
        print("  5. parse_document()       → Parse PDFs and documents")
        print("  6. batch_process()        → Process multiple file types")
        print("  7. media_router()         → Route tasks to right processor")
        print("  8. describe_for_context() → Generate LLM-ready descriptions")
        print()
        print(f"Usage: python {sys.argv[0]} <path_to_file>")

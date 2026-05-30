"""
opencode_media — Multimodal File Processing Module for OpenCode Agents

This module provides a unified processing pipeline for images, audio, video,
and documents. It acts as a bridge between raw media files and text-based
AI agents, enabling agents to "see," "hear," and "read" through text.

Architecture:
    Detection → Routing → Processing → Structured Output

Dependencies (optional, degrade gracefully):
    - Pillow: image basic info
    - pytesseract: OCR for images
    - ffmpeg/ffprobe: audio/video metadata
    - whisper: audio transcription
    - pdftotext: PDF text extraction
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

__version__ = "0.1.0"


# ── Modality Detection ───────────────────────────────────────────────

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.tiff', '.ico'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.m4v', '.3gp'}
DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.pptx', '.csv', '.md', '.txt', '.html', '.htm', '.epub'}
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
                   '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh', '.bash',
                   '.yaml', '.yml', '.json', '.xml', '.toml', '.ini', '.cfg', '.conf',
                   '.sql', '.r', '.m', '.mm', '.dart', '.lua', '.pl', '.pm', '.ex', '.exs'}


def detect_modality(file_path: str) -> str:
    """Detect the modality of a file based on its extension.
    
    Returns one of: 'image', 'audio', 'video', 'document', 'code', 'text', 'unknown'
    """
    ext = Path(file_path).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    elif ext in DOCUMENT_EXTENSIONS:
        return 'document'
    elif ext in CODE_EXTENSIONS:
        return 'code'
    else:
        # Check for text files by trying to read as text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
                f.read(1024)
            return 'text'
        except (UnicodeDecodeError, IOError):
            return 'unknown'


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get basic file information."""
    p = Path(file_path)
    exists = p.exists()
    size_bytes = p.stat().st_size if exists else 0
    return {
        'path': str(p.absolute()),
        'filename': p.name,
        'extension': p.suffix.lower(),
        'size_bytes': size_bytes,
        'size_human': _format_size(size_bytes),
        'modality': detect_modality(file_path),
        'exists': exists,
    }


def _format_size(bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"


# ── Image Processing ─────────────────────────────────────────────────

def analyze_image(file_path: str, detail: str = 'high') -> Dict[str, Any]:
    """Analyze an image file, extracting available information.
    
    Returns a dict with:
    - basic_info: dimensions, format, mode, size
    - ocr_text: extracted text (if tesseract available)
    - description: high-level description of the image
    - metadata: EXIF and other available metadata
    """
    result = {
        'status': 'success',
        'modality': 'image',
        'file': get_file_info(file_path),
        'basic_info': {},
        'ocr_text': None,
        'metadata': {},
        'warnings': [],
    }
    
    # Try Pillow for basic image info
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS as EXIF_TAGS
        
        with Image.open(file_path) as img:
            result['basic_info'] = {
                'format': img.format,
                'mode': img.mode,
                'width': img.width,
                'height': img.height,
                'aspect_ratio': f"{img.width / img.height:.2f}" if img.height > 0 else "N/A",
            }
            
            # Try to extract EXIF metadata
            if hasattr(img, '_getexif') and img._getexif():
                exif_data = {}
                for tag_id, value in img._getexif().items():
                    tag_name = EXIF_TAGS.get(tag_id, tag_id)
                    # Decode bytes if needed
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='replace')
                        except:
                            value = str(value)
                    exif_data[tag_name] = str(value)
                result['metadata'] = exif_data
    except ImportError:
        result['warnings'].append('Pillow not installed — limited image metadata')
    except Exception as e:
        result['warnings'].append(f'Image metadata extraction error: {e}')
    
    # Try OCR with tesseract
    try:
        import pytesseract
        ocr_text = pytesseract.image_to_string(file_path)
        if ocr_text.strip():
            result['ocr_text'] = ocr_text.strip()
    except ImportError:
        result['warnings'].append('pytesseract not installed — OCR unavailable')
    except Exception as e:
        result['warnings'].append(f'OCR error: {e}')
    
    return result


def extract_frames(video_path: str, max_frames: int = 5, interval: Optional[int] = None) -> List[str]:
    """Extract key frames from a video file as temporary images.
    
    Returns list of paths to extracted frame images.
    """
    frames = []
    try:
        # Get video duration
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ]
        duration = float(subprocess.check_output(duration_cmd, stderr=subprocess.STDOUT).decode().strip())
        
        if interval is None:
            interval = max(1, duration / max_frames)
        
        temp_dir = tempfile.mkdtemp(prefix='opencode_frames_')
        
        for i in range(max_frames):
            time_point = i * interval
            if time_point > duration:
                break
            
            frame_path = os.path.join(temp_dir, f'frame_{i:03d}.jpg')
            extract_cmd = [
                'ffmpeg', '-y', '-ss', str(time_point), '-i', video_path,
                '-vframes', '1', '-q:v', '3', frame_path
            ]
            subprocess.run(extract_cmd, capture_output=True, timeout=30)
            
            if os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
                frames.append(frame_path)
    
    except FileNotFoundError:
        pass  # ffmpeg not installed
    except Exception as e:
        pass  # Silently handle errors
    
    return frames


def transcribe_audio(file_path: str, model: str = 'base') -> Dict[str, Any]:
    """Transcribe an audio file using whisper.
    
    Returns dict with:
    - text: full transcription
    - segments: timestamped segments (if available)
    - language: detected language
    - duration: audio duration in seconds
    """
    result = {
        'status': 'success',
        'modality': 'audio',
        'file': get_file_info(file_path),
        'text': None,
        'segments': [],
        'language': None,
        'duration': None,
        'warnings': [],
    }
    
    # Get duration via ffprobe
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', file_path
        ]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        if output:
            result['duration'] = round(float(output), 1)
    except Exception as e:
        result['warnings'].append(f'Could not get duration: {e}')
    
    # Try whisper
    try:
        import whisper
        model_whisper = whisper.load_model(model)
        transcript = model_whisper.transcribe(file_path)
        result['text'] = transcript.get('text', '').strip()
        result['language'] = transcript.get('language')
        if 'segments' in transcript:
            result['segments'] = [
                {
                    'start': round(seg.get('start', 0), 1),
                    'end': round(seg.get('end', 0), 1),
                    'text': seg.get('text', '').strip(),
                }
                for seg in transcript['segments']
            ]
    except ImportError:
        result['warnings'].append('whisper not installed — transcription unavailable')
    except Exception as e:
        result['warnings'].append(f'Transcription error: {e}')
    
    return result


def analyze_video(file_path: str, max_frames: int = 5) -> Dict[str, Any]:
    """Analyze a video file, extracting frames and available metadata.
    
    Returns dict with:
    - basic_info: duration, dimensions, codec, fps
    - frames: extracted keyframe images
    - transcription: audio transcription (if available)
    """
    result = {
        'status': 'success',
        'modality': 'video',
        'file': get_file_info(file_path),
        'basic_info': {},
        'frames': [],
        'transcription': None,
        'warnings': [],
    }
    
    # Get video metadata via ffprobe
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration,size,bit_rate',
            '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate',
            '-of', 'json', file_path
        ]
        output = json.loads(subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode())
        
        if 'format' in output:
            fmt = output['format']
            result['basic_info']['duration'] = round(float(fmt.get('duration', 0)), 1)
            result['basic_info']['bit_rate'] = fmt.get('bit_rate')
        
        if 'streams' in output:
            for stream in output['streams']:
                if stream.get('codec_type') == 'video':
                    result['basic_info']['video_codec'] = stream.get('codec_name')
                    result['basic_info']['width'] = stream.get('width')
                    result['basic_info']['height'] = stream.get('height')
                    fps_str = stream.get('r_frame_rate', '0/1')
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        fps = float(num) / float(den) if float(den) > 0 else 0
                        result['basic_info']['fps'] = round(fps, 1)
                elif stream.get('codec_type') == 'audio':
                    result['basic_info']['audio_codec'] = stream.get('codec_name')
    except Exception as e:
        result['warnings'].append(f'Video metadata error: {e}')
    
    # Extract keyframes
    result['frames'] = extract_frames(file_path, max_frames=max_frames)
    if result['frames']:
        result['basic_info']['extracted_frames'] = len(result['frames'])
    
    # Try audio transcription
    try:
        result['transcription'] = transcribe_audio(file_path)
    except Exception as e:
        result['warnings'].append(f'Audio extraction error: {e}')
    
    return result


def parse_document(file_path: str) -> Dict[str, Any]:
    """Parse a document file, extracting text content and structure.
    
    Supports: PDF, DOCX, CSV, TXT, MD, HTML
    Uses external tools (pdftotext, pandoc) when available, falls back to basic extraction.
    """
    result = {
        'status': 'success',
        'modality': 'document',
        'file': get_file_info(file_path),
        'content': None,
        'metadata': {},
        'page_count': None,
        'tables': [],
        'warnings': [],
    }
    
    ext = Path(file_path).suffix.lower()
    
    # PDF processing
    if ext == '.pdf':
        # Try pdftotext first (fast, reliable)
        try:
            cmd = ['pdftotext', '-layout', file_path, '-']
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=60).decode('utf-8', errors='replace')
            if output.strip():
                result['content'] = output
            
            # Get page count
            info_cmd = ['pdfinfo', file_path]
            info_output = subprocess.check_output(info_cmd, stderr=subprocess.STDOUT, timeout=30).decode('utf-8', errors='replace')
            for line in info_output.split('\n'):
                if 'Pages' in line:
                    try:
                        result['page_count'] = int(line.split(':')[1].strip())
                    except:
                        pass
                if 'Title' in line:
                    title = line.split(':', 1)[1].strip()
                    if title:
                        result['metadata']['title'] = title
                if 'Author' in line:
                    author = line.split(':', 1)[1].strip()
                    if author:
                        result['metadata']['author'] = author
        except FileNotFoundError:
            result['warnings'].append('pdftotext not installed — install poppler-utils')
        except Exception as e:
            result['warnings'].append(f'PDF extraction error: {e}')
    
    # Text, Markdown, CSV (native support)
    elif ext in ('.txt', '.md', '.csv'):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                result['content'] = f.read()
        except Exception as e:
            result['warnings'].append(f'Read error: {e}')
    
    # DOCX, XLSX, PPTX, HTML — try pandoc
    elif ext in ('.docx', '.html', '.htm', '.epub'):
        try:
            cmd = ['pandoc', file_path, '-t', 'markdown', '--wrap=none']
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=60).decode('utf-8', errors='replace')
            if output.strip():
                result['content'] = output
        except FileNotFoundError:
            result['warnings'].append('pandoc not installed — install pandoc for DOCX/HTML support')
        except Exception as e:
            result['warnings'].append(f'Conversion error: {e}')
    
    else:
        # Try reading any file as text (handles code files, configs, etc.)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if len(content.strip()) > 0:
                result['content'] = content
        except Exception as e:
            result['warnings'].append(f'Could not read as text ({ext}): {e}')
    
    return result


# ── Unified Processing Pipeline ───────────────────────────────────────

def process_file(file_path: str, **kwargs) -> Dict[str, Any]:
    """Unified file processing — detect modality and route to appropriate processor.
    
    This is the main entry point for processing any file type.
    """
    if not os.path.exists(file_path):
        return {
            'status': 'error',
            'error': f'File not found: {file_path}',
            'modality': 'unknown',
        }
    
    modality = detect_modality(file_path)
    
    if modality == 'image':
        return analyze_image(file_path, **kwargs)
    elif modality == 'audio':
        return transcribe_audio(file_path, **kwargs)
    elif modality == 'video':
        return analyze_video(file_path, **kwargs)
    elif modality == 'document':
        return parse_document(file_path, **kwargs)
    elif modality in ('code', 'text'):
        return parse_document(file_path, **kwargs)
    else:
        return {
            'status': 'unknown',
            'modality': 'unknown',
            'file': get_file_info(file_path),
            'message': 'File type not recognized as a supported media format',
        }


def summarize_results(results: Dict[str, Any]) -> str:
    """Convert processing results into a concise text summary for LLM consumption."""
    lines = []
    
    modality = results.get('modality', 'unknown').upper()
    file_info = results.get('file', {})
    lines.append(f"📁 File: {file_info.get('filename', 'unknown')}")
    lines.append(f"📐 Size: {file_info.get('size_human', 'unknown')}")
    lines.append(f"🏷️  Modality: {modality}")
    
    if modality == 'IMAGE':
        info = results.get('basic_info', {})
        if info:
            lines.append(f"📏 Dimensions: {info.get('width', '?')}x{info.get('height', '?')}")
            lines.append(f"🎨 Format: {info.get('format', '?')}")
        
        ocr = results.get('ocr_text')
        if ocr:
            lines.append(f"\n📝 Extracted Text (OCR):")
            lines.append(f"```text\n{ocr[:2000]}\n```")
    
    elif modality == 'AUDIO':
        info = results.get('file', {})
        dur = results.get('duration')
        if dur:
            lines.append(f"⏱️  Duration: {dur}s")
        
        text = results.get('text')
        if text:
            lines.append(f"\n📝 Transcription:")
            lines.append(f"```text\n{text[:3000]}\n```")
        
        lang = results.get('language')
        if lang:
            lines.append(f"🌐 Language: {lang}")
    
    elif modality == 'VIDEO':
        info = results.get('basic_info', {})
        if info.get('duration'):
            lines.append(f"⏱️  Duration: {info['duration']}s")
        if info.get('width'):
            lines.append(f"📏 Resolution: {info['width']}x{info['height']}")
        if info.get('fps'):
            lines.append(f"🎬 FPS: {info['fps']}")
        
        frames = results.get('frames', [])
        if frames:
            lines.append(f"🖼️  Extracted {len(frames)} keyframes")
        
        trans = results.get('transcription', {})
        if trans and trans.get('text'):
            lines.append(f"\n📝 Audio Transcription:")
            lines.append(f"```text\n{trans['text'][:2000]}\n```")
    
    elif modality == 'DOCUMENT':
        content = results.get('content')
        pages = results.get('page_count')
        if pages:
            lines.append(f"📄 Pages: {pages}")
        
        meta = results.get('metadata', {})
        if meta.get('title'):
            lines.append(f"📌 Title: {meta['title']}")
        if meta.get('author'):
            lines.append(f"✍️  Author: {meta['author']}")
        
        if content:
            lines.append(f"\n📝 Content Preview ({len(content)} chars):")
            # Show first portion
            preview = content[:2000]
            if len(content) > 2000:
                preview += "\n\n[...content truncated...]"
            lines.append(f"```text\n{preview}\n```")
    
    # Warnings
    warnings = results.get('warnings', [])
    if warnings:
        lines.append(f"\n⚠️  Notes:")
        for w in warnings:
            lines.append(f"  - {w}")
    
    if results.get('status') == 'error':
        lines.append(f"\n❌ Error: {results.get('error', 'Unknown error')}")
    
    return '\n'.join(lines)


# ── CLI Entry Point ───────────────────────────────────────────────────

def main():
    """CLI entry point for processing files."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='OpenCode Media Processor — Analyze images, audio, video, and documents'
    )
    parser.add_argument('file', help='Path to the file to process')
    parser.add_argument('--mode', choices=['auto', 'image', 'audio', 'video', 'document'],
                        default='auto', help='Processing mode (default: auto-detect)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--summary', '-s', action='store_true',
                        help='Output a concise text summary (for LLM consumption)')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output raw JSON')
    parser.add_argument('--frames', type=int, default=5,
                        help='Max keyframes for video (default: 5)')
    parser.add_argument('--whisper-model', default='base',
                        help='Whisper model size (tiny/base/small/medium/large)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(json.dumps({'error': f'File not found: {args.file}'}))
        return 1
    
    # Process
    if args.mode == 'auto':
        result = process_file(args.file, max_frames=args.frames, model=args.whisper_model)
    elif args.mode == 'image':
        result = analyze_image(args.file)
    elif args.mode == 'audio':
        result = transcribe_audio(args.file, model=args.whisper_model)
    elif args.mode == 'video':
        result = analyze_video(args.file, max_frames=args.frames)
    elif args.mode == 'document':
        result = parse_document(args.file)
    
    # Output
    output = None
    if args.summary:
        output = summarize_results(result)
    elif args.json:
        output = json.dumps(result, indent=2, default=str)
    else:
        # Default: short summary for terminal
        summary = summarize_results(result)
        output = json.dumps(result, indent=2, default=str)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Output written to {args.output}")
    else:
        print(output)
    
    return 0


if __name__ == '__main__':
    exit(main())

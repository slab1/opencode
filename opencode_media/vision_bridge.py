"""
Vision Bridge — Automatic image-to-text fallback for text-only models.

This module detects when an image is shared with a model that doesn't
support vision input, and routes it to available processing to generate
a text description that can be used as context.

Architecture:
    User sends image → detect model capabilities → 
      if vision-capable: pass through
      if text-only: extract text description → inject as context

Usage by agents:
    from opencode_media.vision_bridge import process_vision_fallback
    
    # Get a text description of an image for a text-only model
    description = process_vision_fallback("screenshot.png")
    # Use description as context in your prompt
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any, Union
from opencode_media import analyze_image, get_file_info, detect_modality


def describe_image_for_llm(file_path: str, detail_level: str = 'auto') -> str:
    """Create a comprehensive text description of an image for LLM consumption.
    
    This is the primary fallback when a model doesn't support vision input.
    It extracts all available information and formats it as clean text.
    
    Args:
        file_path: Path to the image file
        detail_level: 'auto', 'high', 'low' - controls detail richness
        
    Returns:
        Formatted text description suitable for LLM context injection
    """
    if not os.path.exists(file_path):
        return f"[Image not found: {file_path}]"
    
    modality = detect_modality(file_path)
    if modality != 'image':
        # Not an image - pass through for other processing
        return None
    
    info = get_file_info(file_path)
    analysis = analyze_image(file_path)
    
    parts = []
    parts.append(f"[Image: {info['filename']}]")
    parts.append(f"[Size: {info['size_human']}]")
    
    # Dimensions
    dims = analysis.get('basic_info', {})
    if dims.get('width'):
        parts.append(f"[Dimensions: {dims['width']}x{dims['height']}px]")
    if dims.get('format'):
        parts.append(f"[Format: {dims['format']}]")
    
    # EXIF / metadata
    meta = analysis.get('metadata', {})
    if meta:
        useful = {}
        for k in ['DateTimeOriginal', 'Make', 'Model', 'Software', 'Orientation']:
            if k in meta:
                useful[k] = meta[k]
        if useful:
            parts.append(f"[Camera: {json.dumps(useful)}]")
    
    # OCR text (if available)
    ocr_text = analysis.get('ocr_text')
    if ocr_text and ocr_text.strip():
        text_preview = ocr_text.strip()[:1500]
        if len(ocr_text.strip()) > 1500:
            text_preview += "\n[...OCR text truncated...]"
        parts.append(f"[Text extracted from image]:\n{text_preview}")
    
    # Structure the output
    description = "\n".join(parts)
    
    return description


def check_vision_capability(model_name: str = None, modalities: list = None) -> bool:
    """Check if a model supports vision/image input.
    
    Args:
        model_name: The model identifier string
        modalities: List of supported input modalities
        
    Returns:
        True if the model can process images natively
    """
    # If explicit modalities list is provided, use it
    if modalities is not None:
        return 'image' in modalities
    
    # Model name-based detection
    if model_name:
        model_lower = model_name.lower()
        # These model families typically support vision
        vision_keywords = [
            'vision', 'vl', 'vlm', 'multimodal',
            'gpt-4o', 'gpt-5', 'claude-3.5', 'claude-3-opus',
            'claude-sonnet-4', 'gemini-2', 'gemini-3',
            'grok-vision', 'reka', 'qwen-vl', 'llava',
            'deepseek-vl', 'cogvlm', 'idefics', 'fuyu',
            'pixtral', 'molmo',
        ]
        for keyword in vision_keywords:
            if keyword in model_lower:
                return True
    
    # Default: assume text-only for safety
    return False


def process_vision_fallback(
    file_path: str,
    model_name: str = None,
    model_modalities: list = None,
    user_prompt: str = ""
) -> Dict[str, Any]:
    """Process a file with vision fallback logic.
    
    This is the main entry point for the vision bridge.
    It determines whether the model can handle the file natively
    or needs a text description fallback.
    
    Args:
        file_path: Path to the file
        model_name: Name of the AI model being used
        model_modalities: List of modalities the model supports
        user_prompt: The user's original prompt for context
        
    Returns:
        Dict with:
        - modality: detected file type
        - can_handle_natively: whether the model can process directly
        - text_description: text fallback (None if natively handled)
        - metadata: file metadata
    """
    modality = detect_modality(file_path)
    has_vision = check_vision_capability(model_name, model_modalities)
    
    result = {
        'file_path': file_path,
        'modality': modality,
        'can_handle_natively': has_vision and modality == 'image',
        'text_description': None,
        'metadata': get_file_info(file_path),
    }
    
    # If model can handle images natively, no fallback needed
    if has_vision and modality == 'image':
        return result
    
    # Generate text description as fallback
    if modality == 'image':
        result['text_description'] = describe_image_for_llm(file_path)
    elif modality == 'document':
        from opencode_media import parse_document, summarize_results
        doc_result = parse_document(file_path)
        result['text_description'] = summarize_results(doc_result)
    elif modality in ('code', 'text'):
        from opencode_media import parse_document
        doc_result = parse_document(file_path)
        content = doc_result.get('content', '')
        if content:
            result['text_description'] = content[:5000]  # Truncate for context
    elif modality == 'audio':
        result['text_description'] = f"[Audio file: {Path(file_path).name}. Transcription requires whisper model or MCP server.]"
    elif modality == 'video':
        result['text_description'] = f"[Video file: {Path(file_path).name}. Analysis requires ffmpeg + whisper or MCP server.]"
    else:
        result['text_description'] = f"[File: {Path(file_path).name}. Type '{modality}' may not be processable by this model.]"
    
    return result


# ── CLI ──

def main():
    """CLI entry point for vision bridge."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Vision Bridge — Convert images to text descriptions for LLMs'
    )
    parser.add_argument('file', help='Path to the image file')
    parser.add_argument('--model', '-m', help='Model name (for vision capability check)')
    parser.add_argument('--prompt', '-p', help='User prompt for context')
    parser.add_argument('--output', '-o', help='Output file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(json.dumps({'error': f'File not found: {args.file}'}))
        return 1
    
    result = process_vision_fallback(
        args.file,
        model_name=args.model,
        user_prompt=args.prompt or ""
    )
    
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

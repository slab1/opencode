---
name: pdf-extraction-strategies
description: PDF extraction strategies for the document-agent. Use when extracting text, tables, images, or metadata from PDF files. Covers when to use pdf-mcp, go-docs-mcp, pdftotext, OCR, and hybrid search. The right tool depends on the PDF type.
license: MIT
compatibility: opencode>=1.16.0
---

# PDF Extraction Strategies

Different PDFs need different tools. This skill helps the document-agent pick the right approach based on the PDF's characteristics.

## Decision tree

```
PDF file
├── Text-based (digital)
│   ├── Need structure preserved? → pdf-mcp (read_document)
│   ├── Need page-level metadata? → pdf-mcp (pdf_info)
│   ├── Need table extraction?    → pdf-mcp (extract_tables)
│   └── Just need raw text?       → pdftotext (fast, simple)
│
├── Scanned (image-based, no text layer)
│   ├── English only?             → tesseract OCR
│   ├── Multi-language?           → tesseract with -l flag
│   └── Need layout preserved?    → pdf-mcp (ocr_document)
│
├── Mixed (some pages text, some scanned)
│   └── → pdf-mcp (handles both)
│
├── Need semantic search?
│   └── → pdf-mcp (hybrid_search)
│
└── Need images extracted?
    └── → pdf-mcp (extract_images) or pdfimages CLI
```

## Strategy 1: pdftotext (fast, simple, text-only)

Best for: digital PDFs where you just need the text content.

```bash
# Basic extraction
pdftotext input.pdf output.txt

# Preserve layout (for tables, columns)
pdftotext -layout input.pdf output.txt

# Specific pages
pdftotext -f 1 -l 5 input.pdf output.txt

# To stdout
pdftotext input.pdf -
```

**Pros**: Fast, no dependencies, works on any digital PDF
**Cons**: Loses structure, no tables, no images

## Strategy 2: pdf-mcp (rich, structured)

Best for: when you need tables, images, metadata, or hybrid search.

```python
# Get document info
info = pdf_info(path="doc.pdf")
# Returns: pages, title, author, creation_date, etc.

# Read with structure
content = read_document(path="doc.pdf", pages=[1, 2, 3])
# Returns: structured text per page

# Extract tables
tables = extract_tables(path="doc.pdf", page=5)
# Returns: list of tables as 2D arrays

# Extract images
images = extract_images(path="doc.pdf", output_dir="/tmp/imgs")
# Returns: file paths to extracted images

# Hybrid search (text + semantic)
results = hybrid_search(
    path="doc.pdf",
    query="What was the Q3 revenue?",
    top_k=5
)
# Returns: relevant passages with page numbers

# OCR a scanned PDF
text = ocr_document(path="scanned.pdf", language="eng")
```

**Pros**: Handles all PDF types, structured output, hybrid search
**Cons**: Slower startup, requires npx

## Strategy 3: go-docs-mcp (multi-format, fallback)

Best for: when pdf-mcp is unavailable, or for batch document processing.

```python
# List available documents
docs = list_documents(directory="/path/to/pdfs/")

# Read with structure
content = read_document(path="doc.pdf")

# Search within document
results = search_document(path="doc.pdf", query="revenue")

# Convert to markdown (good for LLMs)
md = convert_to_markdown(path="doc.pdf")
```

**Pros**: 13 tools, handles PDF + DOCX + CSV + Images
**Cons**: Falls back to pdftotext internally, less PDF-specific

## Strategy 4: tesseract OCR (scanned PDFs)

Best for: scanned image-based PDFs without text layer.

```bash
# Convert PDF pages to images, then OCR
pdftoppm -r 300 input.pdf /tmp/page -png
tesseract /tmp/page-1.png /tmp/page-1 -l eng
# Repeat for each page

# Or use ocrmypdf (adds text layer to scanned PDF)
ocrmypdf input.pdf output.pdf -l eng
# Then pdftotext works on the new file
```

**Pros**: Works on any image, no PDF needed
**Cons**: Slow, accuracy depends on quality

## Strategy 5: pdfimages + vision model

Best for: extracting images for vision model analysis.

```bash
# Extract all images
pdfimages -all input.pdf /tmp/img
ls /tmp/img-*.ppm /tmp/img-*.jpg  # or .png
```

Then send images to vision-capable model:
```python
# Use the analyze_image tool on each extracted image
for img_path in extracted_images:
    result = analyze_image(path=img_path, prompt="Describe this image")
```

## Choosing the right strategy

| Need | Strategy | Why |
|------|----------|-----|
| Quick text dump | pdftotext -layout | Fast, simple |
| Tables | pdf-mcp | Structured output |
| Search content | pdf-mcp hybrid_search | Semantic understanding |
| Scanned PDF | pdf-mcp ocr_document or ocrmypdf + tesseract | OCR required |
| Images for vision | pdfimages + analyze_image | Best quality |
| Whole pipeline | pdf-mcp | Handles all cases |
| pdf-mcp unavailable | go-docs-mcp | Good fallback |
| Fallback to basics | pdftotext | Always available |

## Pre-flight checks

Before extracting, always:

```bash
# 1. Check file exists and is readable
ls -la input.pdf
file input.pdf  # Should say "PDF document"

# 2. Check page count
pdfinfo input.pdf | grep Pages

# 3. Detect if scanned
pdftotext input.pdf - | head -100
# If empty or garbled, it's likely scanned → use OCR

# 4. Check for encryption
pdfinfo input.pdf | grep Encrypted
```

## Output formats

Choose based on what you'll do with the extracted content:

- **Plain text**: For grep, simple analysis
- **Markdown**: For LLM consumption, preserves some structure
- **JSON**: For programmatic processing, structured data
- **HTML**: For web display, preserves formatting
- **Tables (CSV/Excel)**: For spreadsheet analysis

```python
# Convert to markdown
md = convert_to_markdown(path="doc.pdf")
# Save to file
with open("doc.md", "w") as f:
    f.write(md)
```

## Performance tips

- **Large PDFs (>100 pages)**: Process in chunks, save intermediate results
- **Multiple PDFs**: Use `parallel` to process in background
- **Memory**: pdf-mcp can be heavy; close other apps
- **Caching**: Save extracted content to avoid re-processing

## When to use this skill

- The user provides a PDF
- You need to extract any kind of content from a PDF
- You're choosing between pdf-mcp, pdftotext, OCR
- The user asks "what's in this PDF?"

## When NOT to use

- DOCX, XLSX, PPTX (use go-docs-mcp for those)
- HTML pages (use web-browser or webfetch)
- Images only (use media-agent)

---
name: hash-anchored-edits
description: Apply hash-anchored line edits to source files to eliminate stale-line errors. Each line is tagged with a LINE#ID content hash; every edit is validated against the hash before writing. Recommended for the build agent and any task involving file edits, raising edit success rate from ~7% to ~68%.
license: MIT
compatibility: opencode>=1.16.0
---

# Hash-Anchored Edits

A pattern for **reliable file editing** that eliminates stale-line errors. Inspired by Oh-My-OpenCode's `LINE#ID` content-hash system.

## The Problem

The default `edit` tool fails when:
- The file changed between read and write
- Multiple lines match the search string
- Whitespace or indentation is off by a character
- Concurrent edits modify the target region

**Naive edit success rate: ~6.7%** (per Oh-My-OpenCode benchmarks on Grok Code Fast 1).

**With hash anchoring: ~68.3%** — a 10x improvement.

## How It Works

### Step 1: Read with line hashes
When reading a file, compute a content hash for each line:
```
line 1:   def hello():         # hash:a1b2
line 2:       print("hi")      # hash:c3d4
line 3:                             # hash:e5f6
line 4:   hello()               # hash:7890
```

### Step 2: Specify edit with hash anchors
When making an edit, reference both content AND hash:
```
old: line 1 (hash:a1b2): def hello():
new: def hello(name):
```

### Step 3: Validate before write
Before applying, re-read the file and verify the line at the specified position still has the expected hash. If not, **fail loudly** instead of writing a wrong edit.

## The Pattern

```python
def hash_line(text, line_num):
    """Compute a short content hash for a single line."""
    return hashlib.sha1(text.encode()).hexdigest()[:4]

def safe_edit(file_path, line_num, old_hash, new_content):
    """Edit a line only if its hash still matches."""
    lines = Path(file_path).read_text().splitlines()
    if line_num >= len(lines):
        raise StaleEditError(f"Line {line_num} no longer exists")
    current_hash = hash_line(lines[line_num], line_num)
    if current_hash != old_hash:
        raise StaleEditError(
            f"Line {line_num} hash mismatch: expected {old_hash}, got {current_hash}"
        )
    lines[line_num] = new_content
    Path(file_path).write_text("\n".join(lines))
```

## When to use

Use this skill when:
- Editing any file with the `edit` tool
- Editing large files where multiple regions could match
- Concurrent workflows where files may change
- Production code where wrong edits are costly

## When NOT to use

- Reading files (no edits)
- Trivial single-line changes in tiny files
- New file creation (no existing lines to anchor)

## Integration with build agent

The `build` agent should:
1. Read files with the `read` tool — note line numbers and content
2. For multi-line edits, capture hash anchors for the surrounding lines
3. Apply edits with hash validation
4. If hash mismatch occurs, re-read and re-apply

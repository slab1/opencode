---
name: hash-validate-edit
description: Validate that a line edit is still valid by re-reading the file and computing a content hash. Use as a pre-flight check before applying any edit, especially when the file may have changed.
license: MIT
compatibility: opencode>=1.16.0
---

# Hash Validate Edit

A **pre-flight check** for file edits. Before applying an edit, verify the target line is still what you think it is.

## Why

Between reading a file and writing it back, the file can change:
- Another process writes to it
- The agent's previous step modified it
- Concurrent subagent work

A naive `edit` operation either:
- Fails silently (no match found)
- Succeeds but writes the wrong change
- Modifies the wrong region

**Hash validation catches all of these before they happen.**

## The Pattern

### Step 1: Read and hash
When you read a file, mentally tag each relevant line with a short hash:
```
12:  config.set("key", "value")   # h:8a3f
13:  return config                  # h:b2c1
```

### Step 2: Build edit with anchors
Specify the edit with both content and hash:
```
old: h:8a3f → config.set("key", "value")
new: config.set("key", default_value)
```

### Step 3: Validate before write
```python
import hashlib
from pathlib import Path

def hash_line(text: str) -> str:
    return hashlib.sha1(text.strip().encode()).hexdigest()[:4]

def validate_edit(file_path: str, line_num: int, expected_hash: str) -> bool:
    """Check that line N still has the expected hash."""
    lines = Path(file_path).read_text().splitlines()
    if line_num >= len(lines):
        return False
    return hash_line(lines[line_num]) == expected_hash

def safe_apply(file_path, line_num, expected_hash, new_content):
    if not validate_edit(file_path, line_num, expected_hash):
        raise StaleEditError(
            f"Line {line_num} hash mismatch — re-read file before editing"
        )
    lines = Path(file_path).read_text().splitlines()
    lines[line_num] = new_content
    Path(file_path).write_text("\n".join(lines))
```

## Failure Modes

| Failure                | Cause                              | Recovery                          |
|------------------------|-------------------------------------|------------------------------------|
| `StaleEditError`       | File changed since read            | Re-read file, re-plan edit        |
| `LineOutOfRange`       | File shrunk, line no longer exists  | Re-read file, find new line number|
| `HashMismatch`         | Line content changed (added spaces) | Re-read file, find right line    |

## When to Use

- Every edit to a file you read more than 30 seconds ago
- Edits during multi-step workflows
- Edits when concurrent processes may be active
- Production code edits where wrong writes are costly

## When Not to Use

- New file creation (no existing lines)
- Trivial single-line edits in small files
- Read-only operations

## Quick Mental Check

Before any `edit` call, ask:
1. Did I read this file recently?
2. Could anything have changed it?
3. Is the line number still valid?
4. Does the content I'm replacing still exist?

If any answer is "unsure" → re-read first.

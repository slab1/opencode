#!/bin/sh
# ── OpenCode Memory Dreaming ────────────────────────────────────────
# Auto-consolidates recent daily notes into long-term knowledge (LTM.md).
# Runs daily via cron. Extracts key findings, decisions, and artifacts
# from daily notes and merges them into a permanent reference file.
# ───────────────────────────────────────────────────────────────────

CONFIG_DIR="${HOME:-/root}/.config/opencode"
MEMORY_DIR="$CONFIG_DIR/memory"
LTM_FILE="$CONFIG_DIR/LTM.md"
LOCK_FILE="/tmp/opencode-dream.lock"
LOG_FILE="$CONFIG_DIR/dream.log"

log() { echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"; }

# Single-instance guard
if [ -f "$LOCK_FILE" ]; then
    read -r pid < "$LOCK_FILE" 2>/dev/null
    if kill -0 "$pid" 2>/dev/null; then
        log "Already running (pid $pid). Skipping."
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

log "=== Dreaming started ==="

# Collect stats
NOTE_COUNT=$(ls "$MEMORY_DIR/"*.md 2>/dev/null | wc -l)
log "Found $NOTE_COUNT daily notes"

# Run the Python consolidator
python3 << 'PYEOF'
import os, re, json, datetime
from pathlib import Path

config_dir = os.environ.get("HOME", "/root") + "/.config/opencode"
memory_dir = config_dir + "/memory"
ltm_path = config_dir + "/LTM.md"

# Read existing LTM if it exists
existing_ltm = ""
if os.path.exists(ltm_path):
    with open(ltm_path) as f:
        existing_ltm = f.read()

# Gather daily notes from last 7 days
notes = sorted(Path(memory_dir).glob("*.md"), reverse=True)[:7]

# Extract structured findings from each note
all_findings = []
all_keywords = set()
note_dates = []

for note in notes:
    content = note.read_text()
    date_match = re.search(r'# Session Notes — (\d{4}-\d{2}-\d{2})', content)
    if date_match:
        note_dates.append(date_match.group(1))
    
    # Extract key findings (lines after "### Key Findings" or bold items)
    findings = re.findall(r'- (.+?)(?:\[[A-Z]+\])?$', content, re.MULTILINE)
    for f in findings:
        f = f.strip()
        if len(f) > 20 and f not in all_findings:
            all_findings.append(f)
            # Extract keywords
            for word in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', f):
                if len(word) > 3:
                    all_keywords.add(word)

# Detect new findings (not in existing LTM)
new_findings = []
for f in all_findings:
    if f not in existing_ltm:
        new_findings.append(f)

# Generate LTM content
if new_findings or not existing_ltm:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_range = f"{note_dates[-1]} to {note_dates[0]}" if len(note_dates) > 1 else (note_dates[0] if note_dates else "unknown")
    
    # Build the consolidated knowledge section
    consolidated = "\n".join(f"- {f}" for f in new_findings[:30])
    
    new_section = f"""
## Dream Session — {now}
**Period**: {date_range} | **Notes consolidated**: {len(notes)}

### Key Knowledge
{consolidated}

### Keywords
{', '.join(sorted(all_keywords)[:50])}

"""

    if existing_ltm:
        # Append to existing LTM
        with open(ltm_path, 'a') as f:
            f.write(new_section)
    else:
        # Create new LTM
        with open(ltm_path, 'w') as f:
            f.write(f"""# OpenCode Long-Term Memory
_Auto-consolidated from daily session notes by the dreaming system._

*Last updated: {now}*
{new_section}""")
    
    print(f"Dreaming complete: {len(new_findings)} new findings consolidated from {len(notes)} notes")
else:
    print("No new findings to consolidate")

PYEOF

if [ $? -eq 0 ]; then
    log "Dreaming completed successfully"
else
    log "WARN: Dreaming failed"
fi

log "=== Dreaming complete ==="
#!/bin/bash
# oc-context - OpenCode Shared Context CLI
# Quick inspection and management of the shared context store
#
# Usage:
#   oc-context                    Show full context
#   oc-context findings [agent]   Show findings (optionally filtered by agent)
#   oc-context decisions          Show decisions
#   oc-context artifacts          Show artifacts
#   oc-context workflow           Show workflow trace
#   oc-context session            Show current session info
#   oc-context summary            Show a human-readable summary
#   oc-context clear              Reset context to empty state (with confirmation)

CONTEXT_FILE="$HOME/.config/opencode/shared/context.json"

if [ ! -f "$CONTEXT_FILE" ]; then
  echo "Error: Context file not found at $CONTEXT_FILE"
  echo "Run 'opencode' to initialize the context store."
  exit 1
fi

show_full() {
  python3 -c "
import json, sys
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
print(json.dumps(ctx, indent=2))
"
}

show_findings() {
  local agent="$1"
  if [ -n "$agent" ]; then
    python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
findings = ctx['findings'].get('$agent', [])
if findings:
    print(f'=== Findings for agent: $agent ===')
    print(json.dumps(findings, indent=2))
else:
    print(f'No findings for agent: $agent')
"
  else
    python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
for agent, findings in ctx['findings'].items():
    if findings:
        print(f'--- {agent} ({len(findings)} findings) ---')
        for f in findings[-3:]:  # Show last 3
            print(f\"  [{f.get('severity','info').upper():8}] {f.get('summary','')[:80]}\")
        print()
"
  fi
}

show_decisions() {
  python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
for category, decisions in ctx['decisions'].items():
    if decisions:
        print(f'=== {category} ===')
        for d in decisions:
            print(f\"  {d.get('summary','')[:100]}\")
        print()
"
}

show_artifacts() {
  python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
for category, items in ctx['artifacts'].items():
    if items:
        print(f'=== {category} ({len(items)} items) ===')
        for item in items[-5:]:  # Show last 5
            print(f\"  {item[:100]}\")
        print()
"
}

show_workflow() {
  python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
trace = ctx.get('workflow_trace', [])
if trace:
    print(f'Workflow Trace ({len(trace)} steps):')
    for i, step in enumerate(trace, 1):
        agent = step.get('agent', 'unknown')
        status = step.get('status', 'unknown')
        summary = step.get('summary', '')[:80]
        print(f'  {i}. [{status:10}] {agent}: {summary}')
else:
    print('No workflow trace found.')
print()
session = ctx.get('session', {})
print(f'Session: {session.get(\"current_id\", \"none\")}')
print(f'Pattern: {session.get(\"workflow_pattern\", \"none\")}')
print(f'Active Agents: {session.get(\"active_agents\", [])}')
"
}

show_session() {
  python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)
session = ctx.get('session', {})
state = ctx.get('state', {})
print('=== Session Info ===')
print(f'  ID:        {session.get(\"current_id\", \"none\")}')
print(f'  Title:     {session.get(\"current_title\", \"none\")}')
print(f'  Pattern:   {session.get(\"workflow_pattern\", \"none\")}')
print(f'  Started:   {session.get(\"started_at\", \"none\")}')
print(f'  Agents:    {session.get(\"active_agents\", [])}')
print()
print('=== State ===')
print(f'  Findings:  {state.get(\"findings_count\", 0)}')
print(f'  Decisions: {state.get(\"decisions_count\", 0)}')
print(f'  Artifacts: {state.get(\"artifacts_count\", 0)}')
print(f'  Updated:   {state.get(\"last_updated_at\", \"none\")} by {state.get(\"last_updated_by\", \"none\")}')
"
}

show_summary() {
  python3 -c "
import json
with open('$CONTEXT_FILE') as f:
    ctx = json.load(f)

session = ctx.get('session', {})
state = ctx.get('state', {})
findings = ctx.get('findings', {})
artifacts = ctx.get('artifacts', {})

print('╔══════════════════════════════════════════╗')
print('║     OpenCode Shared Context Summary      ║')
print('╚══════════════════════════════════════════╝')
print()

# Session
if session.get('current_id'):
    print(f'Session: {session[\"current_id\"]}')
    if session.get('current_title'):
        print(f'Title:   {session[\"current_title\"]}')
    if session.get('workflow_pattern'):
        print(f'Pattern: {session[\"workflow_pattern\"]}')
    print()

# Findings summary
finding_counts = {agent: len(fs) for agent, fs in findings.items() if fs}
if finding_counts:
    print('Findings by agent:')
    for agent, count in sorted(finding_counts.items()):
        sevs = {}
        for f in findings[agent]:
            sevs[f.get('severity','info')] = sevs.get(f.get('severity','info'), 0) + 1
        sev_str = ', '.join(f'{k}={v}' for k,v in sorted(sevs.items()))
        print(f'  {agent:20} {count:3} total  [{sev_str}]')
    print()

# Artifacts summary
artifact_counts = {k: len(v) for k, v in artifacts.items() if v}
if artifact_counts:
    print('Artifacts:')
    for k, v in sorted(artifact_counts.items()):
        print(f'  {k:25} {v}')
    print()

# Workflow trace
trace = ctx.get('workflow_trace', [])
if trace:
    print(f'Workflow steps: {len(trace)}')
    for step in trace:
        agent = step.get('agent', '?')
        status = step.get('status', '?')
        print(f'  [{status:10}] {agent}')
    print()

# Cross-references
xrefs = ctx.get('cross_references', [])
if xrefs:
    print(f'Cross-references: {len(xrefs)}')
    print()
"
}

reset_context() {
  echo "WARNING: This will clear ALL shared context data."
  echo "This cannot be undone. Are you sure? [y/N]"
  read -r response
  if [[ "$response" =~ ^[Yy]$ ]]; then
    python3 -c "
import json, os
ctx = {
    'meta': {
        'version': '2.0.0',
        'created': '$(date -I)',
        'updated': '$(date -Iseconds)',
        'description': 'Structured shared context store for cross-agent memory and workflow continuity'
    },
    'session': {
        'current_id': None,
        'current_title': None,
        'active_agents': [],
        'workflow_pattern': None,
        'started_at': None
    },
    'state': {
        'findings_count': 0,
        'decisions_count': 0,
        'artifacts_count': 0,
        'last_updated_by': None,
        'last_updated_at': None
    },
    'findings': {
        'debug': [], 'security': [], 'architect': [], 'build': [],
        'plan': [], 'review': [], 'test': [], 'general': [],
        'refactor': [], 'docs': [], 'explore': [], 'video-creator': [],
        'web-browser': [], 'display-agent': []
    },
    'decisions': {
        'architecture': [], 'design': [], 'technology': [], 'workflow': []
    },
    'artifacts': {
        'files_created': [], 'files_modified': [], 'files_deleted': [],
        'tests_written': [], 'documentation_updated': []
    },
    'cross_references': [],
    'workflow_trace': []
}
with open(os.path.expanduser('$CONTEXT_FILE'), 'w') as f:
    json.dump(ctx, f, indent=2)
print('Context cleared successfully.')
"
  else
    echo "Cancelled."
  fi
}

case "${1:-full}" in
  full)
    show_full
    ;;
  findings)
    show_findings "$2"
    ;;
  decisions)
    show_decisions
    ;;
  artifacts)
    show_artifacts
    ;;
  workflow)
    show_workflow
    ;;
  session)
    show_session
    ;;
  summary)
    show_summary
    ;;
  clear)
    reset_context
    ;;
  *)
    echo "Usage: oc-context {full|findings [agent]|decisions|artifacts|workflow|session|summary|clear}"
    exit 1
    ;;
esac

#!/bin/bash
# Checkpoint helper for subagents — easy to find and use
# Usage: ./checkpoint-helper.sh save <agent> <run_id> <stage> <status>
#        ./checkpoint-helper.sh list <agent>
#        ./checkpoint-helper.sh resume <agent> <run_id>
set -e
AGENT=${2:-fixer}
RUN_ID=${3:-run_$(date +%Y%m%d)_$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')}
STAGE=${4:-parse_context}
STATUS=${5:-completed}
case "$1" in
  save) python3 -m opencode_improvement checkpoint save --agent "$AGENT" --run "$RUN_ID" --stage "$STAGE" --status "$STATUS" ;;
  list) python3 -m opencode_improvement checkpoint list --agent "$AGENT" ;;
  resume) python3 -m opencode_improvement checkpoint resume --agent "$AGENT" --run "$RUN_ID" ;;
  *) echo "Usage: $0 {save|list|resume} [agent] [run_id] [stage] [status]"; echo "Checkpoints dir: ~/.config/opencode/shared/checkpoints/"; ls -la ~/.config/opencode/shared/checkpoints/$AGENT/ 2>&1 | head -20 ;;
esac

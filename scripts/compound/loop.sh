#!/bin/bash
LIMIT="${1:-25}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
cd "$PROJECT_ROOT"
PRD_JSON="${SCRIPT_DIR}/prd.json"
[ ! -f "$PRD_JSON" ] && exit 0
[ -z "$AGENT_CMD" ] && echo "Set AGENT_CMD for execution loop." && exit 0
i=0
while [ "$i" -lt "$LIMIT" ]; do
  $AGENT_CMD "Load the tasks from $PRD_JSON. Execute the next incomplete task. Update prd.json and the codebase. If all tasks are done, say DONE and exit."
  i=$((i + 1))
done

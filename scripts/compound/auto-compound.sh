#!/bin/bash
# auto-compound.sh — report → PRD → tasks → loop → PR
set -e
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
cd "$PROJECT_ROOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f .env.local ] && source .env.local
git fetch origin main 2>/dev/null || true
git reset --hard origin/main 2>/dev/null || true
mkdir -p reports
LATEST_REPORT=$(ls -t reports/*.md 2>/dev/null | head -1)
if [ -z "$LATEST_REPORT" ]; then
  echo "No reports/*.md found."
  exit 1
fi
ANALYSIS=$("$SCRIPT_DIR/analyze-report.sh" "$LATEST_REPORT")
PRIORITY_ITEM=$(echo "$ANALYSIS" | jq -r '.priority_item')
BRANCH_NAME=$(echo "$ANALYSIS" | jq -r '.branch_name')
git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME" 2>/dev/null || true
mkdir -p tasks
if [ -z "$AGENT_CMD" ]; then
  echo "# PRD: $PRIORITY_ITEM" > "tasks/prd-$(basename "$BRANCH_NAME").md"
  echo '{"tasks":[]}' > "$SCRIPT_DIR/prd.json"
else
  $AGENT_CMD "Load the prd skill. Create a PRD for: $PRIORITY_ITEM. Save to tasks/prd-$(basename $BRANCH_NAME).md"
  $AGENT_CMD "Load the tasks skill. Convert the PRD to $SCRIPT_DIR/prd.json"
fi
"$SCRIPT_DIR/loop.sh" "${LOOP_LIMIT:-25}"
git push -u origin "$BRANCH_NAME" 2>/dev/null || true
command -v gh >/dev/null 2>&1 && gh pr create --draft --title "Compound: $PRIORITY_ITEM" --base main || true

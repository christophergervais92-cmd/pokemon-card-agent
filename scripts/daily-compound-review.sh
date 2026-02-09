#!/bin/bash
# daily-compound-review.sh — compound nightly loop
set -e
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
cd "$PROJECT_ROOT"
# Load ANTHROPIC_API_KEY (and optional AGENT_CMD) from local env — not from plist
[ -f .env ] && set -a && source .env && set +a
[ -f .env.local ] && set -a && source .env.local && set +a
mkdir -p logs

if [ -n "$AGENT_CMD" ]; then
  $AGENT_CMD "Load the compound-engineering skill. Look through and read each thread from the last 24 hours. For any thread where we did NOT use the Compound Engineering skill to compound our learnings at the end, do so now - extract the key learnings from that thread and update the relevant RULE.md or .cursor/rules so we learn from our work and mistakes. Commit your changes and push to main."
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "$SCRIPT_DIR/compound_review.py" ]; then
    git checkout main 2>/dev/null || true
    git pull origin main 2>/dev/null || true
    python3 "$SCRIPT_DIR/compound_review.py" "$PROJECT_ROOT" || true
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      git add RULE.md .cursor/rules 2>/dev/null || true
      git add -u
      git commit -m "chore: compound learnings from daily review" || true
      git push origin main 2>/dev/null || true
    fi
  else
    echo "Set AGENT_CMD or add scripts/compound_review.py and ANTHROPIC_API_KEY."
    exit 1
  fi
fi

#!/bin/bash
REPORT="$1"
[ -z "$REPORT" ] && REPORT="$(ls -t reports/*.md 2>/dev/null | head -1)"
[ ! -f "$REPORT" ] && echo '{"priority_item":"","branch_name":"compound-fallback"}' && exit 0
PRIORITY=$(sed -n 's/^## \s*//p; s/^-\s*//p; s/^\*\s*//p' "$REPORT" | head -1)
[ -z "$PRIORITY" ] && PRIORITY=$(head -1 "$REPORT")
BRANCH_NAME=$(echo "$PRIORITY" | sed 's/[^a-zA-Z0-9]/-/g' | tr '[:upper:]' '[:lower:]' | cut -c1-50)
BRANCH_NAME="compound/${BRANCH_NAME}"
echo "{\"priority_item\":\"$(echo "$PRIORITY" | sed 's/"/\\"/g')\",\"branch_name\":\"$BRANCH_NAME\"}"

#!/usr/bin/env bash
# Opens one GitHub issue per line of $ISSUES_FILE ("title<TAB>body"), skipping titles already open.
set -euo pipefail
[ -s "${ISSUES_FILE:-}" ] || exit 0
gh label create linkedin --color 0A66C2 --force >/dev/null 2>&1 || true
while IFS=$'\t' read -r title body; do
  if gh issue list --state open --label linkedin --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "already open: $title"
  else
    gh issue create --title "$title" --body "$body" --label linkedin
  fi
done < "$ISSUES_FILE"

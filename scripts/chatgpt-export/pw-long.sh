#!/bin/bash
# Обёртка для длинных playwriter-вызовов (без 5-минутного лимита CLI).
# Использование:
#   scripts/chatgpt-export/pw-long.sh <session> <script.js> [timeout_ms=3600000]
#   scripts/chatgpt-export/pw-long.sh 4 scripts/chatgpt-export/extract-project-chat.js
set -euo pipefail
SESSION="${1:?session id}"
SCRIPT="${2:?script path}"
TIMEOUT_MS="${3:-3600000}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
NODE_OPTIONS="--require $REPO_ROOT/scripts/chatgpt-export/playwriter-long-fetch.cjs" \
  exec playwriter -s "$SESSION" -f "$SCRIPT" --timeout "$TIMEOUT_MS"

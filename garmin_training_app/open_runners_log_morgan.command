#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8002}"
URL="${1:-http://127.0.0.1:${PORT}/}"

if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  (
    cd "$APP_DIR"
    PORT="$PORT" python server.py > /tmp/runners_log_server.log 2>&1 &
  )
  sleep 2
fi

open -a "Google Chrome" --args --profile-directory="Profile 1" "$URL"

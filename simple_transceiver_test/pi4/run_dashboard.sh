#!/usr/bin/env bash
set -u

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/.local/state/devbot"
LOG_FILE="$LOG_DIR/dashboard.log"

mkdir -p "$LOG_DIR"

if ! python3 -B "$APP_DIR/dashboard.py" >>"$LOG_FILE" 2>&1; then
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "DevBot Receiver" "Dashboard failed. See $LOG_FILE"
    fi
    exit 1
fi

#!/bin/bash

LOG="$HOME/.local/share/opencode/log/opencode.log"
INTERVAL=30
IDLE_LIMIT=300

echo "OpenCode Watchdog started: $$"

while true; do
    if [ -f "$LOG" ]; then
        recent="$(tail -300 "$LOG")"

        sessions="$(printf '%s\n' "$recent" | sed -n 's/.*session.id=\([^ ]*\).*/\1/p' | sort -u)"

        for session in $sessions; do
            activity="$(printf '%s\n' "$recent" | grep "session.id=$session" | tail -1)"

            if printf '%s\n' "$activity" | grep -Eq 'stream error|Service Unavailable|socket connection|No payment method'; then
                osascript -e "display notification \"API error in session ${session:0:16}. Check OpenCode.\" with title \"OpenCode Watchdog\" sound name \"Basso\""
                echo "$(date): API error in $session"
            fi
        done
    fi

    sleep "$INTERVAL"
done

#!/bin/bash
# Watchdog: restarts main.py load if it crashes
# Usage: nohup bash watchdog.sh > exports/watchdog.log 2>&1 &

cd /Users/kirill/BAZATG
source venv/bin/activate

LOG="exports/full_load.log"
ATTEMPT=0

echo "[$(date)] Watchdog started"

while true; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "[$(date)] Attempt #$ATTEMPT: starting python -u main.py load"

    python -u main.py load >> "$LOG" 2>&1
    EXIT_CODE=$?

    echo "[$(date)] Process exited with code $EXIT_CODE"

    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] Load completed successfully. Watchdog exiting."
        break
    fi

    echo "[$(date)] Crash detected. Waiting 30s before restart..."
    sleep 30
done

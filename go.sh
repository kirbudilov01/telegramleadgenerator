#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
THREADS_DIR="$ROOT_DIR/threads_autopilot"
X_DIR="${X_AGENT_DIR:-$ROOT_DIR/../X-ACTIONS-AGENT}"
SESSION="${DUAL_SESSION_NAME:-dual_agents}"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"

usage() {
  echo "Usage: $0 {doctor|init|login|start|attach|stop|restart|status}" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

check_threads_token() {
  if [ ! -f "$THREADS_DIR/config.json" ]; then
    echo "WARN: $THREADS_DIR/config.json missing (copy from config.example.json)"
    return
  fi

  local has_token
  has_token=$(python3 - <<'PY' "$THREADS_DIR/config.json"
import json, sys
p = sys.argv[1]
cfg = json.load(open(p, 'r', encoding='utf-8'))
val = str(cfg.get('github_token', '')).strip()
print('yes' if val and 'ВСТАВЬ_' not in val else 'no')
PY
)

  if [ "$has_token" = "yes" ]; then
    echo "OK: Threads github_token configured"
  else
    echo "WARN: Threads github_token missing in $THREADS_DIR/config.json"
  fi
}

check_x_config() {
  if [ ! -d "$X_DIR" ]; then
    echo "WARN: X repo not found at $X_DIR"
    return
  fi
  if [ -f "$X_DIR/data/session.json" ]; then
    echo "OK: X session exists"
  else
    echo "WARN: X session missing ($X_DIR/data/session.json)"
  fi
  if [ -d "$X_DIR/node_modules" ]; then
    echo "OK: X dependencies installed"
  else
    echo "WARN: X dependencies missing (run: $0 init)"
  fi
}

cmd="${1:-doctor}"

case "$cmd" in
  doctor)
    require_cmd python3
    require_cmd node
    require_cmd npm
    require_cmd tmux
    echo "OK: required commands found"

    if [ -d "$ROOT_DIR/venv" ]; then
      echo "OK: Python venv exists"
    else
      echo "WARN: Python venv missing (run: $0 init)"
    fi

    if [ -f "$THREADS_DIR/threads_storage_state.json" ] || [ -d "$THREADS_DIR/chrome_profile" ]; then
      echo "OK: Threads login artifacts exist"
    else
      echo "WARN: Threads login not initialized (run: $0 login)"
    fi

    check_threads_token
    check_x_config
    ;;

  init)
    require_cmd python3
    require_cmd npm

    if [ ! -d "$ROOT_DIR/venv" ]; then
      python3 -m venv "$ROOT_DIR/venv"
    fi

    source "$ROOT_DIR/venv/bin/activate"
    "$ROOT_DIR/venv/bin/python" -m pip install -q -r "$THREADS_DIR/requirements.txt"
    "$ROOT_DIR/venv/bin/python" -m playwright install chromium

    if [ ! -f "$THREADS_DIR/config.json" ]; then
      cp "$THREADS_DIR/config.example.json" "$THREADS_DIR/config.json"
      echo "Created $THREADS_DIR/config.json"
    fi

    if [ ! -d "$X_DIR" ]; then
      git clone https://github.com/nirholas/XActions.git "$X_DIR"
    fi

    (cd "$X_DIR" && npm install)
    echo "Init complete. Run: $0 login"
    ;;

  login)
    if [ ! -x "$PYTHON_BIN" ]; then
      echo "Python venv not ready. Run: $0 init" >&2
      exit 1
    fi

    (cd "$THREADS_DIR" && "$PYTHON_BIN" autopilot.py --setup-login)

    if [ -d "$X_DIR" ]; then
      (cd "$X_DIR" && npm run agent:login)
    else
      echo "WARN: X repo not found at $X_DIR"
    fi
    ;;

  start)
    require_cmd tmux
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "Session already running: $SESSION"
      tmux attach -t "$SESSION"
      exit 0
    fi

    tmux new-session -d -s "$SESSION" -x 240 -y 60 -c "$THREADS_DIR"
    tmux setw -t "$SESSION":0 remain-on-exit on

    tmux send-keys -t "$SESSION":0.0 "cd '$THREADS_DIR' && ../venv/bin/python autopilot.py --profile safe --verbose 2>&1 | tee -a autopilot.log" C-m

    tmux split-window -h -t "$SESSION":0 -c "$X_DIR"
    tmux send-keys -t "$SESSION":0.1 "cd '$X_DIR' && mkdir -p logs && npm run agent 2>&1 | tee -a logs/agent.log" C-m

    tmux select-layout -t "$SESSION":0 even-horizontal
    echo "Started tmux session: $SESSION"
    tmux attach -t "$SESSION"
    ;;

  attach)
    require_cmd tmux
    tmux attach -t "$SESSION"
    ;;

  stop)
    require_cmd tmux
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    echo "Stopped session: $SESSION"
    ;;

  restart)
    "$0" stop
    "$0" start
    ;;

  status)
    require_cmd tmux
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "Session is running: $SESSION"
      tmux list-panes -t "$SESSION":0 -F "pane #{pane_index}: #{pane_current_command} | dead=#{pane_dead}"
    else
      echo "Session is not running: $SESSION"
    fi
    ;;

  *)
    usage
    exit 1
    ;;
esac

#!/bin/bash
# backend/run.sh — Manage the FastAPI backend
# Commands:
#   setup   — create venv + pip install dependencies
#   train   — download data (if needed) + train ALS model
#   start   — start uvicorn in the background
#   stop    — stop uvicorn
#   status  — show running status + health
#   restart — stop then start

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/backend.log"
PID_FILE="$LOG_DIR/backend.pid"
VENV="$SCRIPT_DIR/venv"
PORT="${BACKEND_PORT:-8003}"

mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[backend]${NC} $*"; }
warn()  { echo -e "${YELLOW}[backend]${NC} $*"; }
error() { echo -e "${RED}[backend]${NC} $*" >&2; }
section() { echo -e "\n${CYAN}══ backend ▸ $* ══${NC}"; }

# ── Resolve Java 17 for PySpark 3.5 ───────────────────────────────────────
_resolve_java() {
  local JAVA17="/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"
  local JAVA21="/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
  for jpath in "$JAVA17" "$JAVA21"; do
    if [ -d "$jpath" ]; then
      export JAVA_HOME="$jpath"
      info "JAVA_HOME → $jpath"
      return 0
    fi
  done
  warn "Java 17+ not found. PySpark may fail. Install: brew install openjdk@17"
}

# ── Python / uvicorn helpers ───────────────────────────────────────────────
_python()  { [ -f "$VENV/bin/python3"  ] && echo "$VENV/bin/python3"  || echo "python3"; }
_uvicorn() { [ -f "$VENV/bin/uvicorn"  ] && echo "$VENV/bin/uvicorn"  || echo "uvicorn"; }
_pip()     { [ -f "$VENV/bin/pip"      ] && echo "$VENV/bin/pip"      || echo "pip3";    }

# ── setup ──────────────────────────────────────────────────────────────────
cmd_setup() {
  section setup
  if [ ! -d "$VENV" ]; then
    info "Creating virtual environment at $VENV ..."
    python3 -m venv "$VENV"
  else
    info "Virtual environment already exists."
  fi
  info "Installing / updating Python dependencies..."
  "$(_pip)" install --quiet --upgrade pip
  "$(_pip)" install --quiet -r "$SCRIPT_DIR/requirements.txt"
  info "Setup complete."
}

# ── train ──────────────────────────────────────────────────────────────────
cmd_train() {
  section train
  RATINGS="$ROOT_DIR/data/ml-latest-small/ratings.csv"
  if [ ! -f "$RATINGS" ]; then
    warn "MovieLens data not found. Running data/setup.sh first..."
    bash "$ROOT_DIR/data/setup.sh" || { error "Data download failed."; exit 1; }
  fi
  _resolve_java
  info "Training ALS model (this may take 1–3 minutes)..."
  cd "$SCRIPT_DIR"
  "$(_python)" train_and_save.py
  info "Training complete — model saved to: $ROOT_DIR/models/als_model"
}

# ── start ──────────────────────────────────────────────────────────────────
cmd_start() {
  section start
  # Guard: port already in use?
  EXISTING=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  if [ -n "$EXISTING" ]; then
    if [ -f "$PID_FILE" ] && [ "$(cat "$PID_FILE")" = "$EXISTING" ]; then
      warn "Backend already running (PID $EXISTING). Use 'restart' to restart."
    else
      warn "Port $PORT is in use by PID $EXISTING (stale). Run 'stop' first."
    fi
    return 0
  fi
  if [ ! -d "$ROOT_DIR/models/als_model" ]; then
    warn "ALS model not found — recommendations will return errors."
    warn "  Run: bash run.sh train"
  fi
  _resolve_java
  UVICORN="$(_uvicorn)"
  info "uvicorn: $UVICORN"
  info "Launching on port $PORT ..."
  cd "$SCRIPT_DIR"
  nohup "$UVICORN" app.main:app --host 0.0.0.0 --port "$PORT" > "$LOG_FILE" 2>&1 &
  BPID=$!
  echo "$BPID" > "$PID_FILE"
  info "Backend PID $BPID — logs: $LOG_FILE"
  # Wait up to 15 s for the health endpoint
  info "Waiting for server to be ready..."
  for i in $(seq 1 15); do
    sleep 1
    HSTATUS=$(curl -s "http://localhost:$PORT/api/v1/health" 2>/dev/null | \
      python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || true)
    if [ -n "$HSTATUS" ]; then
      info "Ready after ${i}s — health: $HSTATUS"
      return 0
    fi
  done
  warn "No health response after 15s. Check logs: $LOG_FILE"
}

# ── stop ───────────────────────────────────────────────────────────────────
cmd_stop() {
  section stop
  # Kill by saved PID if available
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
      /bin/kill -TERM "$PID" && info "Stopped PID $PID."
    else
      info "Saved PID $PID is not running."
    fi
    rm -f "$PID_FILE"
  else
    info "No PID file found."
  fi
  # Also clear any stale process still holding the port
  STALE=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
  if [ -n "$STALE" ]; then
    warn "Port $PORT still held by PID(s) $STALE — force-stopping..."
    echo "$STALE" | xargs /bin/kill -TERM 2>/dev/null || true
    sleep 1
    # SIGKILL if still alive
    STALE2=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
    [ -n "$STALE2" ] && echo "$STALE2" | xargs /bin/kill -9 2>/dev/null || true
    info "Port $PORT cleared."
  fi
}

# ── status ─────────────────────────────────────────────────────────────────
cmd_status() {
  section status
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
      info "Running — PID $PID  port $PORT"
      HINFO=$(curl -s "http://localhost:$PORT/api/v1/health" 2>/dev/null | \
        python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"status={d['status']}  model_loaded={d['model_loaded']}  spark_active={d['spark_active']}\")
" 2>/dev/null || echo "(no response)")
      info "Health: $HINFO"
      return 0
    fi
  fi
  warn "Backend is not running."
}

# ── restart ────────────────────────────────────────────────────────────────
cmd_restart() { cmd_stop; sleep 1; cmd_start; }

# ── dispatch ───────────────────────────────────────────────────────────────
case "${1:-start}" in
  setup)   cmd_setup   ;;
  train)   cmd_train   ;;
  start)   cmd_start   ;;
  stop)    cmd_stop    ;;
  status)  cmd_status  ;;
  restart) cmd_restart ;;
  *)
    echo "Usage: bash backend/run.sh [setup|train|start|stop|status|restart]"
    exit 1 ;;
esac

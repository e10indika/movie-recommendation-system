#!/bin/bash
# frontend/run.sh — Manage the React/Vite frontend
# Commands:
#   setup   — npm install
#   build   — production build (dist/)
#   start   — start Vite dev server in background
#   stop    — stop Vite dev server
#   status  — show running status
#   restart — stop then start

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/frontend.log"
PID_FILE="$LOG_DIR/frontend.pid"
PORT="${FRONTEND_PORT:-5174}"

mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[frontend]${NC} $*"; }
warn()  { echo -e "${YELLOW}[frontend]${NC} $*"; }
error() { echo -e "${RED}[frontend]${NC} $*" >&2; }
section() { echo -e "\n${CYAN}══ frontend ▸ $* ══${NC}"; }

# ── setup ──────────────────────────────────────────────────────────────────
cmd_setup() {
  section setup
  if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    info "Installing npm dependencies..."
    cd "$SCRIPT_DIR" && npm install
  else
    info "node_modules already present. Skipping install."
  fi
  info "Setup complete."
}

# ── build ──────────────────────────────────────────────────────────────────
cmd_build() {
  section build
  info "Running production build..."
  cd "$SCRIPT_DIR" && npm run build
  info "Build output at: $SCRIPT_DIR/dist"
}

# ── start ──────────────────────────────────────────────────────────────────
cmd_start() {
  section start
  if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
      warn "Frontend already running (PID $OLD_PID). Use 'restart' to restart."
      return 0
    fi
  fi
  if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    info "node_modules missing — running setup first..."
    cmd_setup
  fi
  info "Starting Vite dev server on port $PORT ..."
  cd "$SCRIPT_DIR"
  nohup npm run dev > "$LOG_FILE" 2>&1 &
  FPID=$!
  echo "$FPID" > "$PID_FILE"
  info "Frontend PID $FPID — logs: $LOG_FILE"
  # Wait up to 10 s for server to bind
  for i in $(seq 1 10); do
    sleep 1
    if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
      info "Ready after ${i}s — http://localhost:$PORT"
      return 0
    fi
  done
  warn "No response after 10s. Check logs: $LOG_FILE"
}

# ── stop ───────────────────────────────────────────────────────────────────
cmd_stop() {
  section stop
  if [ ! -f "$PID_FILE" ]; then
    info "No PID file found — frontend may not be running."
    return 0
  fi
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" > /dev/null 2>&1; then
    /bin/kill -TERM "$PID" && info "Stopped PID $PID."
  else
    info "Process $PID is not running."
  fi
  rm -f "$PID_FILE"
}

# ── status ─────────────────────────────────────────────────────────────────
cmd_status() {
  section status
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
      info "Running — PID $PID  port $PORT"
      if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
        info "HTTP check: responding at http://localhost:$PORT"
      else
        warn "HTTP check: no response (still starting?)"
      fi
      return 0
    fi
  fi
  warn "Frontend is not running."
}

# ── restart ────────────────────────────────────────────────────────────────
cmd_restart() { cmd_stop; sleep 1; cmd_start; }

# ── dispatch ───────────────────────────────────────────────────────────────
case "${1:-start}" in
  setup)   cmd_setup   ;;
  build)   cmd_build   ;;
  start)   cmd_start   ;;
  stop)    cmd_stop    ;;
  status)  cmd_status  ;;
  restart) cmd_restart ;;
  *)
    echo "Usage: bash frontend/run.sh [setup|build|start|stop|status|restart]"
    exit 1 ;;
esac

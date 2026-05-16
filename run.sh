#!/bin/bash
# run.sh — Master orchestrator for Movie Recommendation System
#
# Commands:
#   start           start backend + frontend
#   stop            stop both services
#   restart         stop then start both services
#   status          health check all services
#   setup           install all dependencies (venv + npm)
#   train           download MovieLens data + train ALS model
#   logs            tail live logs (both)
#   logs backend    tail backend log only
#   logs frontend   tail frontend log only
#
# First-time flow:
#   bash run.sh setup
#   bash run.sh train
#   bash run.sh start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_SCRIPT="$SCRIPT_DIR/backend/run.sh"
FRONTEND_SCRIPT="$SCRIPT_DIR/frontend/run.sh"
DATA_SCRIPT="$SCRIPT_DIR/data/setup.sh"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${GREEN}[run]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[run]${NC}  $*"; }
error()   { echo -e "${RED}[run]${NC}  $*" >&2; }
banner()  {
  echo -e "\n${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${GREEN}║  Movie Recommendation System — $*${NC}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}\n"
}

_require() { [ -f "$1" ] || { error "Script not found: $1"; exit 1; }; }

# ── setup — install all dependencies ──────────────────────────────────────
cmd_setup() {
  banner "setup"
  _require "$BACKEND_SCRIPT"
  _require "$FRONTEND_SCRIPT"
  bash "$BACKEND_SCRIPT"  setup
  bash "$FRONTEND_SCRIPT" setup
  echo ""
  info "All dependencies installed."
  info "Next: bash run.sh train"
}

# ── train — download data + train model ───────────────────────────────────
cmd_train() {
  banner "train"
  _require "$DATA_SCRIPT"
  _require "$BACKEND_SCRIPT"
  bash "$DATA_SCRIPT"
  bash "$BACKEND_SCRIPT" train
  echo ""
  info "Model ready. Next: bash run.sh start"
}

# ── start — start backend then frontend ───────────────────────────────────
cmd_start() {
  banner "start"
  _require "$BACKEND_SCRIPT"
  _require "$FRONTEND_SCRIPT"
  bash "$BACKEND_SCRIPT"  start
  bash "$FRONTEND_SCRIPT" start
  echo ""
  echo -e "${BOLD}Services running:${NC}"
  echo "  Backend  API : http://localhost:${BACKEND_PORT:-8003}"
  echo "  API Docs     : http://localhost:${BACKEND_PORT:-8003}/docs"
  echo "  Frontend     : http://localhost:${FRONTEND_PORT:-5174}"
  echo ""
  echo -e "${BOLD}Other commands:${NC}"
  echo "  bash run.sh status    — health check"
  echo "  bash run.sh logs      — tail all logs"
  echo "  bash run.sh stop      — shut down"
}

# ── stop — stop both services ──────────────────────────────────────────────
cmd_stop() {
  banner "stop"
  _require "$BACKEND_SCRIPT"
  _require "$FRONTEND_SCRIPT"
  bash "$BACKEND_SCRIPT"  stop
  bash "$FRONTEND_SCRIPT" stop
  info "All services stopped."
}

# ── restart ────────────────────────────────────────────────────────────────
cmd_restart() {
  banner "restart"
  bash "$BACKEND_SCRIPT"  stop
  bash "$FRONTEND_SCRIPT" stop
  sleep 1
  bash "$BACKEND_SCRIPT"  start
  bash "$FRONTEND_SCRIPT" start
}

# ── status ─────────────────────────────────────────────────────────────────
cmd_status() {
  banner "status"
  bash "$BACKEND_SCRIPT"  status
  bash "$FRONTEND_SCRIPT" status
  echo ""
  MODEL_PATH="$SCRIPT_DIR/models/als_model"
  DATA_PATH="$SCRIPT_DIR/data/ml-latest-small/ratings.csv"
  [ -d "$MODEL_PATH" ] && info "ALS model     : PRESENT" || warn "ALS model     : MISSING  — run: bash run.sh train"
  [ -f "$DATA_PATH"  ] && info "MovieLens data: PRESENT" || warn "MovieLens data: MISSING  — run: bash run.sh train"
}

# ── logs — tail log files ──────────────────────────────────────────────────
cmd_logs() {
  local TARGET="${2:-all}"
  local BACKEND_LOG="$LOG_DIR/backend.log"
  local FRONTEND_LOG="$LOG_DIR/frontend.log"
  case "$TARGET" in
    backend)
      [ -f "$BACKEND_LOG"  ] || { warn "No backend log yet."; exit 0; }
      tail -f "$BACKEND_LOG"
      ;;
    frontend)
      [ -f "$FRONTEND_LOG" ] || { warn "No frontend log yet."; exit 0; }
      tail -f "$FRONTEND_LOG"
      ;;
    *)
      declare -a LOGS=()
      [ -f "$BACKEND_LOG"  ] && LOGS+=("$BACKEND_LOG")
      [ -f "$FRONTEND_LOG" ] && LOGS+=("$FRONTEND_LOG")
      [ ${#LOGS[@]} -eq 0 ] && { warn "No log files yet. Start services first."; exit 0; }
      info "Tailing logs (Ctrl+C to stop)..."
      tail -f "${LOGS[@]}"
      ;;
  esac
}

# ── usage ───────────────────────────────────────────────────────────────────
cmd_usage() {
  echo ""
  echo -e "${BOLD}Usage: bash run.sh <command>${NC}"
  echo ""
  echo "  setup           Install Python venv + npm dependencies"
  echo "  train           Download MovieLens data + train ALS model"
  echo "  start           Start backend + frontend"
  echo "  stop            Stop both services"
  echo "  restart         Restart both services"
  echo "  status          Health check all services"
  echo "  logs            Tail all logs"
  echo "  logs backend    Tail backend log"
  echo "  logs frontend   Tail frontend log"
  echo ""
  echo "First-time setup:"
  echo "  bash run.sh setup && bash run.sh train && bash run.sh start"
  echo ""
}

# ── dispatch ───────────────────────────────────────────────────────────────
CMD="${1:-}"
case "$CMD" in
  setup)          cmd_setup          ;;
  train)          cmd_train          ;;
  start)          cmd_start          ;;
  stop)           cmd_stop           ;;
  restart)        cmd_restart        ;;
  status)         cmd_status         ;;
  logs)           cmd_logs "$@"      ;;
  help|--help|-h) cmd_usage          ;;
  "")  warn "No command given."; cmd_usage; exit 1 ;;
  *)   error "Unknown command: $CMD"; cmd_usage; exit 1 ;;
esac

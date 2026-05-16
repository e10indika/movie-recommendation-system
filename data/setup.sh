#!/bin/bash
# data/setup.sh — Download and verify MovieLens dataset
# Usage:
#   bash data/setup.sh          check + download if missing
#   bash data/setup.sh --force  re-download even if data exists

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/ml-latest-small"
RATINGS="$DATA_DIR/ratings.csv"
MOVIES="$DATA_DIR/movies.csv"
ZIP_URL="https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
ZIP_PATH="$SCRIPT_DIR/ml-latest-small.zip"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[data]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[data]${NC}  $*"; }
error()   { echo -e "${RED}[data]${NC}  $*" >&2; }

# ── Already present? ──────────────────────────────────────────────────────
if [[ "$1" != "--force" ]] && [[ -f "$RATINGS" && -f "$MOVIES" ]]; then
  RATING_LINES=$(wc -l < "$RATINGS")
  info "MovieLens data already present at: $DATA_DIR"
  info "  ratings.csv  — $((RATING_LINES - 1)) rows"
  info "  movies.csv   — $(( $(wc -l < "$MOVIES") - 1 )) rows"
  exit 0
fi

# ── Download ──────────────────────────────────────────────────────────────
info "Downloading MovieLens Small dataset (~3 MB)…"
if ! curl -L --progress-bar -o "$ZIP_PATH" "$ZIP_URL"; then
  error "Download failed. Check internet connection."
  exit 1
fi

info "Extracting…"
unzip -o "$ZIP_PATH" -d "$SCRIPT_DIR" > /dev/null
rm -f "$ZIP_PATH"

# ── Verify ────────────────────────────────────────────────────────────────
if [[ ! -f "$RATINGS" || ! -f "$MOVIES" ]]; then
  error "Extraction failed — expected files not found."
  exit 1
fi

info "Done. Files available:"
info "  ratings.csv  — $(( $(wc -l < "$RATINGS") - 1 )) ratings"
info "  movies.csv   — $(( $(wc -l < "$MOVIES")  - 1 )) movies"

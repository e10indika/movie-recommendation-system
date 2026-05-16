#!/bin/bash
set -e

echo "========================================"
echo "  MovieLens Dataset Downloader"
echo "========================================"
echo "Downloading ml-latest-small (~3MB)…"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="$SCRIPT_DIR/ml-latest-small.zip"

curl -L -o "$ZIP_PATH" https://files.grouplens.org/datasets/movielens/ml-latest-small.zip

echo "Extracting…"
cd "$SCRIPT_DIR"
unzip -o "$ZIP_PATH" -d .

echo ""
echo "Extracted to: $SCRIPT_DIR/ml-latest-small/"
echo "Key files:"
ls "$SCRIPT_DIR/ml-latest-small/"*.csv

# Clean up zip
rm -f "$ZIP_PATH"

echo ""
echo "Done! Now train the model:"
echo "  cd ../backend && python3 train_and_save.py"

#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Dispatcher Lambda Build ==="

if [ ! -f "data.csv" ]; then
    echo "ERROR: data.csv not found. Run create_tester.py first to copy azure.csv."
    exit 1
fi

echo "[1/4] Installing dependencies..."
go mod tidy

echo "[2/4] Building Go binary..."
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -tags lambda.norpc -o bootstrap main.go

echo "[3/4] Creating zip package..."
zip -j dispatcher.zip bootstrap data.csv

echo "[4/4] Cleanup..."
rm -f bootstrap

echo "=== Build complete: dispatcher.zip ==="

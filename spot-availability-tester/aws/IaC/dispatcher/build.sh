#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Dispatcher Lambda Build ==="

# Check if data.csv exists (should be copied by create_tester.py)
if [ ! -f "data.csv" ]; then
    echo "ERROR: data.csv not found. Run create_tester.py first to copy region CSV."
    exit 1
fi

# Install Go dependencies
echo "[1/4] Installing dependencies..."
go mod tidy

# Build for AWS Lambda (Linux AMD64)
echo "[2/4] Building Go binary..."
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -tags lambda.norpc -o bootstrap main.go

# Create zip package
echo "[3/4] Creating zip package..."
zip -j dispatcher.zip bootstrap data.csv

# Cleanup
echo "[4/4] Cleanup..."
rm -f bootstrap

echo "=== Build complete: dispatcher.zip ==="

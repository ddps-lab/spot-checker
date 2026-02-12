#!/bin/bash
# Azure SDK Lambda Layer 빌드 스크립트

set -e

echo "=================================="
echo "Building Azure SDK Lambda Layer"
echo "=================================="

# 기존 파일 정리
rm -rf python azure_sdk_layer.zip

# Python 패키지 디렉토리 생성
LAYER_DIR="python/lib/python3.11/site-packages"
mkdir -p $LAYER_DIR

# Azure SDK 설치 (Lambda 최적화)
echo "Installing Azure SDK packages..."
pip install -r requirements_azure_layer.txt -t $LAYER_DIR \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11

# ZIP 파일 생성
echo "Creating ZIP file..."
zip -r azure_sdk_layer.zip python/

# 정리
rm -rf python/

echo "=================================="
echo "✅ Layer built successfully!"
echo "File: azure_sdk_layer.zip"
echo "Size: $(du -h azure_sdk_layer.zip | cut -f1)"
echo "=================================="


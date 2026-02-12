#!/bin/bash
# Azure SDK Lambda Layer 빌드 스크립트

echo "🔨 Building Azure SDK Lambda Layer..."

# 임시 디렉토리 생성
LAYER_DIR="python/lib/python3.11/site-packages"
mkdir -p $LAYER_DIR

# 패키지 설치
pip install -r requirements_azure_layer.txt -t $LAYER_DIR --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.11

# ZIP 파일 생성
zip -r azure_sdk_layer.zip python/

# 정리
rm -rf python/

echo "✅ azure_sdk_layer.zip created successfully!"


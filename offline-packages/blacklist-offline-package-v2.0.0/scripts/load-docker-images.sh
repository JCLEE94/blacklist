#!/bin/bash
# Docker 이미지 로드 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGES_DIR="$PACKAGE_ROOT/docker-images"

if [[ ! -d "$IMAGES_DIR" ]]; then
    echo "❌ Docker 이미지 디렉토리가 없습니다: $IMAGES_DIR"
    exit 1
fi

echo "🐳 Docker 이미지 로드 중..."

for tar_file in "$IMAGES_DIR"/*.tar; do
    if [[ -f "$tar_file" ]]; then
        echo "  📦 로드 중: $(basename "$tar_file")"
        docker load -i "$tar_file"
    fi
done

echo "✅ Docker 이미지 로드 완료"
echo "📋 로드된 이미지:"
docker images

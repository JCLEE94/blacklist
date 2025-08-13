#!/bin/bash
# Python 의존성 오프라인 설치 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
DEPS_DIR="$PACKAGE_ROOT/dependencies"

if [[ ! -d "$DEPS_DIR" ]]; then
    echo "❌ 의존성 디렉토리가 없습니다: $DEPS_DIR"
    exit 1
fi

echo "🐍 Python 의존성 설치 중..."

# pip 업그레이드 (오프라인)
if [[ -f "$DEPS_DIR/all_wheels/pip"*.whl ]]; then
    python3 -m pip install --no-index --find-links "$DEPS_DIR/all_wheels" --upgrade pip
fi

# 모든 wheels 설치
echo "  📦 패키지 설치 중..."
python3 -m pip install --no-index --find-links "$DEPS_DIR/all_wheels" --requirement "$DEPS_DIR/requirements-frozen.txt"

echo "✅ Python 의존성 설치 완료"

# 설치된 패키지 확인
echo "📋 설치된 패키지:"
python3 -m pip list

#!/bin/bash
# 블랙리스트 시스템 언인스톨 스크립트

set -e

INSTALL_DIR="/opt/blacklist"

echo "🗑️ 블랙리스트 시스템 언인스톨"
echo "==============================="

read -p "정말로 블랙리스트 시스템을 제거하시겠습니까? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "언인스톨이 취소되었습니다."
    exit 0
fi

# 서비스 중지 및 비활성화
echo "🛑 서비스 중지 중..."
systemctl stop blacklist || true
systemctl disable blacklist || true

# Docker 컨테이너 중지 및 제거
echo "🐳 Docker 컨테이너 정리 중..."
if [[ -d "$INSTALL_DIR" ]]; then
    cd "$INSTALL_DIR"
    docker-compose down --volumes --remove-orphans || true
fi

# systemd 서비스 파일 제거
echo "⚙️ systemd 서비스 제거 중..."
rm -f /etc/systemd/system/blacklist.service
systemctl daemon-reload

# 설치 디렉토리 제거
echo "📁 설치 디렉토리 제거 중..."
read -p "데이터베이스와 설정을 포함한 모든 데이터를 삭제하시겠습니까? [y/N]: " delete_data
if [[ "$delete_data" =~ ^[Yy]$ ]]; then
    rm -rf "$INSTALL_DIR"
    echo "  ✅ 모든 데이터 삭제됨"
else
    echo "  ⚠️ 데이터 보존됨: $INSTALL_DIR"
fi

# Docker 이미지 제거 (선택사항)
read -p "Docker 이미지도 제거하시겠습니까? [y/N]: " remove_images
if [[ "$remove_images" =~ ^[Yy]$ ]]; then
    docker rmi registry.jclee.me/blacklist:latest || true
    docker rmi redis:7-alpine || true
    echo "  ✅ Docker 이미지 제거됨"
fi

echo "✅ 블랙리스트 시스템 언인스톨 완료"

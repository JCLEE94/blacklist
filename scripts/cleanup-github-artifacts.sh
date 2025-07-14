#!/bin/bash

# GitHub Actions Artifacts 정리 스크립트
# GitHub API를 사용하여 오래된 artifacts 삭제

set -e

echo "🧹 GitHub Actions Artifacts 정리 시작..."

# 설정
GITHUB_OWNER="JCLEE94"
GITHUB_REPO="blacklist"

# GitHub Token 확인
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN 환경변수가 설정되지 않았습니다."
    echo "사용법: GITHUB_TOKEN=your_token ./scripts/cleanup-github-artifacts.sh"
    exit 1
fi

# Artifacts 목록 가져오기
echo "📋 Artifacts 목록 가져오는 중..."

# 모든 artifacts 가져오기 (최대 100개)
ARTIFACTS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/actions/artifacts?per_page=100" | \
    jq -r '.artifacts[] | "\(.id)|\(.name)|\(.size_in_bytes)|\(.created_at)"')

# 총 크기 계산
TOTAL_SIZE=0
TOTAL_COUNT=0

echo "📊 현재 Artifacts 상태:"
echo "========================="

while IFS='|' read -r id name size created; do
    if [ -n "$id" ]; then
        TOTAL_SIZE=$((TOTAL_SIZE + size))
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        SIZE_MB=$((size / 1024 / 1024))
        echo "- $name (${SIZE_MB}MB) - Created: $created"
    fi
done <<< "$ARTIFACTS"

TOTAL_SIZE_MB=$((TOTAL_SIZE / 1024 / 1024))
echo "========================="
echo "총 개수: $TOTAL_COUNT"
echo "총 크기: ${TOTAL_SIZE_MB}MB"
echo ""

# 삭제 확인
read -p "모든 artifacts를 삭제하시겠습니까? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Artifacts 삭제 중..."
    
    DELETE_COUNT=0
    while IFS='|' read -r id name size created; do
        if [ -n "$id" ]; then
            echo "삭제 중: $name"
            curl -s -X DELETE -H "Authorization: token $GITHUB_TOKEN" \
                "https://api.github.com/repos/$GITHUB_OWNER/$GITHUB_REPO/actions/artifacts/$id"
            DELETE_COUNT=$((DELETE_COUNT + 1))
        fi
    done <<< "$ARTIFACTS"
    
    echo ""
    echo "✅ $DELETE_COUNT 개의 artifacts 삭제 완료!"
else
    echo "❌ 취소되었습니다."
fi
#!/bin/bash

# GitOps 안정화 - 로그 로테이션 스크립트
# 실행: ./scripts/log-rotation.sh

set -e

echo "🔄 GitOps 안정화 - 로그 로테이션 시작"

# 로그 디렉터리 생성
mkdir -p logs/archive

# 현재 로그 크기 확인
echo "📊 로그 정리 전 상태:"
du -sh logs/ || echo "logs 디렉터리 없음"

# 7일 이전 로그 파일 아카이브
echo "📦 7일 이전 로그 파일 아카이브 중..."
find logs/ -name "*.log" -mtime +7 -exec mv {} logs/archive/ \; 2>/dev/null || echo "아카이브할 오래된 로그 없음"

# 대용량 JSON 데이터 파일 정리 (30일 이전)
echo "🗂️ 오래된 JSON 데이터 파일 정리 중..."
find data/ -name "*.json" -mtime +30 -delete 2>/dev/null || echo "정리할 오래된 데이터 파일 없음"

# 임시 파일 정리
echo "🧹 임시 파일 정리 중..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 테스트 리포트 정리 (최신 5개만 유지)
echo "📋 테스트 리포트 정리 중..."
if [ -d "test-reports" ]; then
    ls -t test-reports/*.json 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || echo "정리할 테스트 리포트 없음"
fi

# 로그 크기 제한 (1MB 초과 시 tail로 축소)
echo "✂️ 대용량 로그 파일 축소 중..."
for logfile in $(find logs/ -name "*.log" -size +1M 2>/dev/null); do
    if [ -f "$logfile" ]; then
        echo "  축소 중: $logfile ($(du -h "$logfile" | cut -f1))"
        tail -n 1000 "$logfile" > "${logfile}.tmp"
        mv "${logfile}.tmp" "$logfile"
    fi
done

# 정리 후 상태
echo "📊 로그 정리 후 상태:"
du -sh logs/ 2>/dev/null || echo "logs 디렉터리 없음"

# 로그 로테이션 cron job 제안
echo "⏰ 자동 로그 로테이션을 위해 다음 cron job을 추가하세요:"
echo "0 2 * * * cd /home/jclee/app/blacklist && ./scripts/log-rotation.sh >/dev/null 2>&1"

echo "✅ 로그 로테이션 완료!"
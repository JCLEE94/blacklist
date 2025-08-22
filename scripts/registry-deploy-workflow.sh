#!/bin/bash

# Complete registry.jclee.me deployment workflow
# Version: v1.3.4
# 완전 자동화된 registry.jclee.me 배포 워크플로우

set -e

echo "🚀 registry.jclee.me 전체 배포 워크플로우 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 현재 버전 확인
VERSION=$(cat config/VERSION 2>/dev/null | head -1 || echo "1.3.4")
echo "📋 배포 정보:"
echo "  - 현재 버전: v${VERSION}"
echo "  - 대상 레지스트리: registry.jclee.me"
echo "  - 배포 방식: Watchtower 자동 배포"
echo "  - K8s 지원: 매니페스트만 생성 (수동 배포)"

# 사용자 확인
echo ""
read -p "🤔 registry.jclee.me로 v${VERSION} 배포를 진행하시겠습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 배포 취소됨"
    exit 1
fi

echo ""
echo "⚡ Step 1/5: 빌드 및 푸시 실행"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./scripts/build-and-push.sh

echo ""
echo "⚡ Step 2/5: 배포 상태 확인"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
./scripts/verify-registry-deployment.sh

echo ""
echo "⚡ Step 3/5: Watchtower 모니터링 안내"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Watchtower 모니터링을 위해 다음 명령어들을 사용하세요:"
echo ""
echo "# 실시간 Watchtower 로그 (새 터미널에서 실행 권장)"
echo "docker logs watchtower -f"
echo ""
echo "# 컨테이너 상태 확인"
echo "watch -n 5 'docker ps | grep blacklist'"
echo ""
echo "# 배포 완료 후 헬스체크"
echo "watch -n 10 'curl -s https://blacklist.jclee.me/health | jq .'"

echo ""
echo "⚡ Step 4/5: 헬스체크 대기"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏳ Watchtower 자동 배포 완료까지 5-10분 대기..."
echo "   💡 수동 확인: https://blacklist.jclee.me/health"

# 간단한 대기 루프 (최대 10분)
echo "⏰ 자동 헬스체크 시도 중 (최대 10분)..."
for i in {1..60}; do
    if command -v curl >/dev/null 2>&1; then
        if curl -s --max-time 5 "https://blacklist.jclee.me/health" | grep -q "healthy" 2>/dev/null; then
            echo "✅ 헬스체크 성공! (시도 $i/60)"
            break
        fi
    fi
    
    if [ $i -eq 60 ]; then
        echo "⚠️  자동 헬스체크 시간 초과"
        echo "   🔗 수동 확인 필요: https://blacklist.jclee.me/health"
    else
        echo "   ... 대기 중 ($i/60) - 10초 후 재시도"
        sleep 10
    fi
done

echo ""
echo "⚡ Step 5/5: 배포 완료 요약"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 registry.jclee.me 배포 워크플로우 완료!"
echo ""
echo "📋 완료된 작업:"
echo "  ✅ Docker 이미지 빌드 (main, redis, postgresql)"
echo "  ✅ registry.jclee.me 푸시 완료"
echo "  ✅ K8s 매니페스트 생성 (k8s-manifests/)"
echo "  ⏳ Watchtower 자동 배포 (진행 중)"
echo ""
echo "🔗 확인 링크:"
echo "  - 라이브 시스템: https://blacklist.jclee.me/"
echo "  - 헬스체크: https://blacklist.jclee.me/health"
echo "  - API 상태: https://blacklist.jclee.me/api/health"
echo "  - 대시보드: https://blacklist.jclee.me/dashboard"
echo ""
echo "📊 모니터링 명령어:"
echo "  - Watchtower 로그: docker logs watchtower -f"
echo "  - 컨테이너 상태: docker ps | grep blacklist"
echo "  - 앱 로그: docker logs blacklist -f"
echo ""
echo "⚠️  주의사항:"
echo "  - AI는 운영서버에 직접 접근 불가"
echo "  - 실제 배포 상태는 위 링크로 수동 확인 필요"
echo "  - K8s 매니페스트는 별도 수동 배포 필요"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
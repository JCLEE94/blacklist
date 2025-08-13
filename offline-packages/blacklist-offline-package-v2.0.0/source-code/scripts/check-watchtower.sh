#!/bin/bash
# Watchtower 상태 및 감지 문제 진단 스크립트

echo "🔍 Watchtower 감지 문제 진단"
echo "================================"

# 1. 현재 이미지 태그 확인
echo "📦 현재 로컬 이미지:"
docker images | grep "registry.jclee.me/jclee94/blacklist" || echo "로컬 이미지 없음"

# 2. Registry에서 최신 이미지 확인
echo -e "\n🌐 Registry 최신 이미지 확인:"
docker manifest inspect registry.jclee.me/jclee94/blacklist:latest 2>/dev/null && echo "✅ Registry 이미지 존재" || echo "❌ Registry 접근 불가"

# 3. 운영 서버 연결 테스트
echo -e "\n🔗 운영 서버 연결 테스트:"
ping -c 1 192.168.50.215 >/dev/null 2>&1 && echo "✅ 서버 연결 가능" || echo "❌ 서버 연결 불가"

# 4. 서비스 응답 테스트
echo -e "\n🌍 서비스 응답 테스트:"
curl -s --connect-timeout 5 http://192.168.50.215:30001/health >/dev/null 2>&1 && echo "✅ 서비스 응답 정상" || echo "❌ 서비스 응답 없음"

# 5. 최근 커밋 정보
echo -e "\n📝 최근 커밋 (최신 3개):"
git log --oneline -3

# 6. Watchtower 수동 트리거 방법
echo -e "\n🔄 수동 해결 방법:"
echo "1. 새 커밋으로 GitHub Actions 트리거:"
echo "   git commit --allow-empty -m 'trigger: Watchtower 수동 배포 테스트'"
echo "   git push"
echo ""
echo "2. 운영 서버 직접 업데이트 (SSH 접근 가능시):"
echo "   ssh docker@192.168.50.215 -p 1111"
echo "   docker pull registry.jclee.me/jclee94/blacklist:latest"
echo "   docker-compose up -d"
echo ""
echo "3. Watchtower 강제 업데이트 (컨테이너 내에서):"
echo "   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --run-once"

echo -e "\n✨ 진단 완료"
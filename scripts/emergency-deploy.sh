#!/bin/bash
# 응급 수동 배포 스크립트

echo "🚨 응급 수동 배포 실행"
echo "====================="

# 1. 로컬에서 이미지 빌드
echo "🔨 로컬 이미지 빌드 중..."
docker build -t registry.jclee.me/jclee94/blacklist:emergency -f deployment/Dockerfile .

if [ $? -eq 0 ]; then
    echo "✅ 이미지 빌드 성공"
else
    echo "❌ 이미지 빌드 실패"
    exit 1
fi

# 2. Registry 푸시 시도
echo "📤 Registry 푸시 시도..."
docker tag registry.jclee.me/jclee94/blacklist:emergency registry.jclee.me/jclee94/blacklist:latest
docker push registry.jclee.me/jclee94/blacklist:latest

if [ $? -eq 0 ]; then
    echo "✅ Registry 푸시 성공"
else
    echo "❌ Registry 푸시 실패 - 로컬 컨테이너로 테스트"
fi

# 3. 로컬 테스트 실행
echo "🧪 로컬 테스트 실행..."
docker-compose down 2>/dev/null
docker-compose up -d

echo "⏳ 서비스 시작 대기 (30초)..."
sleep 30

# 4. 헬스체크
if curl -s http://localhost:2541/health >/dev/null 2>&1; then
    echo "✅ 로컬 서비스 정상 응답"
    curl -s http://localhost:2541/health | jq '.' || echo "JSON 파싱 실패"
else
    echo "❌ 로컬 서비스 응답 없음"
    docker-compose logs blacklist
fi

echo ""
echo "🎯 다음 단계:"
echo "1. 로컬 테스트 확인: http://localhost:2541"
echo "2. 원격 서버 수동 배포 필요시 SSH 접근"
echo "3. Watchtower 로그 확인 필요"
#\!/bin/bash
# 단일 컨테이너 배포 스크립트

echo "🔄 단일 컨테이너로 전환 시작..."

# 현재 상태 확인
echo "현재 실행 중인 컨테이너:"
docker ps  < /dev/null |  grep blacklist

# 기존 컨테이너 정지
echo "기존 컨테이너 정지..."
docker-compose down

# 최신 이미지 풀
echo "최신 이미지 다운로드..."
docker pull registry.jclee.me/blacklist:latest

# 환경변수 설정
export BLACKLIST_INSTANCE_PATH=/volume1/app/blacklist/instance
export BLACKLIST_DATA_PATH=/volume1/app/blacklist/data
export BLACKLIST_LOGS_PATH=/volume1/app/blacklist/logs

# 디렉토리 생성
mkdir -p $BLACKLIST_INSTANCE_PATH $BLACKLIST_DATA_PATH $BLACKLIST_LOGS_PATH

# 단일 컨테이너 실행
echo "단일 컨테이너 시작..."
docker-compose -f docker-compose.single.yml up -d

# 결과 확인
echo "배포 완료! 상태 확인:"
docker ps
echo ""
echo "헬스 체크:"
sleep 5
curl -s http://localhost:2541/health

echo "✅ 단일 컨테이너 배포 완료"

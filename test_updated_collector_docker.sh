#!/bin/bash
# Docker 컨테이너에서 업데이트된 수집기 테스트

echo "🧪 Docker 컨테이너에서 REGTECH 수집기 테스트"

# 기존 컨테이너 정지
docker stop blacklist 2>/dev/null

# 새 이미지로 컨테이너 실행
echo "🚀 Docker 컨테이너 시작..."
docker run -d --rm \
  --name blacklist \
  -p 8541:8541 \
  -e REGTECH_USERNAME=nextrade \
  -e REGTECH_PASSWORD=Sprtmxm1@3 \
  -e REGTECH_BEARER_TOKEN="BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzdtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMTkyNzYsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.YwZHoHZCVqDnaryluB0h5_ituxYcaRz4voT7GRfgrNrP86W8TfvBuJbHMON4tJa4AQmNP-XhC_PuAVPQTjJADA" \
  -e SECUDIUM_USERNAME=nextrade \
  -e SECUDIUM_PASSWORD=Sprtmxm1@3 \
  -v $(pwd)/instance:/app/instance \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  61f0e8289c84

echo "⏳ 컨테이너 시작 대기 중..."
sleep 10

# 수집 상태 확인
echo -e "\n📊 수집 상태 확인:"
curl -s http://localhost:8541/api/collection/status | python3 -m json.tool

# REGTECH 수집 트리거
echo -e "\n🔄 REGTECH 수집 시작:"
curl -X POST http://localhost:8541/api/collection/regtech/trigger

# 로그 확인
echo -e "\n📋 컨테이너 로그 (마지막 50줄):"
docker logs --tail 50 blacklist

# 수집된 데이터 확인
echo -e "\n🔍 수집된 REGTECH IP 수 확인:"
docker exec blacklist python3 -c "
import sqlite3
conn = sqlite3.connect('/app/instance/blacklist.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM blacklist_ip WHERE source = \"REGTECH\"')
count = cursor.fetchone()[0]
print(f'REGTECH IPs in database: {count}')
conn.close()
"

# 컨테이너 정지
echo -e "\n🛑 테스트 완료. 컨테이너 정지..."
docker stop blacklist
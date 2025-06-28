#!/bin/bash
# 새 Bearer Token으로 Docker 배포

echo "🚀 새 Bearer Token으로 배포 시작"

# Bearer Token 설정
export REGTECH_BEARER_TOKEN="BearereyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJuZXh0cmFkZSIsIm9yZ2FubmFtZSI6IuuEpeyKpO2KuOugiIzdtOuTnCIsImlkIjoibmV4dHJhZGUiLCJleHAiOjE3NTExMjY3NjMsInVzZXJuYW1lIjoi7J6l7ZmN7KSAIn0.3OgfysLpyaYM51KKBtZEb-O8L_juvwLsE07RL4Za1RnZrPW0C3P65Vt4mIYH56zU9Uu-wUuaNmogClKoa4Oy_w"

# .env 파일에 저장
echo "REGTECH_BEARER_TOKEN=$REGTECH_BEARER_TOKEN" > .env.regtech

echo "✅ Bearer Token 저장됨: .env.regtech"

# Docker Compose 실행
echo -e "\n🐳 Docker 컨테이너 재시작..."
docker-compose --env-file .env.regtech -f deployment/docker-compose.yml down
docker-compose --env-file .env.regtech -f deployment/docker-compose.yml up -d

echo -e "\n⏳ 컨테이너 시작 대기 중..."
sleep 10

# 수집 상태 확인
echo -e "\n📊 수집 상태 확인:"
curl -s http://localhost:2541/api/collection/status | python3 -m json.tool

# REGTECH 수집 트리거
echo -e "\n🔄 REGTECH 수집 트리거:"
curl -X POST http://localhost:2541/api/collection/regtech/trigger

echo -e "\n✅ 배포 완료!"
echo "이제 5,587개의 REGTECH IP를 수집할 수 있습니다."
#!/bin/bash
# 초기 수집 트리거 스크립트

echo "Blacklist 초기 수집 시작..."

# Pod 이름 가져오기
POD=$(kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
    echo "❌ Pod을 찾을 수 없습니다"
    exit 1
fi

echo "✅ Pod 찾음: $POD"

# 포트 포워딩 시작 (백그라운드)
kubectl port-forward -n blacklist pod/$POD 8541:2541 &
PF_PID=$!
sleep 3

# 수집 활성화
echo "📊 수집 활성화 중..."
curl -X POST http://localhost:8541/api/collection/enable

# 각 소스 수집 트리거
echo "🔄 REGTECH 수집 시작..."
curl -X POST http://localhost:8541/api/collection/regtech/trigger

echo "🔄 SECUDIUM 수집 시작..."
curl -X POST http://localhost:8541/api/collection/secudium/trigger

# 상태 확인
echo "📊 수집 상태 확인..."
curl http://localhost:8541/api/collection/status | jq .

# 포트 포워딩 종료
kill $PF_PID

echo "✅ 초기 수집 트리거 완료"
#!/bin/bash

echo "🔧 Registry 인증 문제 해결 중..."

# 1. Registry Secret 생성
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  -n blacklist \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. 기존 Pod 재시작
kubectl delete pods -l app=blacklist -n blacklist

# 3. 상태 확인
echo "⏳ Pod 재시작 대기 중..."
sleep 10

kubectl get pods -n blacklist
kubectl get events -n blacklist --sort-by='.lastTimestamp' | tail -10

echo "🌐 서비스 접근 테스트..."
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}')
echo "애플리케이션 URL: http://$NODE_IP:32452"

# 헬스체크 테스트
if curl -f http://$NODE_IP:32452/health 2>/dev/null; then
    echo "✅ 배포 성공! 애플리케이션이 정상 실행 중입니다."
else
    echo "⚠️ 아직 준비 중이거나 추가 확인이 필요합니다."
    echo "로그 확인: kubectl logs -l app=blacklist -n blacklist"
fi
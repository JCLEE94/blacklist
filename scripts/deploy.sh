#!/bin/bash
# Linux/Mac 배포 스크립트

echo "🚀 Blacklist 배포 시작..."

# 기존 리소스 정리
kubectl delete all --all -n blacklist 2>/dev/null
kubectl create namespace blacklist 2>/dev/null

# Registry Secret 생성
kubectl delete secret regcred -n blacklist 2>/dev/null
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=registry_username \
  --docker-password=registry_password \
  -n blacklist

# 배포 (PVC 포함)
kubectl apply -k k8s/

echo "⏳ Pod 초기화 대기 중..."

# Pod이 Running 상태가 될 때까지 모니터링
while true; do
    # Pod 상태 확인
    POD_STATUS=$(kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    POD_READY=$(kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null)
    
    echo "Pod 상태: $POD_STATUS, Ready: $POD_READY"
    
    if [ "$POD_STATUS" = "Running" ] && [ "$POD_READY" = "true" ]; then
        echo "✅ Pod 초기화 완료!"
        break
    fi
    
    if [ "$POD_STATUS" = "Failed" ] || [ "$POD_STATUS" = "CrashLoopBackOff" ]; then
        echo "❌ Pod 실패!"
        kubectl get pods -n blacklist
        kubectl describe pods -n blacklist
        exit 1
    fi
    
    sleep 2
done

echo "📊 최종 상태:"
kubectl get all -n blacklist

echo "📝 초기화 로그:"
kubectl logs deployment/blacklist -n blacklist --tail=20
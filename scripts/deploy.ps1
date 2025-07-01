# Windows 배포 스크립트

Write-Host "🚀 Blacklist 배포 시작..." -ForegroundColor Cyan

# 기존 리소스 및 네임스페이스 완전 삭제
Write-Host "🗑️ 기존 리소스 정리 중..." -ForegroundColor Yellow
kubectl delete all --all -n blacklist 2>$null
kubectl delete namespace blacklist --force --grace-period=0 2>$null

# Terminating 상태 해결
kubectl patch namespace blacklist -p '{\"metadata\":{\"finalizers\":null}}' --type=merge 2>$null

# 완전 삭제 대기
Write-Host "⏳ 네임스페이스 삭제 대기..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 새 네임스페이스 생성
Write-Host "📦 새 네임스페이스 생성..." -ForegroundColor Green
kubectl create namespace blacklist

# Registry Secret 생성
kubectl delete secret regcred -n blacklist
kubectl create secret docker-registry regcred --docker-server=registry.jclee.me --docker-username=qws9411 --docker-password=bingogo1 -n blacklist

# PV 먼저 생성
kubectl apply -f k8s/pv.yaml

# 배포
kubectl apply -k k8s/

Write-Host "⏳ 5초 대기..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "📊 배포 상태:" -ForegroundColor Cyan
kubectl get all -n blacklist

Write-Host "📝 Pod 로그:" -ForegroundColor Cyan
kubectl logs deployment/blacklist -n blacklist -c blacklist --tail=10
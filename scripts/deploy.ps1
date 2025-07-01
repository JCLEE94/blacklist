# Windows 배포 스크립트

Write-Host "🚀 Blacklist 배포 시작..." -ForegroundColor Cyan

# 기존 리소스 정리
kubectl delete all --all -n blacklist
kubectl create namespace blacklist

# Registry Secret 생성
kubectl delete secret regcred -n blacklist
kubectl create secret docker-registry regcred --docker-server=registry.jclee.me --docker-username=qws9411 --docker-password=bingogo1 -n blacklist

# 배포
kubectl apply -k k8s/

Write-Host "⏳ 5초 대기..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "📊 배포 상태:" -ForegroundColor Cyan
kubectl get all -n blacklist

Write-Host "📝 Pod 로그:" -ForegroundColor Cyan
kubectl logs deployment/blacklist -n blacklist --tail=10
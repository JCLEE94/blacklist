# 클린 배포 스크립트 - 기존 리소스 삭제 후 재배포 (PowerShell)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Blacklist 클린 배포 (PowerShell)" -ForegroundColor Cyan
Write-Host "  기존 리소스 삭제 후 재배포" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 기존 리소스 삭제
Write-Host "[1/3] 기존 리소스 삭제 중..." -ForegroundColor Yellow
kubectl delete deployment blacklist -n blacklist 2>$null
kubectl delete deployment blacklist-redis -n blacklist 2>$null
kubectl delete service blacklist -n blacklist 2>$null
kubectl delete service blacklist-nodeport -n blacklist 2>$null
kubectl delete service blacklist-redis -n blacklist 2>$null
kubectl delete pods --all -n blacklist 2>$null
Write-Host "[OK] 기존 리소스 삭제 완료" -ForegroundColor Green
Write-Host ""

# 2. 잠시 대기
Write-Host "[2/3] 5초 대기..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Write-Host ""

# 3. 새로 배포
Write-Host "[3/3] 새로 배포 시작..." -ForegroundColor Yellow
Write-Host ""

$files = @(
    @{Name="네임스페이스"; File="k8s/namespace.yaml"},
    @{Name="ConfigMap"; File="k8s/configmap.yaml"},
    @{Name="Secret"; File="k8s/secret.yaml"},
    @{Name="PVC"; File="k8s/pvc.yaml"},
    @{Name="Redis"; File="k8s/redis.yaml"},
    @{Name="메인 앱"; File="k8s/deployment.yaml"},
    @{Name="서비스"; File="k8s/service.yaml"}
)

foreach ($item in $files) {
    Write-Host "$($item.Name)..." -ForegroundColor Gray
    kubectl apply -f $item.File
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  배포 완료! Pod 상태 확인" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
kubectl get pods -n blacklist

Write-Host ""
Write-Host "실시간 모니터링: kubectl get pods -n blacklist -w" -ForegroundColor Yellow
Read-Host "Press Enter to exit"
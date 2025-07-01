# Windows 배포 스크립트

Write-Host "🚀 Blacklist 배포 시작..." -ForegroundColor Cyan

# 기존 리소스 정리
kubectl delete all --all -n blacklist 2>$null
kubectl create namespace blacklist 2>$null

# Registry Secret 생성
kubectl delete secret regcred -n blacklist 2>$null
kubectl create secret docker-registry regcred `
  --docker-server=registry.jclee.me `
  --docker-username=registry_username `
  --docker-password=registry_password `
  -n blacklist

# PVC 생성
$pvcYaml = @"
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: blacklist-data
  namespace: blacklist
spec:
  accessModes: 
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: blacklist-logs
  namespace: blacklist
spec:
  accessModes: 
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: blacklist-instance
  namespace: blacklist
spec:
  accessModes: 
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
"@

$pvcYaml | kubectl apply -f -

# 배포
kubectl apply -k k8s/

Write-Host "⏳ Pod 초기화 대기 중..." -ForegroundColor Yellow

# Pod이 Running 상태가 될 때까지 모니터링
while ($true) {
    try {
        $podStatus = kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].status.phase}' 2>$null
        $podReady = kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>$null
        
        Write-Host "Pod 상태: $podStatus, Ready: $podReady" -ForegroundColor Gray
        
        if ($podStatus -eq "Running" -and $podReady -eq "true") {
            Write-Host "✅ Pod 초기화 완료!" -ForegroundColor Green
            break
        }
        
        if ($podStatus -eq "Failed" -or $podStatus -eq "CrashLoopBackOff") {
            Write-Host "❌ Pod 실패!" -ForegroundColor Red
            kubectl get pods -n blacklist
            kubectl describe pods -n blacklist
            exit 1
        }
        
        Start-Sleep -Seconds 2
    }
    catch {
        Write-Host "상태 확인 중..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

Write-Host "📊 최종 상태:" -ForegroundColor Cyan
kubectl get all -n blacklist

Write-Host "📝 초기화 로그:" -ForegroundColor Cyan
kubectl logs deployment/blacklist -n blacklist --tail=20
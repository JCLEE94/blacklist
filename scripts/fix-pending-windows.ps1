# Pending Pod 문제 해결 스크립트 (PowerShell)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Pending Pod 문제 해결" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 현재 Pod 상태
Write-Host "[1/6] 현재 Pod 상태 확인..." -ForegroundColor Yellow
kubectl get pods -n blacklist
Write-Host ""

# 2. Pending Pod 찾기
Write-Host "[2/6] Pending Pod 이벤트 확인..." -ForegroundColor Yellow
$pendingPods = kubectl get pods -n blacklist -o json | ConvertFrom-Json | 
    Select-Object -ExpandProperty items | 
    Where-Object { $_.status.phase -eq "Pending" }

foreach ($pod in $pendingPods) {
    Write-Host ""
    Write-Host "=== Pod: $($pod.metadata.name) ===" -ForegroundColor Cyan
    kubectl describe pod $($pod.metadata.name) -n blacklist | Select-String -Pattern "Events:" -Context 0,20
}
Write-Host ""

# 3. PVC 상태 확인
Write-Host "[3/6] PVC 상태 확인..." -ForegroundColor Yellow
kubectl get pvc -n blacklist
$unboundPVCs = kubectl get pvc -n blacklist -o json | ConvertFrom-Json | 
    Select-Object -ExpandProperty items | 
    Where-Object { $_.status.phase -ne "Bound" }

if ($unboundPVCs.Count -gt 0) {
    Write-Host "경고: Bound되지 않은 PVC가 있습니다!" -ForegroundColor Red
}
Write-Host ""

# 4. 노드 리소스 확인
Write-Host "[4/6] 노드 리소스 확인..." -ForegroundColor Yellow
kubectl get nodes
kubectl top nodes 2>$null
Write-Host ""

# 5. 자동 수정 시도
Write-Host "[5/6] 자동 수정 적용 중..." -ForegroundColor Yellow

# Pending Pod 삭제
Write-Host "- Pending Pod 삭제..." -ForegroundColor Gray
kubectl delete pods -n blacklist --field-selector=status.phase=Pending

# 레플리카 수 조정
Write-Host "- 레플리카 수를 1로 조정..." -ForegroundColor Gray
kubectl scale deployment blacklist --replicas=1 -n blacklist

Write-Host ""

# 6. 결과 확인
Write-Host "[6/6] 수정 후 상태..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
kubectl get pods -n blacklist
Write-Host ""

# 추가 권장사항
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  추가 권장사항" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Docker Desktop 리소스 증가:" -ForegroundColor Yellow
Write-Host "   - Settings > Resources > Advanced" -ForegroundColor Gray
Write-Host "   - CPUs: 4+ cores" -ForegroundColor Gray
Write-Host "   - Memory: 8+ GB" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 수동으로 레플리카 조정:" -ForegroundColor Yellow
Write-Host "   kubectl scale deployment blacklist --replicas=2 -n blacklist" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 실시간 모니터링:" -ForegroundColor Yellow
Write-Host "   kubectl get pods -n blacklist -w" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"
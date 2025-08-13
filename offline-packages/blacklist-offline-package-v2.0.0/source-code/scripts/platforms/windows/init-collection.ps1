# 초기 수집 트리거 스크립트 (PowerShell)

Write-Host "Blacklist 초기 수집 시작..." -ForegroundColor Cyan

# Pod 이름 가져오기
$pod = kubectl get pods -n blacklist -l app=blacklist -o jsonpath='{.items[0].metadata.name}'

if (-not $pod) {
    Write-Host "❌ Pod을 찾을 수 없습니다" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Pod 찾음: $pod" -ForegroundColor Green

# 포트 포워딩 시작
$job = Start-Job -ScriptBlock {
    kubectl port-forward -n blacklist pod/$using:pod 8541:2541
}
Start-Sleep -Seconds 3

# 수집 활성화
Write-Host "📊 수집 활성화 중..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:8541/api/collection/enable" -Method POST

# 각 소스 수집 트리거
Write-Host "🔄 REGTECH 수집 시작..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:8541/api/collection/regtech/trigger" -Method POST

Write-Host "🔄 SECUDIUM 수집 시작..." -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:8541/api/collection/secudium/trigger" -Method POST

# 상태 확인
Write-Host "📊 수집 상태 확인..." -ForegroundColor Yellow
$status = Invoke-RestMethod -Uri "http://localhost:8541/api/collection/status"
$status | ConvertTo-Json -Depth 10

# 포트 포워딩 종료
Stop-Job $job
Remove-Job $job

Write-Host "✅ 초기 수집 트리거 완료" -ForegroundColor Green
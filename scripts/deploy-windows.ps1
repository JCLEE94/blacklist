# Blacklist Kubernetes 배포 스크립트 (PowerShell)
# 작성자: Claude
# 설명: Windows PowerShell 환경에서 Kubernetes 배포

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Blacklist Kubernetes 배포 스크립트" -ForegroundColor Cyan
Write-Host "  PowerShell 버전" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 현재 디렉토리 확인
Write-Host "[1/10] 현재 디렉토리: $PWD" -ForegroundColor Yellow
Write-Host ""

# k8s 디렉토리 존재 확인
if (-not (Test-Path "k8s")) {
    Write-Host "[ERROR] k8s 디렉토리를 찾을 수 없습니다!" -ForegroundColor Red
    Write-Host "프로젝트 루트 디렉토리에서 실행해주세요." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    Write-Host "[2/10] 네임스페이스 생성..." -ForegroundColor Yellow
    kubectl apply -f k8s/namespace.yaml
    Write-Host "[OK] 네임스페이스 생성 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[3/10] ConfigMap 생성..." -ForegroundColor Yellow
    kubectl apply -f k8s/configmap.yaml
    Write-Host "[OK] ConfigMap 생성 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[4/10] Secret 생성..." -ForegroundColor Yellow
    kubectl apply -f k8s/secret.yaml
    Write-Host "[OK] Secret 생성 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[5/10] PVC 생성..." -ForegroundColor Yellow
    kubectl apply -f k8s/pvc.yaml
    if (Test-Path "k8s/pvc-instance.yaml") {
        kubectl apply -f k8s/pvc-instance.yaml
    }
    Write-Host "[OK] PVC 생성 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[6/10] Redis 배포..." -ForegroundColor Yellow
    kubectl apply -f k8s/redis.yaml
    Write-Host "[OK] Redis 배포 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[7/10] 메인 애플리케이션 배포..." -ForegroundColor Yellow
    kubectl apply -f k8s/deployment.yaml
    Write-Host "[OK] 애플리케이션 배포 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[8/10] 서비스 생성..." -ForegroundColor Yellow
    kubectl apply -f k8s/service.yaml
    Write-Host "[OK] 서비스 생성 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[9/10] Pending 상태 Pod 정리..." -ForegroundColor Yellow
    kubectl delete pods -n blacklist --field-selector=status.phase=Pending 2>$null
    Write-Host "[OK] Pending Pod 정리 완료" -ForegroundColor Green
    Write-Host ""

    Write-Host "[10/10] 배포 상태 확인..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "=== Pod 상태 ===" -ForegroundColor Cyan
    kubectl get pods -n blacklist
    Write-Host ""
    Write-Host "=== 서비스 상태 ===" -ForegroundColor Cyan
    kubectl get services -n blacklist
    Write-Host ""
    Write-Host "=== PVC 상태 ===" -ForegroundColor Cyan
    kubectl get pvc -n blacklist
    Write-Host ""

    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "  배포가 완료되었습니다!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Pod이 Running 상태가 될 때까지 기다려주세요." -ForegroundColor Yellow
    Write-Host "상태 확인: kubectl get pods -n blacklist -w" -ForegroundColor Yellow
}
catch {
    Write-Host "[ERROR] 배포 중 오류 발생: $_" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"
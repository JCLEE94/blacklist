# ImagePullBackOff 문제 해결 스크립트 (PowerShell)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  ImagePullBackOff 문제 해결" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 문제 진단
Write-Host "[1/5] ImagePullBackOff Pod 확인..." -ForegroundColor Yellow
$problemPods = kubectl get pods -n blacklist | Select-String "ImagePull"
if ($problemPods) {
    Write-Host $problemPods -ForegroundColor Red
} else {
    Write-Host "ImagePullBackOff 상태의 Pod이 없습니다." -ForegroundColor Green
}
Write-Host ""

# 2. 상세 오류 확인
Write-Host "[2/5] 상세 오류 메시지 확인..." -ForegroundColor Yellow
$pods = kubectl get pods -n blacklist -o json | ConvertFrom-Json
foreach ($pod in $pods.items) {
    $containerStatuses = $pod.status.containerStatuses
    foreach ($status in $containerStatuses) {
        if ($status.state.waiting.reason -eq "ImagePullBackOff" -or $status.state.waiting.reason -eq "ErrImagePull") {
            Write-Host ""
            Write-Host "Pod: $($pod.metadata.name)" -ForegroundColor Cyan
            Write-Host "Image: $($status.image)" -ForegroundColor Gray
            Write-Host "Error: $($status.state.waiting.message)" -ForegroundColor Red
            
            # Pod 이벤트 확인
            Write-Host "`n이벤트:" -ForegroundColor Yellow
            kubectl describe pod $($pod.metadata.name) -n blacklist | Select-String -Pattern "Events:" -Context 0,10
        }
    }
}
Write-Host ""

# 3. Registry Secret 확인
Write-Host "[3/5] Docker Registry Secret 확인..." -ForegroundColor Yellow
$secret = kubectl get secret regcred -n blacklist 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "경고: regcred secret이 없습니다!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Registry Secret 생성 명령어:" -ForegroundColor Yellow
    Write-Host 'kubectl create secret docker-registry regcred `' -ForegroundColor Gray
    Write-Host '  --docker-server=registry.jclee.me `' -ForegroundColor Gray
    Write-Host '  --docker-username=YOUR_USERNAME `' -ForegroundColor Gray
    Write-Host '  --docker-password=YOUR_PASSWORD `' -ForegroundColor Gray
    Write-Host '  -n blacklist' -ForegroundColor Gray
} else {
    Write-Host "regcred secret이 존재합니다." -ForegroundColor Green
}
Write-Host ""

# 4. 로컬 이미지 사용 시도
Write-Host "[4/5] 해결 방법 적용..." -ForegroundColor Yellow
Write-Host ""
Write-Host "옵션 1: 공개 Docker Hub 이미지 사용" -ForegroundColor Cyan
Write-Host "kubectl set image deployment/blacklist blacklist=nginx:latest -n blacklist" -ForegroundColor Gray
Write-Host ""

Write-Host "옵션 2: imagePullPolicy를 Never로 변경 (로컬 이미지 사용)" -ForegroundColor Cyan
$patchJson = @'
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "blacklist",
            "imagePullPolicy": "IfNotPresent"
          }
        ]
      }
    }
  }
}
'@
Write-Host "적용 중..." -ForegroundColor Gray
kubectl patch deployment blacklist -n blacklist --type merge -p $patchJson
Write-Host ""

Write-Host "옵션 3: 로컬에서 이미지 빌드" -ForegroundColor Cyan
Write-Host "docker build -t blacklist:local ." -ForegroundColor Gray
Write-Host "kubectl set image deployment/blacklist blacklist=blacklist:local -n blacklist" -ForegroundColor Gray
Write-Host ""

# 5. Pod 재시작
Write-Host "[5/5] Pod 재시작..." -ForegroundColor Yellow
kubectl delete pods -n blacklist --field-selector=status.phase!=Running
Write-Host ""

# 대기 후 상태 확인
Write-Host "5초 후 상태 확인..." -ForegroundColor Gray
Start-Sleep -Seconds 5
kubectl get pods -n blacklist
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  추가 도움말" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Private Registry 인증 문제인 경우:" -ForegroundColor Yellow
Write-Host "   - Docker Desktop에서 로그인: docker login registry.jclee.me" -ForegroundColor Gray
Write-Host "   - Secret 재생성 필요" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 네트워크 문제인 경우:" -ForegroundColor Yellow
Write-Host "   - VPN 연결 확인" -ForegroundColor Gray
Write-Host "   - 프록시 설정 확인" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 이미지가 존재하지 않는 경우:" -ForegroundColor Yellow
Write-Host "   - 이미지 태그 확인" -ForegroundColor Gray
Write-Host "   - Registry에 이미지 존재 여부 확인" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"
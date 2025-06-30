# Blacklist Management System - Kubernetes Management Script for Windows
# PowerShell 스크립트로 Kubernetes 환경을 쉽게 관리할 수 있습니다.

param(
    [Parameter(Position=0)]
    [string]$Action,
    
    [Parameter(Position=1)]
    [string]$Option
)

# 색상 출력 함수
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

# 설정
$NAMESPACE = "blacklist"
$DEPLOYMENT = "blacklist"
$REGISTRY = "registry.jclee.me"

function Show-Help {
    Write-Info "=== Blacklist Kubernetes Management Tool ==="
    Write-Output ""
    Write-Output "사용법: .\k8s-management.ps1 [명령] [옵션]"
    Write-Output ""
    Write-Output "명령어:"
    Write-Output "  deploy       - Kubernetes에 애플리케이션 배포"
    Write-Output "  status       - 현재 배포 상태 확인"
    Write-Output "  logs         - 애플리케이션 로그 보기"
    Write-Output "  scale        - 레플리카 수 조정 (예: scale 4)"
    Write-Output "  restart      - 애플리케이션 재시작"
    Write-Output "  rollback     - 이전 버전으로 롤백"
    Write-Output "  pods         - Pod 목록 및 상태"
    Write-Output "  describe     - Pod 상세 정보"
    Write-Output "  exec         - Pod에 접속"
    Write-Output "  health       - 헬스 체크"
    Write-Output "  cleanup      - 리소스 정리"
    Write-Output "  setup        - 초기 설정"
    Write-Output ""
    Write-Output "예시:"
    Write-Output "  .\k8s-management.ps1 deploy"
    Write-Output "  .\k8s-management.ps1 scale 4"
    Write-Output "  .\k8s-management.ps1 logs"
}

function Test-Prerequisites {
    Write-Info "전제 조건 확인 중..."
    
    # kubectl 확인
    try {
        kubectl version --client --short | Out-Null
        Write-Success "✓ kubectl 사용 가능"
    } catch {
        Write-Error "✗ kubectl이 설치되지 않았거나 PATH에 없습니다"
        return $false
    }
    
    # cluster 연결 확인
    try {
        kubectl cluster-info | Out-Null
        Write-Success "✓ Kubernetes 클러스터 연결됨"
    } catch {
        Write-Error "✗ Kubernetes 클러스터에 연결할 수 없습니다"
        return $false
    }
    
    return $true
}

function Deploy-Application {
    Write-Info "애플리케이션 배포 시작..."
    
    # namespace 생성
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    Write-Success "✓ Namespace 생성/확인 완료"
    
    # ConfigMap과 Secret 배포
    if (Test-Path "k8s/configmap.yaml") {
        kubectl apply -f k8s/configmap.yaml
        Write-Success "✓ ConfigMap 배포 완료"
    }
    
    if (Test-Path "k8s/secret.yaml") {
        kubectl apply -f k8s/secret.yaml
        Write-Success "✓ Secret 배포 완료"
    }
    
    # 전체 k8s 리소스 배포
    kubectl apply -f k8s/
    Write-Success "✓ 모든 리소스 배포 완료"
    
    Write-Info "배포 상태 확인 중..."
    kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE
}

function Get-Status {
    Write-Info "=== 현재 배포 상태 ==="
    
    # Deployment 상태
    Write-Info "Deployment 상태:"
    kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o wide
    
    # Pod 상태
    Write-Info "`nPod 상태:"
    kubectl get pods -n $NAMESPACE -o wide
    
    # Service 상태
    Write-Info "`nService 상태:"
    kubectl get svc -n $NAMESPACE
    
    # Ingress 상태 (있다면)
    Write-Info "`nIngress 상태:"
    kubectl get ingress -n $NAMESPACE 2>$null
}

function Get-Logs {
    if ($Option) {
        # 특정 Pod 로그
        Write-Info "Pod '$Option' 로그:"
        kubectl logs $Option -n $NAMESPACE -f
    } else {
        # Deployment 로그
        Write-Info "애플리케이션 로그 (Ctrl+C로 종료):"
        kubectl logs -f deployment/$DEPLOYMENT -n $NAMESPACE
    }
}

function Scale-Application {
    if (-not $Option) {
        Write-Error "레플리카 수를 지정해주세요. 예: .\k8s-management.ps1 scale 4"
        return
    }
    
    Write-Info "레플리카를 $Option 개로 조정 중..."
    kubectl scale deployment $DEPLOYMENT --replicas=$Option -n $NAMESPACE
    
    Write-Info "스케일링 상태 확인 중..."
    kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE
    Write-Success "✓ 스케일링 완료"
}

function Restart-Application {
    Write-Info "애플리케이션 재시작 중..."
    kubectl rollout restart deployment/$DEPLOYMENT -n $NAMESPACE
    
    Write-Info "재시작 상태 확인 중..."
    kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE
    Write-Success "✓ 재시작 완료"
}

function Rollback-Application {
    Write-Info "배포 히스토리 확인:"
    kubectl rollout history deployment/$DEPLOYMENT -n $NAMESPACE
    
    Write-Info "`n이전 버전으로 롤백 중..."
    kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
    
    Write-Info "롤백 상태 확인 중..."
    kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE
    Write-Success "✓ 롤백 완료"
}

function Get-Pods {
    Write-Info "=== Pod 목록 ==="
    kubectl get pods -n $NAMESPACE -o wide
    
    Write-Info "`n=== Pod 상세 상태 ==="
    kubectl top pods -n $NAMESPACE 2>$null
}

function Describe-Pod {
    if (-not $Option) {
        Write-Info "사용 가능한 Pod 목록:"
        kubectl get pods -n $NAMESPACE --no-headers -o custom-columns=":metadata.name"
        Write-Warning "Pod 이름을 지정해주세요. 예: .\k8s-management.ps1 describe pod-name"
        return
    }
    
    Write-Info "Pod '$Option' 상세 정보:"
    kubectl describe pod $Option -n $NAMESPACE
}

function Exec-Pod {
    if (-not $Option) {
        Write-Info "사용 가능한 Pod 목록:"
        kubectl get pods -n $NAMESPACE --no-headers -o custom-columns=":metadata.name"
        Write-Warning "Pod 이름을 지정해주세요. 예: .\k8s-management.ps1 exec pod-name"
        return
    }
    
    Write-Info "Pod '$Option'에 접속 중... (exit로 종료)"
    kubectl exec -it $Option -n $NAMESPACE -- /bin/bash
}

function Test-Health {
    Write-Info "=== 헬스 체크 ==="
    
    # Pod 상태 확인
    $pods = kubectl get pods -n $NAMESPACE --no-headers -o custom-columns=":metadata.name,:status.phase"
    $runningPods = 0
    $totalPods = 0
    
    foreach ($pod in $pods) {
        $totalPods++
        if ($pod -match "Running") {
            $runningPods++
        }
    }
    
    Write-Info "실행 중인 Pod: $runningPods / $totalPods"
    
    # Service 엔드포인트 확인
    $serviceIP = kubectl get svc $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
    if ($serviceIP) {
        Write-Info "Service IP: $serviceIP"
    }
    
    # NodePort 확인
    $nodePort = kubectl get svc "${DEPLOYMENT}-nodeport" -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>$null
    if ($nodePort) {
        Write-Info "NodePort: $nodePort"
        Write-Info "접속 URL: http://localhost:$nodePort"
    }
    
    Write-Success "✓ 헬스 체크 완료"
}

function Cleanup-Resources {
    Write-Warning "모든 리소스를 삭제하시겠습니까? (y/N)"
    $confirm = Read-Host
    
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Info "리소스 정리 중..."
        kubectl delete namespace $NAMESPACE
        Write-Success "✓ 모든 리소스 삭제 완료"
    } else {
        Write-Info "작업 취소됨"
    }
}

function Setup-Environment {
    Write-Info "=== 초기 환경 설정 ==="
    
    # namespace 생성
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    Write-Success "✓ Namespace 생성"
    
    # Registry secret 생성 (대화형)
    Write-Info "Docker Registry 인증 정보 설정"
    $username = Read-Host "Registry Username"
    $password = Read-Host "Registry Password" -AsSecureString
    $passwordText = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
    
    kubectl create secret docker-registry regcred `
        --docker-server=$REGISTRY `
        --docker-username=$username `
        --docker-password=$passwordText `
        -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    Write-Success "✓ Registry Secret 생성"
    Write-Success "✓ 초기 설정 완료"
}

# 메인 실행 로직
if (-not (Test-Prerequisites)) {
    Write-Error "전제 조건을 만족하지 않습니다. 스크립트를 종료합니다."
    exit 1
}

switch ($Action) {
    "deploy" { Deploy-Application }
    "status" { Get-Status }
    "logs" { Get-Logs }
    "scale" { Scale-Application }
    "restart" { Restart-Application }
    "rollback" { Rollback-Application }
    "pods" { Get-Pods }
    "describe" { Describe-Pod }
    "exec" { Exec-Pod }
    "health" { Test-Health }
    "cleanup" { Cleanup-Resources }
    "setup" { Setup-Environment }
    default { Show-Help }
}

Write-Info "`n=== 작업 완료 ==="
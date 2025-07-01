@echo off
REM Blacklist Windows 배포 스크립트
REM 작성자: Claude
REM 설명: Windows 환경에서 Kubernetes 배포를 위한 배치 스크립트

echo =====================================
echo   Blacklist Kubernetes 배포 스크립트
echo   Windows 환경
echo =====================================
echo.

REM 현재 디렉토리 확인
echo [1/10] 현재 디렉토리: %CD%
echo.

REM k8s 디렉토리 존재 확인
if not exist "k8s" (
    echo [ERROR] k8s 디렉토리를 찾을 수 없습니다!
    echo 프로젝트 루트 디렉토리에서 실행해주세요.
    pause
    exit /b 1
)

echo [2/10] 네임스페이스 생성...
kubectl apply -f k8s/namespace.yaml
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 네임스페이스 생성 실패!
    pause
    exit /b 1
)
echo [OK] 네임스페이스 생성 완료
echo.

echo [3/10] ConfigMap 생성...
kubectl apply -f k8s/configmap.yaml
echo [OK] ConfigMap 생성 완료
echo.

echo [4/10] Secret 생성...
kubectl apply -f k8s/secret.yaml
echo [OK] Secret 생성 완료
echo.

echo [5/10] PVC 생성...
kubectl apply -f k8s/pvc.yaml
if exist "k8s/pvc-instance.yaml" (
    kubectl apply -f k8s/pvc-instance.yaml
)
echo [OK] PVC 생성 완료
echo.

echo [6/10] Redis 배포...
kubectl apply -f k8s/redis.yaml
echo [OK] Redis 배포 완료
echo.

echo [7/10] 메인 애플리케이션 배포...
kubectl apply -f k8s/deployment.yaml
echo [OK] 애플리케이션 배포 완료
echo.

echo [8/10] 서비스 생성...
kubectl apply -f k8s/service.yaml
echo [OK] 서비스 생성 완료
echo.

echo [9/10] Pending 상태 Pod 정리...
kubectl delete pods -n blacklist --field-selector=status.phase=Pending 2>nul
echo [OK] Pending Pod 정리 완료
echo.

echo [10/10] 배포 상태 확인...
echo.
echo === Pod 상태 ===
kubectl get pods -n blacklist
echo.
echo === 서비스 상태 ===
kubectl get services -n blacklist
echo.
echo === PVC 상태 ===
kubectl get pvc -n blacklist
echo.

echo =====================================
echo   배포가 완료되었습니다!
echo =====================================
echo.
echo Pod이 Running 상태가 될 때까지 기다려주세요.
echo 상태 확인: kubectl get pods -n blacklist -w
echo.
pause
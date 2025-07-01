@echo off
REM 클린 배포 스크립트 - 기존 리소스 삭제 후 재배포

echo =====================================
echo   Blacklist 클린 배포 (Windows)
echo   기존 리소스 삭제 후 재배포
echo =====================================
echo.

REM 1. 기존 리소스 삭제
echo [1/3] 기존 리소스 삭제 중...
kubectl delete deployment blacklist -n blacklist 2>nul
kubectl delete deployment blacklist-redis -n blacklist 2>nul
kubectl delete service blacklist -n blacklist 2>nul
kubectl delete service blacklist-nodeport -n blacklist 2>nul
kubectl delete service blacklist-redis -n blacklist 2>nul
kubectl delete pods --all -n blacklist 2>nul
echo [OK] 기존 리소스 삭제 완료
echo.

REM 2. 잠시 대기
echo [2/3] 5초 대기...
timeout /t 5 /nobreak >nul
echo.

REM 3. 새로 배포
echo [3/3] 새로 배포 시작...
echo.

echo 네임스페이스...
kubectl apply -f k8s/namespace.yaml

echo ConfigMap...
kubectl apply -f k8s/configmap.yaml

echo Secret...
kubectl apply -f k8s/secret.yaml

echo PVC...
kubectl apply -f k8s/pvc.yaml

echo Redis...
kubectl apply -f k8s/redis.yaml

echo 메인 앱...
kubectl apply -f k8s/deployment.yaml

echo 서비스...
kubectl apply -f k8s/service.yaml

echo.
echo =====================================
echo   배포 완료! Pod 상태 확인
echo =====================================
kubectl get pods -n blacklist

echo.
echo 실시간 모니터링: kubectl get pods -n blacklist -w
pause
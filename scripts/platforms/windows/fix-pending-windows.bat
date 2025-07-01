@echo off
REM Pending Pod 문제 해결 스크립트

echo =====================================
echo   Pending Pod 문제 해결
echo =====================================
echo.

echo [1/5] 현재 Pod 상태 확인...
kubectl get pods -n blacklist
echo.

echo [2/5] Pending Pod 이벤트 확인...
for /f "tokens=1" %%i in ('kubectl get pods -n blacklist ^| findstr Pending ^| findstr /r "^blacklist"') do (
    echo.
    echo === Pod: %%i ===
    kubectl describe pod %%i -n blacklist | findstr -A 10 "Events:"
)
echo.

echo [3/5] PVC 상태 확인...
kubectl get pvc -n blacklist
echo.

echo [4/5] 노드 리소스 확인...
kubectl get nodes
kubectl describe nodes | findstr -A 5 "Allocated resources:"
echo.

echo [5/5] 해결 방법 적용...
echo.
echo 옵션 1: 레플리카 수 줄이기
echo kubectl scale deployment blacklist --replicas=1 -n blacklist
echo.
echo 옵션 2: 리소스 요구사항 줄이기 (이미 적용됨)
echo.
echo 옵션 3: Pending Pod 삭제 후 재생성
kubectl delete pods -n blacklist --field-selector=status.phase=Pending
echo.
echo 옵션 4: Docker Desktop 리소스 늘리기
echo Docker Desktop 설정에서 CPU/Memory 할당 증가
echo.

pause
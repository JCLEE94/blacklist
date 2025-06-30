# Kubernetes Deployment Guide

## 사전 준비사항

1. Kubernetes 클러스터 (1.24+)
2. kubectl 설치 및 설정
3. Ingress Controller (nginx-ingress)
4. cert-manager (HTTPS 인증서)
5. Private Docker Registry 접근 권한

## 배포 방법

### 1. 네임스페이스 및 리소스 생성

```bash
# 전체 리소스 배포
kubectl apply -k k8s/

# 또는 개별 배포
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/cronjob.yaml
```

### 2. 배포 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n blacklist

# Service 확인
kubectl get svc -n blacklist

# Ingress 확인
kubectl get ingress -n blacklist

# HPA 상태
kubectl get hpa -n blacklist

# 로그 확인
kubectl logs -f deployment/blacklist -n blacklist
```

### 3. 통합 테스트 실행

```bash
# 통합 테스트 Job 실행
kubectl apply -f k8s/test-job.yaml

# 테스트 결과 확인
kubectl logs job/blacklist-integration-test -n blacklist
```

### 4. 수동 배포 (CI/CD 없이)

```bash
# 이미지 빌드 및 푸시
docker build -f deployment/Dockerfile -t registry.jclee.me/blacklist:latest .
docker push registry.jclee.me/blacklist:latest

# 롤링 업데이트
kubectl rollout restart deployment/blacklist -n blacklist

# 롤아웃 상태 확인
kubectl rollout status deployment/blacklist -n blacklist
```

## 주요 기능

### 1. 자동 스케일링 (HPA)
- CPU 70% 이상 시 자동 확장
- 메모리 80% 이상 시 자동 확장
- 최소 2개, 최대 10개 Pod

### 2. Health Check
- Liveness Probe: /health (30초 간격)
- Readiness Probe: /health (10초 간격)

### 3. 일일 자동 수집 (CronJob)
- 매일 새벽 2시 (UTC) 자동 실행
- REGTECH, SECUDIUM 순차 수집

### 4. 데이터 영속성
- PVC로 데이터 보존
- Pod 재시작 시에도 데이터 유지

## 모니터링

```bash
# Pod 리소스 사용량
kubectl top pods -n blacklist

# 실시간 로그
kubectl logs -f deployment/blacklist -n blacklist --tail=100

# 이벤트 확인
kubectl get events -n blacklist --sort-by='.lastTimestamp'
```

## 트러블슈팅

### 1. Pod가 시작되지 않는 경우
```bash
kubectl describe pod <pod-name> -n blacklist
```

### 2. 수집 기능 오류
```bash
# Pod 내부 접속
kubectl exec -it deployment/blacklist -n blacklist -- /bin/bash

# 환경 변수 확인
env | grep REGTECH
```

### 3. 롤백
```bash
kubectl rollout undo deployment/blacklist -n blacklist
```

## 보안 고려사항

1. Secret은 실제 환경에서 Sealed Secrets 또는 외부 Secret Manager 사용
2. NetworkPolicy로 Pod 간 통신 제한
3. RBAC로 권한 관리
4. Pod Security Standards 적용
# CI/CD Pipeline Guide

## Overview

간소화되고 실용적인 CI/CD 파이프라인입니다. Kubernetes의 핵심 기능을 활용하면서도 복잡성을 최소화했습니다.

## Workflows

### 1. Main Pipeline (`main.yml`)
- **트리거**: main/develop 브랜치 푸시, PR
- **단계**: 
  1. 테스트 실행
  2. Docker 이미지 빌드 및 푸시
  3. 프로덕션 자동 배포 (main 브랜치만)

### 2. Staging 배포 (`deploy-staging.yml`)
- **트리거**: develop 브랜치 푸시, 수동
- **특징**: 자동 스모크 테스트 포함

### 3. Production 배포 (`deploy-production.yml`)
- **트리거**: 수동 (workflow_dispatch)
- **배포 전략**:
  - Rolling Update (기본)
  - Blue-Green
  - Canary
- **특징**: 배포 전 이미지 검증, 롤백 계획 생성

### 4. Security 스캔 (`security-scan.yml`)
- **트리거**: 매일 자동, PR (의존성 변경 시)
- **검사 항목**:
  - Python 의존성 취약점
  - 코드 보안 이슈 (Bandit)
  - 컨테이너 이미지 스캔 (Trivy)

### 5. 리소스 정리 (`cleanup.yml`)
- **트리거**: 매주 일요일 자동
- **정리 대상**:
  - 오래된 Docker 이미지
  - 완료된 Jobs
  - 실패한 Pods

### 6. 수동 롤백 (`manual-rollback.yml`)
- **트리거**: 수동
- **옵션**: 특정 리비전 또는 이전 버전으로 롤백

## 배포 방법

### 자동 배포
```bash
# main 브랜치에 푸시하면 자동으로 프로덕션 배포
git push origin main

# develop 브랜치에 푸시하면 스테이징 배포
git push origin develop
```

### 수동 배포
```bash
# 간단한 배포 스크립트 사용
./scripts/simple-deploy.sh production deploy
./scripts/simple-deploy.sh staging deploy
./scripts/simple-deploy.sh development deploy

# 상태 확인
./scripts/simple-deploy.sh production status

# 헬스 체크
./scripts/simple-deploy.sh production health

# 롤백
./scripts/simple-deploy.sh production rollback
```

### GitHub UI에서 수동 배포
1. Actions 탭 → Deploy to Production
2. Run workflow 클릭
3. 이미지 태그와 배포 전략 선택
4. Run workflow 실행

## 환경 구성

### Development
- **네임스페이스**: blacklist-dev
- **리소스**: 최소 (테스트용)
- **자동 배포**: 없음 (수동만)

### Staging  
- **네임스페이스**: blacklist-staging
- **리소스**: 중간
- **자동 배포**: develop 브랜치 푸시 시

### Production
- **네임스페이스**: blacklist
- **리소스**: 최대
- **자동 배포**: main 브랜치 푸시 시

## 필수 GitHub Secrets

```yaml
DOCKER_AUTH_CONFIG    # Docker 레지스트리 인증 정보
REGISTRY_USERNAME     # 레지스트리 사용자명 (_token)
REGISTRY_PASSWORD     # 레지스트리 패스워드
REGTECH_USERNAME      # REGTECH 사용자명
REGTECH_PASSWORD      # REGTECH 패스워드
SECUDIUM_USERNAME     # SECUDIUM 사용자명
SECUDIUM_PASSWORD     # SECUDIUM 패스워드
```

## 배포 전략 상세

### Rolling Update
- 기본 전략
- 점진적으로 Pod 교체
- 무중단 배포

### Blue-Green
- 두 개의 완전한 환경 운영
- 즉시 전환 가능
- 빠른 롤백

### Canary
- 새 버전을 일부 트래픽에만 노출
- 5분간 모니터링
- 오류 감지 시 자동 롤백

## 트러블슈팅

### 배포 실패 시
```bash
# 로그 확인
kubectl logs -l app=blacklist -n blacklist --tail=50

# 이벤트 확인
kubectl get events -n blacklist --sort-by='.lastTimestamp'

# 수동 롤백
./scripts/simple-deploy.sh production rollback
```

### 이미지 풀 실패
```bash
# Docker 인증 확인
kubectl get secret regcred -n blacklist -o yaml

# Secret 재생성
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=_token \
  --docker-password=$REGISTRY_PASSWORD \
  -n blacklist
```

### 헬스 체크 실패
```bash
# Pod에 직접 접속
kubectl exec -it deployment/blacklist -n blacklist -- /bin/sh

# 로컬에서 테스트
kubectl port-forward svc/blacklist 8541:8541 -n blacklist
curl http://localhost:8541/health
```

## 모니터링

```bash
# 실시간 로그 확인
kubectl logs -f deployment/blacklist -n blacklist

# 리소스 사용량
kubectl top pods -n blacklist

# HPA 상태
kubectl get hpa -n blacklist -w
```

## 베스트 프랙티스

1. **이미지 태그**: 항상 구체적인 태그 사용 (latest 지양)
2. **테스트**: 배포 전 로컬 테스트 필수
3. **단계적 배포**: dev → staging → production
4. **모니터링**: 배포 후 최소 10분간 모니터링
5. **문서화**: 변경사항 README 업데이트

## 자주 사용하는 명령어

```bash
# 빠른 배포
./scripts/simple-deploy.sh production

# 특정 이미지로 배포
IMAGE_TAG=v1.2.3 ./scripts/simple-deploy.sh production

# 전체 상태 확인
for env in development staging production; do
  echo "=== $env ==="
  ./scripts/simple-deploy.sh $env status
done

# 모든 환경 헬스 체크
for env in development staging production; do
  ./scripts/simple-deploy.sh $env health
done
```
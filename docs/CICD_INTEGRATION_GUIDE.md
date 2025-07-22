# CI/CD Integration Guide

## 개요

이 가이드는 Docker Registry(registry.jclee.me)와 Helm Repository(charts.jclee.me)를 사용한 완전한 CI/CD 파이프라인 설정을 설명합니다.

## 인증 정보

### Docker Registry
- **URL**: `https://registry.jclee.me`
- **Username**: `admin`
- **Password**: `bingogo1`
- **Basic Auth**: `Authorization: Basic YWRtaW46YmluZ29nbzE=`

### ChartMuseum (Helm Repository)
- **URL**: `https://charts.jclee.me`
- **Username**: `admin`
- **Password**: `bingogo1`
- **Basic Auth**: `Authorization: Basic YWRtaW46YmluZ29nbzE=`

### ArgoCD
- **URL**: `https://argo.jclee.me`
- **Username**: `admin`
- **Password**: `bingogo1`

## GitHub Secrets 설정

다음 secrets를 GitHub 저장소에 추가하세요:

```bash
# GitHub CLI 사용
gh secret set DOCKER_REGISTRY_USER -b "admin"
gh secret set DOCKER_REGISTRY_PASS -b "bingogo1"
gh secret set HELM_REPO_USERNAME -b "admin"
gh secret set HELM_REPO_PASSWORD -b "bingogo1"
```

## 로컬 개발 환경 설정

1. 환경 변수 파일 생성:
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

2. 환경 변수 로드:
```bash
source .env
```

## 인증 테스트

```bash
# 모든 서비스 인증 테스트
./scripts/test-auth-services.sh
```

## 배포 프로세스

### 자동 배포 (CI/CD)
1. 코드를 main 브랜치에 push
2. GitHub Actions가 자동으로:
   - Docker 이미지 빌드 및 registry.jclee.me에 푸시
   - Helm 차트 패키징 및 charts.jclee.me에 푸시
3. ArgoCD가 자동으로 새 버전 감지 및 배포

### 수동 배포
```bash
# 통합 배포 스크립트 사용
./scripts/integrated-deployment.sh [version]

# 예시
./scripts/integrated-deployment.sh v1.0.0
./scripts/integrated-deployment.sh latest
```

## Docker 명령어

### 로그인
```bash
docker login registry.jclee.me -u admin -p bingogo1
```

### 이미지 빌드 및 푸시
```bash
# 빌드
docker build -f deployment/Dockerfile -t registry.jclee.me/blacklist:latest .

# 푸시
docker push registry.jclee.me/blacklist:latest
```

### 이미지 목록 확인
```bash
curl -u admin:bingogo1 https://registry.jclee.me/v2/_catalog | jq .
```

## Helm 명령어

### Repository 추가
```bash
helm repo add jclee-charts https://charts.jclee.me \
  --username admin --password bingogo1
helm repo update
```

### Chart 패키징 및 푸시
```bash
# 패키징
helm package helm/blacklist

# 푸시
curl --data-binary "@blacklist-1.0.0.tgz" \
  -u admin:bingogo1 \
  https://charts.jclee.me/api/charts
```

### Chart 설치
```bash
helm install blacklist jclee-charts/blacklist \
  --set image.repository=registry.jclee.me/blacklist \
  --set image.tag=latest
```

## ArgoCD 명령어

### 로그인
```bash
argocd login argo.jclee.me \
  --username admin \
  --password bingogo1 \
  --grpc-web
```

### 애플리케이션 상태 확인
```bash
argocd app get blacklist
argocd app sync blacklist
```

## 문제 해결

### Registry 연결 실패
```bash
# TLS 인증서 확인
curl -v https://registry.jclee.me/v2/

# 인증 테스트
curl -u admin:bingogo1 https://registry.jclee.me/v2/_catalog
```

### Helm 차트 푸시 실패
```bash
# ChartMuseum 상태 확인
curl https://charts.jclee.me/health

# API 엔드포인트 테스트
curl -u admin:bingogo1 https://charts.jclee.me/api/charts
```

### ArgoCD 동기화 실패
```bash
# 애플리케이션 새로고침
argocd app refresh blacklist

# 강제 동기화
argocd app sync blacklist --force
```

## 모니터링

### 애플리케이션 상태
```bash
kubectl get all -n blacklist
kubectl logs -f deployment/blacklist -n blacklist
```

### 헬스 체크
```bash
curl http://localhost:32452/health
```

## 보안 권장사항

1. **프로덕션 환경**에서는 더 강력한 패스워드 사용
2. **RBAC** 설정으로 접근 권한 제한
3. **네트워크 정책**으로 트래픽 제한
4. **시크릿 관리 도구** (Vault, Sealed Secrets) 사용
5. **정기적인 패스워드 변경**

## 참고 문서

- [Docker Registry API](https://docs.docker.com/registry/spec/api/)
- [ChartMuseum API](https://github.com/helm/chartmuseum#api)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Helm Documentation](https://helm.sh/docs/)
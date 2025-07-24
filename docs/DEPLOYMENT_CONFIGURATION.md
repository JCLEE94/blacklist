# 배포 설정 가이드

## 개요

이 프로젝트는 환경별 설정을 통한 유연한 배포 시스템을 제공합니다. 하드코딩된 값들을 제거하고 환경 변수와 템플릿을 사용하여 다양한 환경에 쉽게 배포할 수 있습니다.

## 디렉토리 구조

```
config/
├── deployment-template.yaml     # 중앙 집중식 설정 템플릿
├── environments/               # 환경별 설정 파일
│   ├── dev.env                # 개발 환경 설정
│   ├── staging.env            # 스테이징 환경 설정 (선택사항)
│   └── prod.env               # 프로덕션 환경 설정
└── backups/                   # 설정 백업 (자동 생성)

scripts/
├── config-manager.sh          # 설정 관리 스크립트
├── universal-deploy.sh        # 통합 배포 스크립트
├── deploy.sh.template         # 배포 스크립트 템플릿
└── deploy.sh                  # 기존 배포 스크립트

k8s/
├── *.yaml.template           # Kubernetes 리소스 템플릿
└── rendered/                 # 렌더링된 파일 (자동 생성)
    ├── dev/
    ├── staging/
    └── prod/

argocd/
├── application.yaml.template # ArgoCD 애플리케이션 템플릿
└── rendered/                # 렌더링된 파일 (자동 생성)
```

## 환경 설정

### 1. 환경 변수 설정

각 환경에 맞는 설정 파일을 편집합니다:

#### 개발 환경 (`config/environments/dev.env`)
```bash
BASE_DOMAIN=localhost:8541
REGISTRY_URL=localhost:5000
HELM_REPOSITORY=http://localhost:8080/charts
ENVIRONMENT=development
```

#### 프로덕션 환경 (`config/environments/prod.env`)
```bash
BASE_DOMAIN=your-domain.com
REGISTRY_URL=registry.your-domain.com
HELM_REPOSITORY=https://charts.your-domain.com
ENVIRONMENT=production
```

### 2. 필수 환경 변수

모든 환경에서 설정해야 하는 필수 변수들:

```bash
# 기본 프로젝트 설정
PROJECT_NAME=blacklist
BASE_DOMAIN=your-domain.com
REGISTRY_URL=registry.your-domain.com

# Git 설정
GIT_REPOSITORY=https://github.com/your-org/blacklist.git
GIT_USERNAME=your-username
GIT_EMAIL=your-email@domain.com

# 보안 설정 (Kubernetes Secret으로 관리 권장)
REGTECH_USERNAME=your-regtech-username
REGTECH_PASSWORD=your-regtech-password
SECUDIUM_USERNAME=your-secudium-username
SECUDIUM_PASSWORD=your-secudium-password
JWT_SECRET_KEY=your-jwt-secret
API_SECRET_KEY=your-api-secret
```

## 사용 방법

### 1. 설정 관리

```bash
# 설정 검증
./scripts/config-manager.sh validate prod

# 환경 초기화
./scripts/config-manager.sh init prod

# 템플릿 렌더링
./scripts/config-manager.sh render prod k8s/service.yaml.template

# 사용 가능한 환경 목록
./scripts/config-manager.sh list

# 설정 백업
./scripts/config-manager.sh backup prod

# 설정 복원
./scripts/config-manager.sh restore prod backup_20250723_120000.tar.gz
```

### 2. 통합 배포

```bash
# 프로덕션 배포
./scripts/universal-deploy.sh prod

# 개발 환경 배포 (시뮬레이션)
./scripts/universal-deploy.sh dev --dry-run

# 설정 검증만 수행
./scripts/universal-deploy.sh staging --config-only

# 이미지 빌드 건너뛰기
./scripts/universal-deploy.sh prod --skip-build

# 도움말
./scripts/universal-deploy.sh --help
```

### 3. 기존 스크립트 업데이트

기존 스크립트를 환경별 설정으로 업데이트:

```bash
# 기존 deploy.sh를 템플릿으로 교체
cp scripts/deploy.sh.template scripts/deploy.sh

# 환경 변수 설정 후 실행
ENVIRONMENT=prod ./scripts/deploy.sh
```

## 마이그레이션 가이드

### 현재 하드코딩된 환경을 새 시스템으로 마이그레이션

1. **현재 설정 백업**
```bash
cp -r k8s k8s.backup
cp -r argocd argocd.backup
```

2. **환경 설정 파일 생성**
```bash
# 프로덕션 환경 설정 편집
vim config/environments/prod.env

# 실제 값들로 수정:
# - jclee.me → your-domain.com
# - registry.jclee.me → registry.your-domain.com
# - 192.168.50.110 → your-remote-server-ip
```

3. **설정 검증**
```bash
./scripts/config-manager.sh validate prod
```

4. **초기화 및 테스트**
```bash
# 환경 초기화
./scripts/config-manager.sh init prod

# DRY RUN으로 테스트
./scripts/universal-deploy.sh prod --dry-run
```

5. **실제 배포**
```bash
./scripts/universal-deploy.sh prod
```

## 보안 고려사항

### 1. 민감한 정보 관리

환경 설정 파일에 있는 민감한 정보는 Kubernetes Secret으로 관리하는 것을 권장합니다:

```bash
# Secret 생성 (자동화됨)
kubectl create secret generic blacklist-secret \
  --from-literal=REGTECH_USERNAME="$REGTECH_USERNAME" \
  --from-literal=REGTECH_PASSWORD="$REGTECH_PASSWORD" \
  --namespace=blacklist
```

### 2. Git 보안

민감한 환경 설정 파일은 `.gitignore`에 추가:

```gitignore
# 환경별 보안 설정 (선택사항)
config/environments/prod.env
config/environments/staging.env
```

## 트러블슈팅

### 1. 템플릿 렌더링 오류

```bash
# envsubst 설치 확인
which envsubst || sudo apt-get install gettext-base

# 환경 변수 확인
env | grep -E "(BASE_DOMAIN|REGISTRY_URL|PROJECT_NAME)"
```

### 2. ArgoCD 배포 실패

```bash
# ArgoCD 네임스페이스 확인
kubectl get namespace argocd

# ArgoCD 애플리케이션 상태 확인
argocd app get blacklist --grpc-web

# 수동 동기화
argocd app sync blacklist --force --grpc-web
```

### 3. Docker 이미지 빌드 실패

```bash
# Docker 상태 확인
docker info

# 레지스트리 연결 확인
docker login registry.your-domain.com
```

## 추가 자료

- [ArgoCD 공식 문서](https://argo-cd.readthedocs.io/)
- [Kubernetes 환경 변수 가이드](https://kubernetes.io/docs/tasks/inject-data-application/define-environment-variable-container/)
- [Helm 차트 베스트 프랙티스](https://helm.sh/docs/chart_best_practices/)

## FAQ

**Q: 기존 하드코딩된 설정이 여전히 작동하나요?**
A: 네, 기존 설정은 백워드 호환성을 위해 유지됩니다. 하지만 새로운 템플릿 시스템 사용을 권장합니다.

**Q: 여러 클러스터에 동시 배포할 수 있나요?**
A: 네, 각 클러스터에 대해 별도의 환경 설정을 만들고 병렬로 배포할 수 있습니다.

**Q: CI/CD 파이프라인에서 어떻게 사용하나요?**
A: 환경별 설정을 GitHub Secrets로 설정하고 워크플로우에서 해당 환경을 선택하여 배포합니다.
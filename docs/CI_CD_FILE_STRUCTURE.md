# CI/CD 파일 구조 정리 현황

## 정리 완료 (2025-01-15)

### 1. GitHub Actions Workflows
**현재 활성 파일:**
- `.github/workflows/gitops-pipeline.yml` - 통합된 메인 GitOps 파이프라인

**아카이브된 파일:**
- `archive/workflows/` - 이전 버전의 워크플로우 파일들

### 2. ArgoCD 설정
**현재 활성 파일:**
- `k8s/argocd-app-helm.yaml` - Helm 기반 ArgoCD Application
- `k8s/argocd-image-updater-config.yaml` - Image Updater 설정
- `k8s/argocd-health-override.yaml` - Health check 커스터마이징

**아카이브된 파일:**
- `archive/argocd-configs/` - Kustomize 기반 이전 설정들
  - argocd-app-blacklist.yaml
  - argocd-app-clean.yaml
  - argocd-app-helm-git.yaml
  - argocd-app-override.yaml
  - argocd-app-production.yaml
  - argocd-app-staging.yaml
  - argocd-app.yaml

### 3. 배포 스크립트
**현재 활성 스크립트:**
- `scripts/k8s-management.sh` - ArgoCD 통합 관리 도구
- `scripts/deploy.sh` - 간단한 배포 스크립트
- `scripts/multi-deploy.sh` - 멀티 서버 배포
- `scripts/all-clusters-deploy.sh` - 전체 클러스터 배포
- `scripts/unified-deploy.sh` - 플랫폼 무관 통합 배포

**설정 스크립트:**
- `scripts/setup/argocd-complete-setup.sh` - ArgoCD 완전 자동화 설정
- `scripts/setup/argocd-cli-setup.sh` - ArgoCD CLI 설치
- `scripts/setup/argocd-github-access.sh` - GitHub 연동 설정

### 4. Helm Charts
**활성 차트:**
- `charts/blacklist/` - 메인 Helm 차트
  - `Chart.yaml` - 차트 메타데이터
  - `values.yaml` - 기본 설정값
  - `templates/` - Kubernetes 리소스 템플릿

### 5. Docker 관련
**활성 파일:**
- `deployment/Dockerfile` - 메인 컨테이너 이미지
- `deployment/docker-compose.yml` - 로컬 개발용

### 6. Kubernetes 매니페스트
**활성 구조:**
- `k8s/base/` - Kustomize base (레거시, 참조용)
- `k8s/overlays/` - 환경별 설정 (레거시, 참조용)
- ArgoCD가 Helm 차트를 사용하므로 직접 사용되지 않음

## 파이프라인 흐름

1. **코드 푸시** → GitHub Actions 트리거
2. **품질 검사** → Linting, Security scan
3. **테스트** → Unit tests, Integration tests
4. **Docker 빌드** → registry.jclee.me에 푸시
5. **Helm Chart** → ChartMuseum에 업로드
6. **ArgoCD 동기화** → 자동 배포

## 주요 통합 포인트

- **Docker Registry**: `registry.jclee.me` (인증 필요)
- **Helm Repository**: `https://charts.jclee.me` (ChartMuseum)
- **ArgoCD Server**: `https://argo.jclee.me`
- **Production URL**: `https://blacklist.jclee.me`

## 정리 효과

- 중복 파일 제거로 관리 포인트 단순화
- GitOps 워크플로우 명확화
- Helm 중심의 배포 표준화
- 자동화 수준 향상
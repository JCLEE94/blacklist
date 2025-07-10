# ArgoCD 설정 가이드

이 문서는 ArgoCD CLI를 사용하여 Blacklist 애플리케이션의 GitOps 배포를 설정하는 방법을 설명합니다.

## 📋 사전 요구사항

1. **Kubernetes 클러스터**
   - kubectl이 설치되고 클러스터에 연결되어 있어야 함
   - 충분한 권한 (namespace, deployment 생성 등)

2. **GitHub 설정**
   - GitHub Personal Access Token (read:packages, write:packages 권한)
   - GitHub Actions Secrets 설정 완료

3. **환경 변수**
   ```bash
   # .env 파일 설정
   cp .env.example .env
   nano .env
   
   # 환경 변수 로드
   source scripts/load-env.sh
   ```

## 🚀 빠른 시작

### 1단계: ArgoCD 설치 및 설정

```bash
# ArgoCD CLI 기반 전체 설정
./scripts/setup/argocd-cli-setup.sh
```

이 스크립트는 다음을 수행합니다:
- ArgoCD CLI 설치
- ArgoCD 서버 설치 (필요한 경우)
- 서버 로그인 및 인증
- GitHub Repository 연결
- Application 생성
- Image Updater 설정
- 초기 동기화

### 2단계: GHCR 시크릿 설정

```bash
# GitHub Container Registry 시크릿 생성
export GITHUB_USERNAME="your-github-username"
export GITHUB_TOKEN="your-personal-access-token"
./scripts/setup-ghcr-secret.sh
```

### 3단계: GitHub Actions Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions에서 다음 시크릿 추가:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `KUBE_CONFIG` | base64 인코딩된 kubeconfig | `cat ~/.kube/config \| base64` |
| `ARGOCD_SERVER` | ArgoCD 서버 주소 | `argo.jclee.me` |
| `ARGOCD_AUTH_TOKEN` | ArgoCD 인증 토큰 | 아래 명령으로 생성 |

#### ArgoCD 인증 토큰 생성:
```bash
# ArgoCD 로그인
argocd login argo.jclee.me --username admin --grpc-web

# 토큰 생성
argocd account generate-token --account admin --grpc-web
```

## 🔧 수동 설정

### ArgoCD CLI 설치

```bash
# 최신 버전 다운로드
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64

# 설치
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64

# 버전 확인
argocd version --client
```

### ArgoCD 서버 설치

```bash
# 네임스페이스 생성
kubectl create namespace argocd

# ArgoCD 설치
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 설치 확인
kubectl get all -n argocd
```

### ArgoCD 초기 비밀번호 확인

```bash
# 초기 admin 비밀번호
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Application 생성 (CLI)

```bash
# 로그인
argocd login argo.jclee.me --username admin --grpc-web

# Repository 추가
argocd repo add https://github.com/JCLEE94/blacklist.git --grpc-web

# Application 생성
argocd app create blacklist \
  --repo https://github.com/JCLEE94/blacklist.git \
  --path k8s \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace blacklist \
  --revision main \
  --sync-policy automated \
  --self-heal \
  --auto-prune \
  --grpc-web

# 동기화
argocd app sync blacklist --grpc-web
```

## 📊 모니터링 및 관리

### ArgoCD CLI 명령어

```bash
# 애플리케이션 목록
argocd app list --grpc-web

# 애플리케이션 상태
argocd app get blacklist --grpc-web

# 수동 동기화
argocd app sync blacklist --grpc-web

# 히스토리 확인
argocd app history blacklist --grpc-web

# 롤백
argocd app rollback blacklist <revision> --grpc-web

# 로그 확인
argocd app logs blacklist --grpc-web

# 리소스 확인
argocd app resources blacklist --grpc-web
```

### 웹 UI 접속

1. 브라우저에서 https://argo.jclee.me 접속
2. Username: `admin`
3. Password: 초기 비밀번호 또는 변경한 비밀번호

## 🔄 Image Updater 설정

ArgoCD Image Updater는 자동으로 새 이미지를 감지하고 배포합니다.

### 설정 확인

```bash
# Image Updater 로그 확인
kubectl logs -n argocd deployment/argocd-image-updater -f

# Application 어노테이션 확인
kubectl get application blacklist -n argocd -o yaml | grep -A 5 annotations
```

### 수동 이미지 업데이트

```bash
# Kustomize를 사용한 이미지 업데이트
cd k8s
kustomize edit set image ghcr.io/jclee94/blacklist:latest=ghcr.io/jclee94/blacklist:v1.2.3
git add . && git commit -m "chore: update image to v1.2.3"
git push
```

## 🚨 문제 해결

### ArgoCD 서버 접속 불가

```bash
# 포트 포워딩 사용
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 로컬에서 접속
argocd login localhost:8080 --username admin --insecure
```

### 동기화 실패

```bash
# 상태 확인
argocd app get blacklist --grpc-web

# 이벤트 확인
kubectl get events -n blacklist --sort-by='.lastTimestamp'

# 강제 동기화
argocd app sync blacklist --force --grpc-web
```

### Image Updater 문제

```bash
# Image Updater 재시작
kubectl rollout restart deployment/argocd-image-updater -n argocd

# 시크릿 확인
kubectl get secret ghcr-secret -n blacklist
```

## 📚 참고 자료

- [ArgoCD 공식 문서](https://argo-cd.readthedocs.io/)
- [ArgoCD CLI 참조](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd/)
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/)
- [Kustomize 문서](https://kustomize.io/)
# Self-hosted Runner 가이드

## 🏃 개요

이 프로젝트는 GitHub Actions에서 self-hosted runner를 사용하여 CI/CD 파이프라인을 실행합니다.

## 🔧 Self-hosted Runner 설정

### 1. Runner 요구사항

- **OS**: Ubuntu 20.04 이상 (권장)
- **Docker**: 설치 및 실행 중
- **kubectl**: Kubernetes 클러스터 접근 가능
- **권한**: Docker 및 Kubernetes 명령 실행 권한

### 2. Runner 설치

```bash
# GitHub에서 runner 다운로드 (Settings > Actions > Runners)
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Runner 설정
./config.sh --url https://github.com/JCLEE94/blacklist --token YOUR_TOKEN

# 서비스로 설치
sudo ./svc.sh install
sudo ./svc.sh start
```

### 3. Runner 라벨 설정

워크플로우에서 사용하는 라벨:
- `self-hosted`
- `linux` (선택사항)
- `x64` (선택사항)

## 📋 워크플로우 호환성

### GitHub Actions 버전 제약사항

self-hosted runner 환경에서는 특정 버전의 actions를 사용해야 합니다:

```yaml
# ✅ 호환 가능한 버전
- uses: actions/checkout@v3         # NOT v4
- uses: docker/setup-buildx-action@v2  # NOT v3
- uses: docker/build-push-action@v4    # NOT v5

# ❌ 호환되지 않는 버전
- uses: actions/checkout@v4         # 최신 버전은 오류 발생 가능
```

### 필수 도구 설치

Runner가 실행되는 시스템에 다음 도구들이 설치되어 있어야 합니다:

```bash
# Docker
sudo apt-get update
sudo apt-get install docker.io
sudo usermod -aG docker $USER

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Python (구문 체크용)
sudo apt-get install python3 python3-pip

# Git
sudo apt-get install git
```

## 🔐 보안 설정

### 1. Docker Registry 인증

Runner가 private registry에 접근할 수 있도록 설정:

```bash
# Docker 로그인
docker login registry.jclee.me -u USERNAME -p PASSWORD

# 인증 정보가 ~/.docker/config.json에 저장됨
```

### 2. Kubernetes 접근

Runner가 Kubernetes 클러스터에 접근할 수 있도록 kubeconfig 설정:

```bash
# kubeconfig 복사
mkdir -p ~/.kube
cp /path/to/kubeconfig ~/.kube/config

# 권한 확인
kubectl get nodes
```

### 3. GitHub Secrets

워크플로우에서 사용하는 secrets:
- `DOCKER_USERNAME`: Docker Registry 사용자명
- `DOCKER_PASSWORD`: Docker Registry 비밀번호
- `DEPLOYMENT_WEBHOOK_URL`: (선택사항) 배포 알림 웹훅

## 🚨 일반적인 문제 해결

### 1. Docker 권한 오류

```bash
# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인
```

### 2. kubectl 권한 오류

```bash
# kubeconfig 권한 확인
chmod 600 ~/.kube/config
```

### 3. Runner 오프라인

```bash
# Runner 서비스 상태 확인
sudo ./svc.sh status

# 서비스 재시작
sudo ./svc.sh stop
sudo ./svc.sh start
```

### 4. 디스크 공간 부족

```bash
# Docker 이미지 정리
docker system prune -a -f

# 오래된 빌드 캐시 정리
docker builder prune -f
```

## 📊 모니터링

### Runner 상태 확인

GitHub Repository Settings > Actions > Runners에서 확인 가능

### 로그 확인

```bash
# Runner 서비스 로그
journalctl -u actions.runner.JCLEE94-blacklist.runner-name -f

# 작업 디렉토리
cd /home/runner/actions-runner/_work/blacklist/blacklist
```

## 🔄 업데이트

### Runner 업데이트

1. GitHub에서 새 버전 알림 확인
2. 서비스 중지: `sudo ./svc.sh stop`
3. 새 버전 다운로드 및 설치
4. 서비스 시작: `sudo ./svc.sh start`

### 워크플로우 수정 시 주의사항

- Action 버전 변경 시 호환성 테스트 필수
- self-hosted 환경의 제약사항 고려
- 로컬 테스트 후 적용

## 📞 지원

문제 발생 시:
1. Runner 로그 확인
2. GitHub Actions 로그 확인
3. 시스템 리소스 확인 (CPU, 메모리, 디스크)
4. 네트워크 연결 상태 확인
# GitHub Secrets 설정 가이드

GitHub Actions CI/CD 파이프라인을 위해 다음 Secrets를 설정해야 합니다.

## 설정 방법
1. GitHub 저장소로 이동: https://github.com/qws941/blacklist-management
2. Settings → Secrets and variables → Actions 클릭
3. "New repository secret" 버튼 클릭
4. 아래 각 Secret 추가

## 필수 Secrets

### REGISTRY_USERNAME
- **값**: `qws941`
- **설명**: Docker Registry (registry.jclee.me) 사용자명

### REGISTRY_PASSWORD  
- **값**: `bingogo1l7!`
- **설명**: Docker Registry 비밀번호

### DEPLOY_USER
- **값**: `docker`
- **설명**: 배포 서버 SSH 사용자명

### DEPLOY_HOST
- **값**: `registry.jclee.me`
- **설명**: 배포 서버 호스트 주소

### DEPLOY_PORT
- **값**: `1112`
- **설명**: 배포 서버 SSH 포트

### DEPLOY_SSH_KEY
- **값**: SSH 개인키 내용 (전체 복사)
- **설명**: 배포 서버 접속용 SSH 개인키
- **생성 방법**:
  ```bash
  # 로컬에서 실행
  cat ~/.ssh/id_rsa  # 또는 사용하는 개인키 경로
  ```

## 선택적 Secrets

### GRAFANA_PASSWORD
- **값**: 원하는 Grafana 관리자 비밀번호
- **설명**: Grafana 모니터링 대시보드 비밀번호 (선택사항)

## 테스트 방법

모든 Secrets 설정 후:

1. 새 브랜치 생성:
   ```bash
   git checkout -b test-cicd
   ```

2. 작은 변경사항 추가:
   ```bash
   echo "# CI/CD Test" >> README.md
   git add README.md
   git commit -m "test: CI/CD pipeline"
   git push origin test-cicd
   ```

3. Pull Request 생성하여 CI/CD 실행 확인

## 트러블슈팅

- **권한 오류**: DEPLOY_SSH_KEY가 올바른지 확인
- **레지스트리 오류**: REGISTRY_USERNAME/PASSWORD 확인
- **연결 오류**: DEPLOY_HOST/PORT가 정확한지 확인
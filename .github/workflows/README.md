# GitHub Actions CI/CD Setup

## Required GitHub Secrets

GitHub 저장소의 Settings → Secrets and variables → Actions에서 다음 secrets를 추가해야 합니다:

### Docker Hub (선택사항)
- `DOCKER_USERNAME`: Docker Hub 사용자명 (예: qws941)
- `DOCKER_PASSWORD`: Docker Hub 비밀번호

### Private Registry (필수)
- `REGISTRY_USERNAME`: registry.jclee.me 사용자명 (예: qws941)
- `REGISTRY_PASSWORD`: registry.jclee.me 비밀번호

### SSH Deployment (필수)
- `DEPLOY_SSH_KEY`: 배포 서버 SSH 개인키

## 설정 방법

```bash
# GitHub CLI 사용
gh secret set REGISTRY_USERNAME -b "qws941"
gh secret set REGISTRY_PASSWORD -b "your-password"
gh secret set DOCKER_USERNAME -b "qws941" 
gh secret set DOCKER_PASSWORD -b "your-password"

# SSH 키 설정
gh secret set DEPLOY_SSH_KEY < ~/.ssh/deploy_key
```

## 워크플로우 설명

1. **Test Stage**: Python 환경에서 설정 검증 및 앱 시작 테스트
2. **Build Stage**: Docker 이미지 빌드 및 registry.jclee.me로 푸시
3. **Deploy Stage**: SSH로 운영 서버에 배포 (main 브랜치만)
4. **Verify Stage**: 배포 후 헬스체크
5. **Notify Stage**: 최종 결과 알림

## Watchtower 통합

운영 서버의 Watchtower가 자동으로 새 이미지를 감지하고 업데이트합니다.
- 폴링 간격: 30초
- 스코프: registry.jclee.me
- 라벨: com.centurylinklabs.watchtower.enable=true

## 브랜치 전략

- `main`: 운영 배포 (자동)
- `develop`: 개발 환경 (빌드만)
- Pull Request: 테스트만 실행
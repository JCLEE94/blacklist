# GitHub Container Registry (GHCR) Migration Guide

## 개요

이 문서는 기존의 사설 레지스트리(`registry.jclee.me`)에서 GitHub Container Registry(GHCR)로 마이그레이션하는 과정을 설명합니다.

## 주요 변경사항

### 1. 레지스트리 URL 변경
- **기존**: `registry.jclee.me/blacklist`
- **신규**: `ghcr.io/jclee94/blacklist`

### 2. 인증 방식 변경
- **기존**: 사용자명/비밀번호 기반 인증
- **신규**: GitHub Personal Access Token (PAT) 기반 인증

### 3. 이미지 풀 시크릿 변경
- **기존**: `regcred`
- **신규**: `ghcr-secret`

## 마이그레이션 단계

### 1단계: GitHub Personal Access Token 생성

1. GitHub 설정 → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 다음 권한 선택:
   - `read:packages` - 패키지 읽기
   - `write:packages` - 패키지 쓰기
   - `delete:packages` - 패키지 삭제 (선택사항)
4. 토큰 생성 및 안전한 곳에 저장

### 2단계: GHCR 시크릿 설정

```bash
# 환경 변수 설정
export GITHUB_USERNAME="your-github-username"
export GITHUB_TOKEN="your-personal-access-token"

# GHCR 시크릿 생성 스크립트 실행
./scripts/setup-ghcr-secret.sh
```

### 3단계: GitHub Actions 시크릿 설정

GitHub 저장소 Settings → Secrets and variables → Actions에서 다음 시크릿 추가:

- `KUBE_CONFIG`: Kubernetes 클러스터 접근을 위한 kubeconfig (base64 인코딩)
- `ARGOCD_SERVER`: ArgoCD 서버 주소 (예: `argo.jclee.me`)
- `ARGOCD_AUTH_TOKEN`: ArgoCD 인증 토큰
- `SLACK_WEBHOOK_URL`: Slack 알림용 웹훅 URL (선택사항)
- `K6_CLOUD_TOKEN`: 성능 테스트용 k6 클라우드 토큰 (선택사항)

### 4단계: 워크플로우 활성화

1. 기존 워크플로우 비활성화:
   ```bash
   # .github/workflows/main.yml → .github/workflows/main.yml.old
   mv .github/workflows/main.yml .github/workflows/main.yml.old
   ```

2. 새 워크플로우 활성화:
   ```bash
   # enhanced-cicd.yml을 기본 워크플로우로 사용
   cp .github/workflows/enhanced-cicd.yml .github/workflows/main.yml
   ```

### 5단계: ArgoCD 설정 업데이트

```bash
# ArgoCD 애플리케이션 업데이트
kubectl apply -f k8s/argocd-app-clean.yaml

# ArgoCD 동기화
argocd app sync blacklist --grpc-web
```

### 6단계: 이미지 빌드 및 푸시 테스트

```bash
# Docker 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# 이미지 빌드
docker build -f deployment/Dockerfile -t ghcr.io/$GITHUB_USERNAME/blacklist:test .

# 이미지 푸시
docker push ghcr.io/$GITHUB_USERNAME/blacklist:test

# 이미지 확인
docker pull ghcr.io/$GITHUB_USERNAME/blacklist:test
```

## CI/CD 파이프라인 개선사항

### 1. 병렬 처리
- 코드 품질 검사 (lint, security, type-check)를 병렬로 실행
- 단위 테스트와 통합 테스트를 병렬로 실행

### 2. 캐싱 전략
- GitHub Actions 캐시 활용 (pip, pytest, Docker layers)
- BuildKit 인라인 캐시로 빌드 속도 향상

### 3. 보안 강화
- Trivy를 이용한 취약점 스캐닝
- SBOM (Software Bill of Materials) 생성
- Provenance 정보 포함

### 4. 멀티 플랫폼 빌드
- linux/amd64 및 linux/arm64 지원
- 다양한 환경에서 실행 가능

### 5. 자동 롤백
- 배포 실패 시 자동으로 이슈 생성
- 롤백 준비 자동화

## 기존 시스템과의 호환성

### 임시 호환성 유지 (선택사항)

마이그레이션 기간 동안 두 레지스트리를 동시에 사용해야 하는 경우:

```yaml
# k8s/deployment.yaml
imagePullSecrets:
  - name: ghcr-secret
  - name: regcred  # 기존 시크릿도 유지
```

### 점진적 마이그레이션

1. **Phase 1**: 새 이미지를 GHCR에 푸시하되, 기존 레지스트리도 유지
2. **Phase 2**: 모든 배포를 GHCR에서 수행
3. **Phase 3**: 기존 레지스트리 참조 완전 제거

## 문제 해결

### 인증 실패
```bash
# 토큰 권한 확인
gh api user -H "Authorization: token $GITHUB_TOKEN"

# 패키지 권한 확인
gh api user/packages/container/blacklist -H "Authorization: token $GITHUB_TOKEN"
```

### 이미지 풀 실패
```bash
# 시크릿 확인
kubectl get secret ghcr-secret -n blacklist -o yaml

# 시크릿 재생성
kubectl delete secret ghcr-secret -n blacklist
./scripts/setup-ghcr-secret.sh
```

### ArgoCD 동기화 실패
```bash
# ArgoCD 로그 확인
argocd app logs blacklist --grpc-web

# 수동 동기화 강제
argocd app sync blacklist --force --grpc-web
```

## 모니터링

### GitHub Packages 대시보드
- https://github.com/users/YOUR_USERNAME/packages/container/blacklist

### 이미지 사용량 확인
```bash
# 패키지 정보 조회
gh api /user/packages/container/blacklist/versions
```

### 비용 관리
- Public 저장소: 무료
- Private 저장소: 
  - 무료 계정: 500MB 스토리지, 1GB/월 전송량
  - Pro 계정: 2GB 스토리지, 10GB/월 전송량

## 롤백 계획

문제 발생 시 기존 레지스트리로 롤백:

```bash
# 1. deployment.yaml에서 이미지 URL 변경
kubectl set image deployment/blacklist blacklist=registry.jclee.me/blacklist:latest -n blacklist

# 2. 이미지 풀 시크릿 변경
kubectl patch deployment blacklist -n blacklist --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/imagePullSecrets",
    "value": [{"name": "regcred"}]
  }
]'

# 3. 롤아웃 상태 확인
kubectl rollout status deployment/blacklist -n blacklist
```

## 완료 체크리스트

- [ ] GitHub Personal Access Token 생성
- [ ] GHCR 시크릿 설정 완료
- [ ] GitHub Actions 시크릿 설정
- [ ] CI/CD 워크플로우 업데이트
- [ ] Kubernetes 매니페스트 업데이트
- [ ] ArgoCD 설정 업데이트
- [ ] 첫 번째 이미지 빌드 및 푸시 성공
- [ ] 배포 테스트 완료
- [ ] 모니터링 설정 확인
- [ ] 팀원들에게 변경사항 공유

## 참고 자료

- [GitHub Container Registry 문서](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Actions에서 GHCR 사용하기](https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions)
- [Kubernetes에서 Private Registry 사용하기](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)
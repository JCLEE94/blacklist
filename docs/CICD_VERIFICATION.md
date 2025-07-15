# CI/CD 파이프라인 검증 가이드

## 1. 사전 준비사항 확인

### GitHub Secrets 설정 확인
```bash
# GitHub CLI로 시크릿 확인
gh secret list

# 필수 시크릿 목록
# - REGISTRY_USERNAME
# - REGISTRY_PASSWORD
# - CHARTS_REPO_TOKEN
# - SECRET_KEY
# - JWT_SECRET_KEY
# - REGTECH_USERNAME
# - REGTECH_PASSWORD
# - SECUDIUM_USERNAME
# - SECUDIUM_PASSWORD
```

### GitHub Variables 설정 확인
```bash
# GitHub CLI로 변수 확인
gh variable list

# 필수 변수 목록
# - SERVICE_URL
# - ARGOCD_URL
```

## 2. charts.jclee.me 리포지토리 준비

### 리포지토리 구조 확인
```bash
charts.jclee.me/
├── charts/
│   └── blacklist/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           └── ...
```

### 차트 파일 복사
```bash
# 현재 리포지토리에서 charts.jclee.me로 복사
cp -r charts/blacklist/* /path/to/charts.jclee.me/charts/blacklist/
```

## 3. CI/CD 파이프라인 테스트

### 3.1 로컬 빌드 테스트
```bash
# 코드 품질 검사
echo "🔍 코드 품질 검사..."
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
black --check src/ --diff
isort src/ --check-only --diff
mypy src/ --ignore-missing-imports

# 보안 스캔
echo "🔒 보안 스캔..."
bandit -r src/ -ll
safety check

# 테스트 실행
echo "🧪 테스트 실행..."
pytest tests/ -v --cov=src
```

### 3.2 Docker 이미지 빌드 테스트
```bash
# 이미지 빌드
echo "🐳 Docker 이미지 빌드..."
docker build -f deployment/Dockerfile -t blacklist:test .

# 이미지 실행 테스트
echo "🚀 이미지 실행 테스트..."
docker run -d --name blacklist-test -p 8541:8541 blacklist:test
sleep 10

# 헬스체크
curl -f http://localhost:8541/health || echo "❌ 헬스체크 실패"

# 컨테이너 정리
docker stop blacklist-test
docker rm blacklist-test
```

### 3.3 GitHub Actions 워크플로우 테스트
```bash
# 워크플로우 구문 검사
echo "📋 워크플로우 구문 검사..."
gh workflow validate .github/workflows/ci-cd.yml

# 워크플로우 수동 실행
echo "🚀 워크플로우 수동 실행..."
gh workflow run ci-cd.yml

# 실행 상태 확인
gh run list --workflow=ci-cd.yml
```

## 4. ArgoCD 설정 검증

### 4.1 ArgoCD 설치 확인
```bash
# ArgoCD 설치 상태 확인
kubectl get pods -n argocd

# ArgoCD 서버 접근 확인
curl -k https://argo.jclee.me/health
```

### 4.2 ArgoCD 애플리케이션 배포 테스트
```bash
# 배포 스크립트 실행
./scripts/deploy-argocd.sh

# 애플리케이션 상태 확인
argocd app get blacklist --grpc-web --server argo.jclee.me
```

## 5. 전체 파이프라인 검증

### 5.1 코드 변경 → 자동 배포 테스트
```bash
# 1. 코드 변경
echo "# Test change $(date)" >> README.md

# 2. 커밋 및 푸시
git add README.md
git commit -m "test: pipeline verification"
git push origin main

# 3. GitHub Actions 실행 확인
gh run list --workflow=ci-cd.yml --limit=1

# 4. 이미지 빌드 확인
docker pull registry.jclee.me/blacklist:latest

# 5. Charts 리포지토리 PR 확인
# https://github.com/jclee/charts/pulls

# 6. ArgoCD 동기화 확인
argocd app get blacklist --grpc-web --server argo.jclee.me
```

### 5.2 서비스 동작 확인
```bash
# 서비스 접근 테스트
curl -f https://blacklist.jclee.me/health

# API 엔드포인트 테스트
curl -f https://blacklist.jclee.me/api/stats

# 파드 상태 확인
kubectl get pods -n blacklist
kubectl logs -f deployment/blacklist -n blacklist
```

## 6. 성능 및 안정성 검증

### 6.1 부하 테스트
```bash
# Apache Bench를 사용한 부하 테스트
ab -n 1000 -c 10 https://blacklist.jclee.me/health

# 또는 wrk를 사용한 부하 테스트
wrk -t12 -c400 -d30s https://blacklist.jclee.me/health
```

### 6.2 롤백 테스트
```bash
# 이전 버전으로 롤백
argocd app rollback blacklist --grpc-web --server argo.jclee.me

# 롤백 상태 확인
kubectl rollout status deployment/blacklist -n blacklist
```

## 7. 모니터링 및 로그 확인

### 7.1 파이프라인 로그 확인
```bash
# GitHub Actions 로그 확인
gh run view --log

# ArgoCD 로그 확인
kubectl logs -f deployment/argocd-server -n argocd
```

### 7.2 애플리케이션 로그 확인
```bash
# 애플리케이션 로그 확인
kubectl logs -f deployment/blacklist -n blacklist

# 이벤트 확인
kubectl get events -n blacklist --sort-by=.metadata.creationTimestamp
```

## 8. 문제 해결

### 8.1 일반적인 문제점

#### GitHub Actions 실패
```bash
# 실패 원인 확인
gh run view --log

# 시크릿 확인
gh secret list
```

#### Docker 이미지 빌드 실패
```bash
# 레지스트리 접근 확인
docker login registry.jclee.me

# 이미지 수동 빌드
docker build -f deployment/Dockerfile -t registry.jclee.me/blacklist:debug .
```

#### ArgoCD 동기화 실패
```bash
# 애플리케이션 상태 확인
argocd app get blacklist --grpc-web --server argo.jclee.me

# 수동 동기화
argocd app sync blacklist --grpc-web --server argo.jclee.me
```

### 8.2 디버깅 명령어

```bash
# 파이프라인 디버그
echo "🔍 파이프라인 디버깅..."

# 1. GitHub Actions 상태
gh run list --workflow=ci-cd.yml --limit=5

# 2. 레지스트리 이미지 확인
docker images registry.jclee.me/blacklist

# 3. ArgoCD 상태
argocd app list --grpc-web --server argo.jclee.me

# 4. Kubernetes 리소스 확인
kubectl get all -n blacklist

# 5. 네트워크 연결 테스트
curl -I https://blacklist.jclee.me/health
```

## 9. 성공 기준

### 9.1 CI/CD 파이프라인 성공 기준
- [ ] 코드 품질 검사 통과
- [ ] 보안 스캔 통과 (경고 허용)
- [ ] 단위 테스트 통과 (일부 실패 허용)
- [ ] 통합 테스트 통과 (일부 실패 허용)
- [ ] Docker 이미지 빌드 성공
- [ ] 이미지 레지스트리 푸시 성공
- [ ] Charts 리포지토리 PR 생성 성공
- [ ] ArgoCD 동기화 성공

### 9.2 배포 성공 기준
- [ ] 파드 Running 상태
- [ ] 서비스 접근 가능
- [ ] 헬스체크 응답 200 OK
- [ ] API 엔드포인트 정상 응답
- [ ] 로그 정상 출력
- [ ] 리소스 사용량 정상 범위

## 10. 체크리스트

### 배포 전 체크리스트
- [ ] GitHub Secrets 설정 완료
- [ ] GitHub Variables 설정 완료
- [ ] charts.jclee.me 리포지토리 준비
- [ ] ArgoCD 설치 및 설정 완료
- [ ] 레지스트리 접근 권한 확인
- [ ] 네트워크 연결 확인

### 배포 후 체크리스트
- [ ] 파이프라인 실행 성공
- [ ] 이미지 빌드 및 푸시 성공
- [ ] Charts PR 생성 성공
- [ ] ArgoCD 동기화 성공
- [ ] 서비스 정상 동작 확인
- [ ] 모니터링 및 로그 확인
- [ ] 부하 테스트 통과
- [ ] 롤백 테스트 통과

이 가이드를 따라 모든 검증을 완료하면 CI/CD 파이프라인이 정상적으로 작동하는 것을 확인할 수 있습니다.
# CI/CD 파이프라인 안정화 가이드

## 개요
블랙리스트 시스템의 CI/CD 파이프라인을 안정화하기 위한 개선 사항들입니다.

## 주요 개선사항

### 1. GitHub Actions 워크플로우 (`stable-cicd.yml`)
- **에러 처리 개선**: `|| true` 제거, 적절한 에러 핸들링
- **단계별 분리**: 코드 품질, 테스트, 빌드, 배포 단계 명확히 구분
- **조건부 실행**: main 브랜치만 배포, PR은 테스트만
- **캐시 최적화**: self-hosted runner용 로컬 캐시 사용

### 2. Docker 최적화 (`Dockerfile.optimized`)
- **멀티스테이지 빌드**: 의존성 설치와 실행 이미지 분리
- **캐시 효율성**: requirements.txt 먼저 복사하여 캐시 활용
- **보안 강화**: non-root 사용자로 실행
- **메타데이터**: 빌드 정보 라벨 추가

### 3. ArgoCD 설정 (`argocd-app-stable.yaml`)
- **자동 동기화**: selfHeal 활성화로 수동 변경 방지
- **안전한 배포**: 3회 재시도, 점진적 백오프
- **리소스 정리**: prune 정책으로 불필요한 리소스 제거
- **차이점 무시**: replicas, clusterIP 등 동적 값 무시

### 4. 배포 스크립트 (`stable-deploy.sh`)
- **사전 체크**: kubectl, ArgoCD CLI 확인
- **에러 처리**: 각 단계별 실패 시 적절한 처리
- **헬스체크**: 배포 후 자동 검증
- **롤백 지원**: 실패 시 자동 롤백

## 사용 방법

### 1. 로컬 테스트
```bash
# 코드 품질 검사
flake8 src/ --max-line-length=88
black --check src/
isort src/ --check-only

# 테스트 실행
pytest tests/ -v

# Docker 빌드 테스트
docker build -f deployment/Dockerfile.optimized -t blacklist:test .
```

### 2. 배포
```bash
# 자동 배포 (권장)
git push origin main  # GitHub Actions가 자동으로 처리

# 수동 배포
./scripts/stable-deploy.sh
```

### 3. 모니터링
```bash
# 배포 상태 확인
kubectl get pods -n blacklist
kubectl logs -f deployment/blacklist -n blacklist

# ArgoCD 상태 확인
argocd app get blacklist --grpc-web

# 헬스체크
curl http://localhost:32452/health
```

## 트러블슈팅

### 빌드 실패
```bash
# 캐시 삭제
rm -rf /tmp/.buildx-cache

# 로컬 빌드 테스트
docker build --no-cache -f deployment/Dockerfile.optimized .
```

### 배포 실패
```bash
# Pod 상태 확인
kubectl describe pod -n blacklist

# 이전 버전으로 롤백
kubectl rollout undo deployment/blacklist -n blacklist

# ArgoCD 수동 동기화
argocd app sync blacklist --force
```

### 헬스체크 실패
```bash
# Pod 로그 확인
kubectl logs -f deployment/blacklist -n blacklist

# 서비스 엔드포인트 확인
kubectl get endpoints -n blacklist

# 직접 Pod 접속
kubectl exec -it deployment/blacklist -n blacklist -- /bin/bash
```

## 환경 변수 설정

### GitHub Secrets (필수)
```
REGISTRY_USERNAME    # Registry 사용자명
REGISTRY_PASSWORD    # Registry 비밀번호
ARGOCD_SERVER       # ArgoCD 서버 주소
ARGOCD_PASSWORD     # ArgoCD admin 비밀번호
```

### Kubernetes Secrets
```bash
# Registry 인증
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  -n blacklist

# 애플리케이션 비밀번호
kubectl create secret generic blacklist-secrets \
  --from-literal=REGTECH_USERNAME=nextrade \
  --from-literal=REGTECH_PASSWORD='Sprtmxm1@3' \
  -n blacklist
```

## 성능 최적화

### 1. 병렬 처리
- GitHub Actions matrix 전략으로 테스트 병렬 실행
- Docker 멀티스테이지 빌드로 빌드 시간 단축

### 2. 캐싱
- Python 의존성 캐싱
- Docker 레이어 캐싱
- self-hosted runner 로컬 캐시 활용

### 3. 리소스 관리
- HPA로 자동 스케일링
- 적절한 리소스 요청/제한 설정

## 보안 고려사항

1. **시크릿 관리**: 하드코딩된 비밀번호 제거
2. **이미지 스캔**: 취약점 스캔 추가 권장
3. **네트워크 정책**: Pod 간 통신 제한
4. **RBAC**: 최소 권한 원칙 적용

## 향후 개선사항

1. **Helm Chart 도입**: 더 나은 버전 관리
2. **Blue-Green 배포**: 무중단 배포 구현
3. **메트릭 수집**: Prometheus 연동
4. **알림 설정**: Slack/Email 알림
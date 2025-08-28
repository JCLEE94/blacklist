# 🚀 Blacklist GitOps 배포 파이프라인

blacklist 프로젝트를 위한 고도화된 GitHub Actions GitOps 워크플로우와 Kubernetes 매니페스트가 성공적으로 구성되었습니다.

## 📁 생성된 파일 구조

```
blacklist/
├── .github/workflows/
│   └── main-gitops.yml           # 메인 GitOps 워크플로우
├── k8s/
│   ├── base/                     # 기본 Kubernetes 매니페스트
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── secret.yaml
│   └── overlays/
│       └── production/           # 프로덕션 환경 오버레이
│           ├── kustomization.yaml
│           └── resource-patch.yaml
└── argocd-application.yaml       # ArgoCD Application 정의
```

## 🔄 GitOps 워크플로우 단계

### 1. 🧹 코드 품질 검사
- **Python 린팅**: flake8, black, isort
- **보안 스캔**: bandit, safety
- **파일 크기 검사**: 500줄 제한 준수 확인
- **테스트 실행**: pytest with coverage

### 2. 🏷️ 자동 버전 관리
- **날짜 기반 버전**: `v2025.01.11-abc1234` 형식
- **Git 태그 생성**: main 브랜치에서 자동 태깅
- **중복 방지**: 기존 태그 충돌 시 타임스탬프 추가

### 3. 🐳 Docker 이미지 빌드 & 푸시
- **멀티 플랫폼**: linux/amd64, linux/arm64
- **레지스트리**: registry.jclee.me/jclee94/blacklist
- **캐싱 최적화**: GitHub Actions 캐시 활용
- **보안 스캔**: Trivy를 통한 취약점 검사

### 4. 📝 K8s 매니페스트 업데이트
- **자동 이미지 태그 업데이트**: kustomization.yaml 수정
- **환경별 설정**: production/staging/development
- **Git 커밋**: 매니페스트 변경사항 자동 커밋

### 5. 🔄 ArgoCD 동기화
- **API 기반 동기화**: ArgoCD REST API 호출
- **상태 모니터링**: 배포 상태 실시간 확인
- **재시도 로직**: 실패 시 자동 재시도

### 6. ✅ 배포 후 검증
- **헬스체크**: `/health` 엔드포인트 검증
- **API 테스트**: 주요 엔드포인트 동작 확인
- **자동 롤백**: 실패 시 이전 버전으로 롤백

## 🔧 필수 설정

### GitHub Secrets
```bash
# Registry 인증
REGISTRY_USER=your-registry-username
REGISTRY_PASS=your-registry-password

# ArgoCD API 토큰
ARGOCD_TOKEN=your-argocd-api-token
```

### GitHub Variables
```bash
# 인프라 도메인
REGISTRY_DOMAIN=registry.jclee.me
ARGOCD_DOMAIN=argo.jclee.me

# 프로젝트 설정
PROJECT_NAME=blacklist
K8S_NAMESPACE=default

# 알림 (선택사항)
SLACK_WEBHOOK_URL=your-slack-webhook-url
```

## 🎯 트리거 조건

### 자동 트리거
- **Push to main**: 프로덕션 자동 배포
- **Push to develop**: 스테이징/개발 환경 배포
- **Pull Request**: 품질 검사만 실행

### 수동 트리거
- **Workflow Dispatch**: 환경 선택 가능
- **강제 재빌드**: 이미지 캐시 무시 옵션

## 📊 배포 환경

### Production (main 브랜치)
```yaml
환경: production
네임스페이스: default
도메인: blacklist.jclee.me
복제본: 3개
자동 확장: 3-10개 Pod
SSL: 자동 (Let's Encrypt)
```

### Staging (develop 브랜치)
```yaml
환경: staging
네임스페이스: staging
도메인: staging-blacklist.jclee.me
복제본: 2개
```

### Development (develop 브랜치)
```yaml
환경: development
네임스페이스: development
도메인: dev-blacklist.jclee.me
복제본: 1개
```

## 🔐 보안 기능

### 애플리케이션 보안
- **비루트 실행**: UID 1000으로 실행
- **읽기 전용 파일시스템**: 보안 강화
- **리소스 제한**: CPU/메모리 제한 설정

### 네트워크 보안
- **TLS 강제**: HTTPS 리다이렉트
- **속도 제한**: 분당 50-100 요청 제한
- **ModSecurity**: WAF 보호 (프로덕션)

### Kubernetes 보안
- **Pod Security Context**: 보안 컨텍스트 적용
- **Service Account**: 최소 권한 원칙
- **Secret 관리**: 암호화된 환경변수

## 📈 모니터링 & 관찰성

### 헬스체크 엔드포인트
- **Startup Probe**: 초기 실행 상태 확인
- **Liveness Probe**: 서비스 생존 상태
- **Readiness Probe**: 트래픽 수신 준비 상태

### 메트릭 수집
- **Prometheus**: 메트릭 스크래핑 설정
- **포트**: 2541번 포트에서 메트릭 제공
- **경로**: `/metrics` 엔드포인트

### 로깅
- **구조화된 로그**: JSON 형태 로그 출력
- **로그 레벨**: 환경별 로그 레벨 설정
- **로그 집계**: ELK Stack 연동 가능

## 🚀 배포 명령어

### 수동 워크플로우 실행
```bash
# GitHub Actions 탭에서 "GitOps Deployment Pipeline" 선택
# "Run workflow" 클릭 후 환경 선택
```

### ArgoCD 수동 동기화
```bash
# ArgoCD CLI 사용
argocd app sync blacklist-production

# 또는 ArgoCD 웹 UI에서 Sync 버튼 클릭
# https://argo.jclee.me
```

### Kubernetes 직접 배포
```bash
# Kustomize를 사용한 직접 배포
kubectl apply -k k8s/overlays/production

# 배포 상태 확인
kubectl get pods -l app=blacklist
kubectl logs -l app=blacklist -f
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. Docker 빌드 실패
```bash
# 캐시 정리 후 재시도
docker system prune -a
```

#### 2. ArgoCD 동기화 실패
```bash
# 애플리케이션 새로고침
argocd app refresh blacklist-production

# 수동 동기화 실행
argocd app sync blacklist-production --force
```

#### 3. Pod 시작 실패
```bash
# 로그 확인
kubectl logs -l app=blacklist --tail=100

# 이벤트 확인
kubectl get events --sort-by=.metadata.creationTimestamp
```

#### 4. 헬스체크 실패
```bash
# 엔드포인트 직접 테스트
kubectl port-forward svc/blacklist-service 8080:80
curl http://localhost:8080/health
```

### 롤백 절차

#### GitHub Actions를 통한 롤백
1. 이전 성공한 커밋으로 되돌리기
2. 워크플로우 재실행

#### ArgoCD를 통한 롤백
1. ArgoCD UI에서 History 탭 선택
2. 이전 버전 선택 후 Rollback

#### Kubernetes를 통한 롤백
```bash
# 배포 롤백
kubectl rollout undo deployment/blacklist

# 특정 리비전으로 롤백
kubectl rollout undo deployment/blacklist --to-revision=2
```

## 📞 지원

### 모니터링 대시보드
- **ArgoCD**: https://argo.jclee.me
- **애플리케이션**: https://blacklist.jclee.me
- **GitHub Actions**: https://github.com/jclee/blacklist/actions

### 로그 및 메트릭
- **Pod 로그**: `kubectl logs -l app=blacklist`
- **이벤트**: `kubectl get events`
- **메트릭**: `curl blacklist.jclee.me/metrics`

---

## ✅ 배포 완료 체크리스트

- [x] GitHub Actions 워크플로우 생성
- [x] Kubernetes 매니페스트 구성
- [x] ArgoCD Application 정의
- [x] 보안 설정 구성
- [x] 모니터링 설정 완료
- [x] 문서화 완료

### 다음 단계
1. GitHub Secrets 및 Variables 설정
2. ArgoCD에 Application 등록
3. 첫 배포 테스트 실행
4. 모니터링 대시보드 설정
5. 알림 채널 구성

🎉 **blacklist GitOps 파이프라인이 성공적으로 구성되었습니다!**
# Blacklist K8s Configuration (GitOps)

이 저장소는 블랙리스트 시스템의 Kubernetes 설정을 관리합니다.

## 📁 디렉토리 구조

```
.
├── base/                   # 공통 Kubernetes 리소스
│   ├── deployment.yaml    # 기본 Deployment
│   ├── service.yaml       # Service 정의
│   ├── configmap.yaml     # ConfigMap
│   └── kustomization.yaml # Kustomize 설정
├── overlays/              # 환경별 설정
│   ├── dev/              # 개발 환경
│   ├── staging/          # 스테이징 환경
│   └── prod/             # 프로덕션 환경
└── argocd/
    └── applications/      # ArgoCD Application 정의
```

## 🚀 시작하기

### 1. 사전 요구사항

- Kubernetes 클러스터 접근 권한
- kubectl 설치
- kustomize 설치 (선택사항)
- ArgoCD 접근 권한

### 2. 로컬에서 매니페스트 빌드

```bash
# 개발 환경
kustomize build overlays/dev

# 프로덕션 환경
kustomize build overlays/prod

# 직접 적용 (권장하지 않음 - ArgoCD 사용)
kustomize build overlays/dev | kubectl apply -f -
```

### 3. Secret 관리

**중요**: 실제 시크릿은 Git에 커밋하지 마세요!

#### 개발 환경
```bash
cd overlays/dev
cp .env.secret.example .env.secret
# .env.secret 파일을 실제 값으로 수정
```

#### 프로덕션 환경
프로덕션은 Kubernetes Secret을 직접 생성:
```bash
kubectl create secret generic blacklist-secrets \
  --from-literal=REGTECH_USERNAME=actual_username \
  --from-literal=REGTECH_PASSWORD=actual_password \
  --namespace=blacklist
```

## 🔄 GitOps 워크플로우

1. **코드 변경** → App 저장소 (blacklist)에 푸시
2. **CI/CD** → GitHub Actions가 Docker 이미지 빌드 & 푸시
3. **매니페스트 업데이트** → 이 저장소의 이미지 태그 자동 업데이트
4. **ArgoCD 동기화** → 변경사항 감지 및 자동 배포

## 📝 환경별 설정

### Development (dev)
- Namespace: `blacklist-dev`
- Replicas: 1
- 리소스: 최소 설정
- 로그 레벨: DEBUG
- 수집 기능: 비활성화

### Production (prod)
- Namespace: `blacklist`
- Replicas: 3 (HPA로 자동 스케일링)
- 리소스: 프로덕션 사양
- 로그 레벨: WARNING
- 수집 기능: 활성화

## 🛠️ 일반적인 작업

### 이미지 태그 업데이트
```bash
cd overlays/prod
kustomize edit set image registry.jclee.me/blacklist:v1.2.3
```

### ConfigMap 수정
```bash
cd overlays/prod
# kustomization.yaml의 configMapGenerator 섹션 수정
```

### 새로운 환경 추가
```bash
mkdir -p overlays/staging
cp overlays/dev/* overlays/staging/
# 환경에 맞게 수정
```

## 🔐 보안 고려사항

1. **Secret 관리**
   - Git에 실제 시크릿 커밋 금지
   - Sealed Secrets 또는 External Secrets 사용 권장

2. **이미지 Pull Secret**
   ```bash
   kubectl create secret docker-registry regcred \
     --docker-server=registry.jclee.me \
     --docker-username=admin \
     --docker-password=<password> \
     --namespace=blacklist
   ```

3. **RBAC**
   - 최소 권한 원칙 적용
   - 환경별 접근 권한 분리

## 🔍 트러블슈팅

### ArgoCD 동기화 실패
```bash
# ArgoCD 앱 상태 확인
argocd app get blacklist-prod

# 수동 동기화
argocd app sync blacklist-prod

# 차이점 확인
argocd app diff blacklist-prod
```

### 이미지 Pull 오류
```bash
# Secret 확인
kubectl get secret regcred -n blacklist -o yaml

# Secret 재생성
kubectl delete secret regcred -n blacklist
kubectl create secret docker-registry regcred ...
```

## 📞 지원

문제가 있으면 이슈를 생성해주세요.
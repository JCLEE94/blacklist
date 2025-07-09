# Kubernetes Native CI/CD Pipeline

이 문서는 Kubernetes의 장점을 최대한 활용하도록 재설계된 CI/CD 파이프라인을 설명합니다.

## 주요 개선사항

### 1. **병렬 처리 최적화**
- 코드 품질 검사를 매트릭스 빌드로 병렬화 (lint, security, dependency)
- 테스트를 종류별로 병렬 실행 (unit, integration, e2e)
- 멀티 플랫폼 컨테이너 빌드 (amd64, arm64)

### 2. **Kubernetes 네이티브 기능 활용**
- **Kustomize**: 환경별 구성 관리 (base + overlays)
- **HPA**: CPU/메모리/커스텀 메트릭 기반 자동 스케일링
- **VPA**: 리소스 요구사항 자동 최적화
- **PDB**: 무중단 배포를 위한 Pod 중단 예산
- **NetworkPolicy**: 세밀한 네트워크 보안 정책
- **TopologySpreadConstraints**: AZ 간 균등 분산

### 3. **고급 배포 전략**
- **Rolling Update**: 기본 무중단 배포
- **Blue-Green**: 즉시 롤백 가능한 배포
- **Canary**: Flagger를 통한 점진적 배포
- **GitOps**: ArgoCD 기반 선언적 배포

### 4. **보안 강화**
- **OPA (Open Policy Agent)**: 정책 기반 보안 검증
- **Trivy**: 컨테이너 이미지 취약점 스캔
- **PodSecurityPolicy**: Pod 수준 보안 정책
- **RBAC**: 최소 권한 원칙 적용
- **Sealed Secrets**: 암호화된 시크릿 관리

### 5. **모니터링 및 관찰성**
- **Prometheus**: 메트릭 수집 및 저장
- **Grafana**: 시각화 대시보드
- **ServiceMonitor**: 자동 메트릭 수집 구성
- **PrometheusRule**: 자동화된 알림 규칙
- **분산 추적**: OpenTelemetry 지원

### 6. **성능 최적화**
- **Build 캐싱**: Docker layer 캐싱 및 registry 캐싱
- **의존성 캐싱**: pip, npm 등 패키지 캐싱
- **병렬 빌드**: 멀티 플랫폼 동시 빌드
- **리소스 최적화**: VPA를 통한 자동 최적화

## 파일 구조

```
.github/workflows/
└── k8s-native-cicd.yml      # 메인 CI/CD 워크플로우

k8s/
├── base/                    # 기본 Kubernetes 리소스
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── networkpolicy.yaml
│   └── servicemonitor.yaml
├── overlays/               # 환경별 구성
│   ├── development/
│   ├── staging/
│   └── production/
├── components/             # 재사용 가능한 컴포넌트
│   ├── security/          # 보안 관련 리소스
│   └── monitoring/        # 모니터링 관련 리소스
├── policies/              # OPA 정책
│   ├── security.rego
│   └── resource-limits.rego
└── monitoring/            # 모니터링 구성
    ├── dashboards/
    └── alerts/

charts/blacklist/          # Helm Chart
├── Chart.yaml
├── values.yaml
└── templates/

scripts/
└── k8s-native-deploy.sh   # 통합 배포 스크립트

tests/
├── e2e/                   # End-to-End 테스트
├── performance/           # 성능 테스트
├── unit/                  # 단위 테스트
└── integration/           # 통합 테스트
```

## 사용 방법

### 1. 자동 배포 (GitHub Actions)

```bash
# main 브랜치에 푸시하면 자동으로 프로덕션 배포
git push origin main

# develop 브랜치에 푸시하면 스테이징 배포
git push origin develop
```

### 2. 수동 배포

```bash
# Rolling Update (기본)
./scripts/k8s-native-deploy.sh -e production -s rolling

# Blue-Green 배포
./scripts/k8s-native-deploy.sh -e production -s blue-green

# Canary 배포
./scripts/k8s-native-deploy.sh -e production -s canary

# Helm 배포
./scripts/k8s-native-deploy.sh -e production -s helm

# ArgoCD GitOps 배포
./scripts/k8s-native-deploy.sh -e production -s argocd
```

### 3. 환경별 배포

```bash
# 개발 환경
./scripts/k8s-native-deploy.sh -e development

# 스테이징 환경
./scripts/k8s-native-deploy.sh -e staging

# 프로덕션 환경
./scripts/k8s-native-deploy.sh -e production
```

### 4. 롤백

```bash
# 이전 버전으로 롤백
./scripts/k8s-native-deploy.sh --rollback
```

## 환경별 설정

### Development
- **Namespace**: blacklist-dev
- **Replicas**: 1
- **Resources**: 최소 (CPU: 50m-200m, Memory: 128Mi-256Mi)
- **HPA**: 1-3 replicas

### Staging
- **Namespace**: blacklist-staging
- **Replicas**: 2
- **Resources**: 중간 (CPU: 100m-500m, Memory: 256Mi-512Mi)
- **HPA**: 2-5 replicas
- **Ingress**: staging.blacklist.jclee.me

### Production
- **Namespace**: blacklist
- **Replicas**: 3
- **Resources**: 최대 (CPU: 500m-2000m, Memory: 512Mi-2Gi)
- **HPA**: 3-20 replicas
- **VPA**: 자동 리소스 최적화
- **Ingress**: blacklist.jclee.me

## 모니터링

### Prometheus 메트릭
- Request rate, response time, error rate
- CPU/Memory 사용률
- Pod 상태 및 재시작 횟수
- 커스텀 비즈니스 메트릭

### Grafana 대시보드
- 애플리케이션 성능 대시보드
- 인프라 모니터링 대시보드
- 비즈니스 메트릭 대시보드

### 알림
- 높은 오류율 (>5%)
- 높은 응답 시간 (p95 > 1s)
- Pod 재시작
- 리소스 사용률 초과

## 성능 테스트

K6를 사용한 부하 테스트:

```bash
# 로컬 테스트
k6 run tests/performance/load-test.js

# 프로덕션 테스트
k6 run -e BASE_URL=https://blacklist.jclee.me tests/performance/load-test.js

# 결과 분석
python scripts/analyze-performance.py performance-summary.json
```

## 보안 검증

### 컨테이너 이미지 스캔
```bash
trivy image registry.jclee.me/blacklist:latest
```

### OPA 정책 테스트
```bash
# 매니페스트 생성
kustomize build k8s/overlays/production > manifest.yaml

# 정책 검증
opa eval -d k8s/policies -i manifest.yaml "data.kubernetes.admission.deny[x]"
```

## 트러블슈팅

### Pod가 시작되지 않을 때
```bash
kubectl describe pod <pod-name> -n blacklist
kubectl logs <pod-name> -n blacklist --previous
```

### HPA가 작동하지 않을 때
```bash
kubectl get hpa -n blacklist
kubectl describe hpa blacklist -n blacklist
kubectl top pods -n blacklist
```

### 네트워크 정책 문제
```bash
kubectl get networkpolicy -n blacklist
kubectl describe networkpolicy blacklist -n blacklist
```

### ArgoCD 동기화 문제
```bash
argocd app get blacklist-production
argocd app sync blacklist-production --force
argocd app rollback blacklist-production
```

## 베스트 프랙티스

1. **이미지 태그**: 절대 `latest` 태그를 프로덕션에 사용하지 않음
2. **리소스 제한**: 모든 컨테이너에 requests/limits 설정
3. **헬스 체크**: liveness, readiness, startup probe 구성
4. **보안**: 최소 권한 원칙, non-root 사용자 실행
5. **모니터링**: 모든 환경에 메트릭과 로깅 구성
6. **자동화**: GitOps를 통한 선언적 배포
7. **테스트**: 배포 전 자동화된 테스트 실행

## 향후 개선 계획

1. **Service Mesh (Istio/Linkerd)**: 고급 트래픽 관리
2. **Progressive Delivery**: Feature flags 통합
3. **Chaos Engineering**: 장애 주입 테스트
4. **Cost Optimization**: Karpenter를 통한 노드 자동 관리
5. **Multi-Cluster**: Federation을 통한 멀티 클러스터 관리
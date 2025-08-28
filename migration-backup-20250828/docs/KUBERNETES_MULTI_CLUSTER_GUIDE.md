# Kubernetes 멀티 클러스터 배포 가이드

## 📋 목차

1. [개요](#개요)
2. [클러스터 등록](#클러스터-등록)
3. [멀티 클러스터 배포](#멀티-클러스터-배포)
4. [ArgoCD 멀티 클러스터 설정](#argocd-멀티-클러스터-설정)
5. [트러블슈팅](#트러블슈팅)

## 개요

Blacklist 시스템을 여러 Kubernetes 클러스터에 동시에 배포하고 관리하는 방법을 설명합니다.

### 지원 기능

- ✅ 여러 Kubernetes 클러스터 동시 배포
- ✅ kubectl context 기반 클러스터 관리
- ✅ ArgoCD GitOps 멀티 클러스터 지원
- ✅ 병렬 배포로 빠른 롤아웃
- ✅ 클러스터별 상태 모니터링

## 클러스터 등록

### 1. 클러스터 등록 도구 실행

```bash
# 대화형 메뉴로 클러스터 관리
./scripts/kubectl-register-cluster.sh

# 또는 직접 명령 실행
./scripts/kubectl-register-cluster.sh add    # 클러스터 추가
./scripts/kubectl-register-cluster.sh list   # 클러스터 목록
./scripts/kubectl-register-cluster.sh test   # 연결 테스트
```

### 2. 클러스터 추가 방법

#### 방법 1: kubeconfig 파일로 추가

```bash
# 다른 클러스터의 kubeconfig 파일이 있는 경우
./scripts/kubectl-register-cluster.sh add

# 메뉴에서 1번 선택 후 kubeconfig 파일 경로 입력
# 예: /path/to/cluster2-kubeconfig.yaml
```

#### 방법 2: 원격 서버에서 자동 복사

```bash
# SSH 접근이 가능한 원격 서버의 kubeconfig 복사
./scripts/kubectl-register-cluster.sh add

# 메뉴에서 3번 선택
# 원격 서버 주소 입력: user@192.168.50.110
# kubeconfig 경로 입력 (기본값: ~/.kube/config)
```

#### 방법 3: 수동으로 클러스터 정보 입력

```bash
# API 서버 주소와 인증 정보를 직접 입력
./scripts/kubectl-register-cluster.sh add

# 메뉴에서 2번 선택
# 클러스터 이름: prod-cluster
# API 서버 URL: https://192.168.50.110:6443
# 인증 방식 선택 (인증서/토큰/사용자명)
```

### 3. 등록된 클러스터 확인

```bash
# kubectl contexts 확인
kubectl config get-contexts

# 클러스터별 연결 테스트
./scripts/kubectl-register-cluster.sh test
```

## 멀티 클러스터 배포

### 1. 모든 클러스터에 동시 배포

```bash
# 등록된 모든 클러스터에 자동 배포
./scripts/all-clusters-deploy.sh

# 메뉴에서 1번 선택: 모든 클러스터에 배포
```

### 2. 특정 클러스터 선택 배포

```bash
./scripts/all-clusters-deploy.sh

# 메뉴에서 2번 선택: 특정 클러스터만 선택하여 배포
```

### 3. 배포 진행 상황

```bash
# 실시간 진행 상황 모니터링
경과 시간: 45초 | 완료: 3/5

# 클러스터별 상태 확인
[local-cluster] 배포 완료!
[prod-cluster] 배포 완료!
[dev-cluster] 배포 진행중...
```

### 4. 배포 결과 확인

배포 완료 후 자동으로 각 클러스터의 상태를 확인합니다:

```bash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[local-cluster] 상태 확인
NAME                         READY   STATUS    RESTARTS   AGE
blacklist-7b9c5d4f6f-x2m4n   1/1     Running   0          2m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[prod-cluster] 상태 확인
NAME                         READY   STATUS    RESTARTS   AGE
blacklist-7b9c5d4f6f-k8s9p   1/1     Running   0          2m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## ArgoCD 멀티 클러스터 설정

### 1. ArgoCD에 클러스터 추가

```bash
# ArgoCD CLI로 클러스터 추가
argocd cluster add <context-name> --grpc-web

# 예시
argocd cluster add prod-cluster --grpc-web
argocd cluster add dev-cluster --grpc-web
```

### 2. ArgoCD Application 멀티 클러스터 설정

`k8s/argocd-app-multicluster.yaml` 생성:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: blacklist-multicluster
  namespace: argocd
spec:
  generators:
  - clusters: {}
  template:
    metadata:
      name: '{{name}}-blacklist'
    spec:
      project: default
      source:
        repoURL: https://github.com/JCLEE94/blacklist
        targetRevision: main
        path: k8s
      destination:
        server: '{{server}}'
        namespace: blacklist
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
        - CreateNamespace=true
```

### 3. ApplicationSet 배포

```bash
# ApplicationSet 적용
kubectl apply -f k8s/argocd-app-multicluster.yaml

# 모든 클러스터의 애플리케이션 확인
argocd app list --grpc-web
```

## 클러스터별 설정 관리

### 1. 클러스터별 환경 변수

각 클러스터마다 다른 설정이 필요한 경우:

```bash
# k8s/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

configMapGenerator:
  - name: cluster-config
    literals:
      - CLUSTER_NAME=production
      - NODE_PORT=32543

# k8s/overlays/development/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

configMapGenerator:
  - name: cluster-config
    literals:
      - CLUSTER_NAME=development
      - NODE_PORT=32544
```

### 2. 클러스터별 리소스 조정

```yaml
# k8s/overlays/production/deployment-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
spec:
  replicas: 4  # Production은 4개 replica
  template:
    spec:
      containers:
      - name: blacklist
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## 모니터링 및 관리

### 1. 클러스터별 상태 확인

```bash
# 특정 클러스터로 전환
kubectl config use-context prod-cluster

# Pod 상태 확인
kubectl get pods -n blacklist

# 로그 확인
kubectl logs -f deployment/blacklist -n blacklist

# 모든 클러스터 상태 한번에 확인
for ctx in $(kubectl config get-contexts -o name); do
  echo "=== $ctx ==="
  kubectl --context=$ctx get pods -n blacklist
  echo ""
done
```

### 2. 멀티 클러스터 로그 수집

```bash
# stern을 사용한 멀티 클러스터 로그 스트리밍
stern --all-namespaces --context=local-cluster blacklist &
stern --all-namespaces --context=prod-cluster blacklist &
```

### 3. 클러스터별 메트릭

```bash
# 각 클러스터의 리소스 사용량 확인
for ctx in $(kubectl config get-contexts -o name); do
  echo "=== $ctx resource usage ==="
  kubectl --context=$ctx top pods -n blacklist
  echo ""
done
```

## 트러블슈팅

### 1. 클러스터 연결 실패

```bash
# 문제: 클러스터 연결 실패
# 해결: 인증서 및 API 서버 주소 확인
kubectl config view --context=<context-name>

# kubeconfig 재설정
kubectl config set-cluster <cluster-name> \
  --server=https://new-api-server:6443 \
  --certificate-authority=/path/to/ca.crt
```

### 2. 배포 실패

```bash
# 배포 로그 확인
cat /tmp/deploy_<cluster-name>.log

# 일반적인 문제:
# - 네임스페이스 권한 부족
# - Docker Registry 접근 실패
# - 리소스 부족

# 해결: 클러스터별 권한 확인
kubectl auth can-i create deployment -n blacklist
```

### 3. ArgoCD 동기화 실패

```bash
# ArgoCD 애플리케이션 상태 확인
argocd app get <app-name> --grpc-web

# 수동 동기화
argocd app sync <app-name> --grpc-web

# 클러스터 연결 상태 확인
argocd cluster list --grpc-web
```

## 베스트 프랙티스

### 1. 클러스터 명명 규칙

```bash
# 환경과 지역을 포함한 명명
<environment>-<region>-cluster

예시:
- prod-kr-cluster
- dev-us-cluster
- staging-eu-cluster
```

### 2. 배포 순서

1. 개발 클러스터 먼저 배포
2. 스테이징 클러스터 검증
3. 프로덕션 클러스터 최종 배포

### 3. 롤백 전략

```bash
# 특정 클러스터만 롤백
kubectl config use-context <cluster-name>
kubectl rollout undo deployment/blacklist -n blacklist

# ArgoCD를 통한 롤백
argocd app rollback <app-name> <revision> --grpc-web
```

### 4. 보안 고려사항

- 각 클러스터마다 별도의 시크릿 사용
- 클러스터간 네트워크 격리
- RBAC 권한 최소화

## 자동화 예시

### GitHub Actions에서 멀티 클러스터 배포

```yaml
# .github/workflows/multi-cluster-deploy.yml
name: Multi-Cluster Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        cluster: [dev, staging, prod]
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        
      - name: Configure kubeconfig
        env:
          KUBECONFIG_DATA: ${{ secrets[format('KUBECONFIG_{0}', matrix.cluster)] }}
        run: |
          echo "$KUBECONFIG_DATA" | base64 -d > kubeconfig
          export KUBECONFIG=$(pwd)/kubeconfig
          
      - name: Deploy to cluster
        run: |
          kubectl apply -k k8s/overlays/${{ matrix.cluster }}
          kubectl rollout status deployment/blacklist -n blacklist
```

## 요약

멀티 클러스터 배포를 통해:
- 🚀 여러 환경에 동시 배포
- 🔄 일관된 배포 프로세스
- 📊 중앙화된 모니터링
- 🛡️ 환경별 격리 및 보안

추가 지원이 필요하면 [GitHub Issues](https://github.com/JCLEE94/blacklist/issues)에 문의해주세요.
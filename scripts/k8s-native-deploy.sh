#!/bin/bash

# Kubernetes Native CI/CD Deployment Script
# 이 스크립트는 Kubernetes의 장점을 최대한 활용하는 배포 프로세스를 구현합니다.

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 환경 변수
NAMESPACE="${NAMESPACE:-blacklist}"
ENVIRONMENT="${ENVIRONMENT:-production}"
DEPLOYMENT_STRATEGY="${STRATEGY:-rolling}"
REGISTRY="${REGISTRY:-registry.jclee.me}"
IMAGE_NAME="${IMAGE_NAME:-blacklist}"
HELM_RELEASE="${HELM_RELEASE:-blacklist}"

# 로깅 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# 사전 요구사항 확인
check_prerequisites() {
    log "Checking prerequisites..."
    
    # 필수 도구 확인
    local tools=("kubectl" "helm" "kustomize" "argocd")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is not installed"
        fi
    done
    
    # Kubernetes 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        error "Unable to connect to Kubernetes cluster"
    fi
    
    # ArgoCD 연결 확인
    if ! argocd app list &> /dev/null; then
        warning "ArgoCD CLI not logged in. Some features may be limited."
    fi
    
    success "All prerequisites met"
}

# 환경별 설정 적용
apply_environment_config() {
    log "Applying $ENVIRONMENT environment configuration..."
    
    case $ENVIRONMENT in
        development)
            NAMESPACE="blacklist-dev"
            REPLICAS=1
            RESOURCES_LIMITS_CPU="200m"
            RESOURCES_LIMITS_MEMORY="256Mi"
            ;;
        staging)
            NAMESPACE="blacklist-staging"
            REPLICAS=2
            RESOURCES_LIMITS_CPU="500m"
            RESOURCES_LIMITS_MEMORY="512Mi"
            ;;
        production)
            NAMESPACE="blacklist"
            REPLICAS=3
            RESOURCES_LIMITS_CPU="2000m"
            RESOURCES_LIMITS_MEMORY="2Gi"
            ;;
        *)
            error "Unknown environment: $ENVIRONMENT"
            ;;
    esac
    
    success "Environment configuration applied"
}

# Kustomize 빌드 및 검증
build_and_validate_manifests() {
    log "Building and validating Kubernetes manifests..."
    
    # Kustomize 빌드
    local manifest_file="/tmp/blacklist-${ENVIRONMENT}.yaml"
    kustomize build "k8s/overlays/${ENVIRONMENT}" > "$manifest_file"
    
    # 매니페스트 검증
    if command -v kubeconform &> /dev/null; then
        kubeconform -strict -summary "$manifest_file" || error "Manifest validation failed"
    else
        kubectl --dry-run=client -f "$manifest_file" || error "Manifest validation failed"
    fi
    
    # OPA 정책 검증 (설치되어 있는 경우)
    if command -v opa &> /dev/null && [ -d "k8s/policies" ]; then
        log "Running OPA policy validation..."
        opa eval -d k8s/policies -i "$manifest_file" \
            "data.kubernetes.admission.deny[x]" | jq -e '. == {}' || \
            warning "Some policies failed, but continuing..."
    fi
    
    success "Manifests built and validated"
    echo "$manifest_file"
}

# Helm을 통한 배포
deploy_with_helm() {
    log "Deploying with Helm..."
    
    # Helm 의존성 업데이트
    helm dependency update charts/blacklist
    
    # Helm 배포
    helm upgrade --install "$HELM_RELEASE" charts/blacklist \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --values "charts/blacklist/values.yaml" \
        --values "charts/blacklist/values-${ENVIRONMENT}.yaml" \
        --set image.tag="${IMAGE_TAG:-latest}" \
        --set environment="$ENVIRONMENT" \
        --wait --timeout 10m
    
    success "Helm deployment completed"
}

# Rolling Update 전략
deploy_rolling_update() {
    log "Performing rolling update deployment..."
    
    # 이미지 업데이트
    kubectl set image deployment/${HELM_RELEASE} \
        ${IMAGE_NAME}="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG:-latest}" \
        -n "$NAMESPACE" \
        --record
    
    # 롤아웃 상태 모니터링
    kubectl rollout status deployment/${HELM_RELEASE} -n "$NAMESPACE" --timeout=10m
    
    success "Rolling update completed"
}

# Blue-Green 배포 전략
deploy_blue_green() {
    log "Performing blue-green deployment..."
    
    # 현재 활성 환경 확인
    local current_color=$(kubectl get service ${HELM_RELEASE} -n "$NAMESPACE" \
        -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "blue")
    
    local new_color="green"
    if [ "$current_color" == "green" ]; then
        new_color="blue"
    fi
    
    log "Current environment: $current_color, deploying to: $new_color"
    
    # 새 환경 배포
    helm upgrade --install "${HELM_RELEASE}-${new_color}" charts/blacklist \
        --namespace "$NAMESPACE" \
        --values "charts/blacklist/values.yaml" \
        --values "charts/blacklist/values-${ENVIRONMENT}.yaml" \
        --set nameOverride="${HELM_RELEASE}-${new_color}" \
        --set fullnameOverride="${HELM_RELEASE}-${new_color}" \
        --set image.tag="${IMAGE_TAG:-latest}" \
        --wait --timeout 10m
    
    # 헬스 체크
    log "Running health checks on new environment..."
    local retries=30
    while [ $retries -gt 0 ]; do
        if kubectl exec -n "$NAMESPACE" deployment/${HELM_RELEASE}-${new_color} -- \
            curl -f http://localhost:8541/health &>/dev/null; then
            success "Health check passed"
            break
        fi
        retries=$((retries - 1))
        sleep 10
    done
    
    if [ $retries -eq 0 ]; then
        error "Health check failed for new environment"
    fi
    
    # 트래픽 전환
    log "Switching traffic to new environment..."
    kubectl patch service ${HELM_RELEASE} -n "$NAMESPACE" -p \
        "{\"spec\":{\"selector\":{\"app\":\"blacklist\",\"version\":\"${new_color}\"}}}"
    
    # 이전 환경 정리 (옵션)
    read -p "Remove old environment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        helm uninstall "${HELM_RELEASE}-${current_color}" -n "$NAMESPACE" || true
    fi
    
    success "Blue-green deployment completed"
}

# Canary 배포 전략
deploy_canary() {
    log "Performing canary deployment with Flagger..."
    
    # Flagger 설치 확인
    if ! kubectl get crd canaries.flagger.app &>/dev/null; then
        warning "Flagger not installed. Installing..."
        kubectl apply -k github.com/fluxcd/flagger//kustomize/linkerd
    fi
    
    # Canary 리소스 생성/업데이트
    cat <<EOF | kubectl apply -f -
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: ${HELM_RELEASE}
  namespace: ${NAMESPACE}
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${HELM_RELEASE}
  service:
    port: 8541
    targetPort: 8541
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 30s
EOF
    
    # 이미지 업데이트로 Canary 배포 시작
    kubectl set image deployment/${HELM_RELEASE} \
        ${IMAGE_NAME}="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG:-latest}" \
        -n "$NAMESPACE"
    
    # Canary 진행 상황 모니터링
    log "Monitoring canary deployment progress..."
    while true; do
        local status=$(kubectl get canary/${HELM_RELEASE} -n "$NAMESPACE" \
            -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
        
        log "Canary status: $status"
        
        case $status in
            "Succeeded")
                success "Canary deployment succeeded!"
                break
                ;;
            "Failed")
                error "Canary deployment failed!"
                ;;
            "Unknown"|"")
                warning "Canary status unknown, waiting..."
                ;;
        esac
        
        sleep 30
    done
}

# ArgoCD를 통한 GitOps 배포
deploy_with_argocd() {
    log "Deploying with ArgoCD (GitOps)..."
    
    # ArgoCD Application 생성/업데이트
    cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${HELM_RELEASE}-${ENVIRONMENT}
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/jclee/blacklist
    targetRevision: HEAD
    path: k8s/overlays/${ENVIRONMENT}
  destination:
    server: https://kubernetes.default.svc
    namespace: ${NAMESPACE}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
EOF
    
    # 동기화 트리거
    argocd app sync "${HELM_RELEASE}-${ENVIRONMENT}" --grpc-web
    
    # 동기화 대기
    argocd app wait "${HELM_RELEASE}-${ENVIRONMENT}" --health --grpc-web
    
    success "ArgoCD deployment completed"
}

# 배포 후 검증
post_deployment_validation() {
    log "Running post-deployment validation..."
    
    # Pod 상태 확인
    kubectl get pods -n "$NAMESPACE" -l app=blacklist
    
    # 서비스 엔드포인트 확인
    local endpoints=$(kubectl get endpoints ${HELM_RELEASE} -n "$NAMESPACE" \
        -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
    
    if [ "$endpoints" -eq 0 ]; then
        error "No healthy endpoints found"
    fi
    
    log "Found $endpoints healthy endpoints"
    
    # 기본 기능 테스트
    log "Running smoke tests..."
    
    # 헬스 체크
    kubectl run smoke-test-health --rm -i --restart=Never \
        --image=curlimages/curl:latest -n "$NAMESPACE" -- \
        curl -f "http://${HELM_RELEASE}:8541/health" || \
        error "Health check failed"
    
    # API 테스트
    kubectl run smoke-test-api --rm -i --restart=Never \
        --image=curlimages/curl:latest -n "$NAMESPACE" -- \
        curl -f "http://${HELM_RELEASE}:8541/api/stats" || \
        warning "API test failed"
    
    success "Post-deployment validation completed"
}

# 모니터링 설정
setup_monitoring() {
    log "Setting up monitoring..."
    
    # ServiceMonitor 생성 (Prometheus Operator가 설치된 경우)
    if kubectl get crd servicemonitors.monitoring.coreos.com &>/dev/null; then
        kubectl apply -f k8s/base/servicemonitor.yaml -n "$NAMESPACE"
        success "ServiceMonitor created"
    fi
    
    # Grafana 대시보드 설정
    if kubectl get service grafana -n monitoring &>/dev/null; then
        kubectl create configmap blacklist-dashboard \
            --from-file=k8s/monitoring/dashboards/blacklist-dashboard.json \
            -n monitoring --dry-run=client -o yaml | kubectl apply -f -
        success "Grafana dashboard configured"
    fi
    
    # 알림 규칙 설정
    kubectl apply -f k8s/monitoring/alerts/blacklist-alerts.yaml -n "$NAMESPACE" || \
        warning "Failed to apply alert rules"
}

# 롤백 함수
rollback() {
    log "Rolling back deployment..."
    
    case $DEPLOYMENT_STRATEGY in
        rolling)
            kubectl rollout undo deployment/${HELM_RELEASE} -n "$NAMESPACE"
            kubectl rollout status deployment/${HELM_RELEASE} -n "$NAMESPACE"
            ;;
        helm)
            helm rollback ${HELM_RELEASE} -n "$NAMESPACE"
            ;;
        argocd)
            argocd app rollback "${HELM_RELEASE}-${ENVIRONMENT}" --grpc-web
            ;;
        *)
            error "Rollback not supported for strategy: $DEPLOYMENT_STRATEGY"
            ;;
    esac
    
    success "Rollback completed"
}

# 메인 실행 함수
main() {
    log "Starting Kubernetes Native Deployment"
    log "Environment: $ENVIRONMENT"
    log "Strategy: $DEPLOYMENT_STRATEGY"
    
    # 사전 요구사항 확인
    check_prerequisites
    
    # 환경 설정 적용
    apply_environment_config
    
    # 배포 전략에 따른 실행
    case $DEPLOYMENT_STRATEGY in
        rolling)
            deploy_rolling_update
            ;;
        blue-green)
            deploy_blue_green
            ;;
        canary)
            deploy_canary
            ;;
        helm)
            deploy_with_helm
            ;;
        argocd|gitops)
            deploy_with_argocd
            ;;
        *)
            # 기본: Kustomize + kubectl
            local manifest_file=$(build_and_validate_manifests)
            kubectl apply -f "$manifest_file"
            kubectl wait --for=condition=available --timeout=600s \
                deployment -l app=blacklist -n "$NAMESPACE"
            ;;
    esac
    
    # 배포 후 검증
    post_deployment_validation
    
    # 모니터링 설정
    setup_monitoring
    
    success "Deployment completed successfully!"
    
    # 배포 정보 출력
    echo
    log "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Namespace: $NAMESPACE"
    echo "  Strategy: $DEPLOYMENT_STRATEGY"
    echo "  Image: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG:-latest}"
    echo
    
    # 접속 정보 출력
    local ingress_host=$(kubectl get ingress -n "$NAMESPACE" \
        -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "N/A")
    
    if [ "$ingress_host" != "N/A" ]; then
        log "Application URL: https://$ingress_host"
    else
        log "Port-forward to access the application:"
        echo "  kubectl port-forward -n $NAMESPACE svc/${HELM_RELEASE} 8541:8541"
    fi
}

# 명령행 인자 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--strategy)
            DEPLOYMENT_STRATEGY="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --rollback)
            rollback
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Deployment environment (development|staging|production)"
            echo "  -s, --strategy STRATEGY  Deployment strategy (rolling|blue-green|canary|helm|argocd)"
            echo "  -t, --tag TAG           Image tag to deploy"
            echo "  -n, --namespace NS      Kubernetes namespace"
            echo "  --rollback              Rollback the last deployment"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# 메인 함수 실행
main
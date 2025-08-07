#!/bin/bash

# Deploy using jclee.me infrastructure
# This script configures and deploys the application using:
# - argo.jclee.me (ArgoCD)
# - charts.jclee.me (Helm Charts)
# - registry.jclee.me (Docker Registry)

set -e

# Configuration
NAMESPACE="blacklist"
ARGOCD_SERVER="argo.jclee.me"
HELM_REPO="https://charts.jclee.me"
DOCKER_REGISTRY="registry.jclee.me"
APP_NAME="blacklist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed"
    fi
    
    # Check argocd CLI
    if ! command -v argocd &> /dev/null; then
        warning "argocd CLI not installed. Installing..."
        curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        sudo install -m 555 /tmp/argocd /usr/local/bin/argocd
        rm /tmp/argocd
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        warning "helm not installed. Some features may not work."
    fi
    
    log "Prerequisites check completed"
}

# Test connectivity to jclee.me infrastructure
test_connectivity() {
    log "Testing connectivity to jclee.me infrastructure..."
    
    # Test ArgoCD
    if curl -k -s -o /dev/null -w "%{http_code}" https://${ARGOCD_SERVER} | grep -q "200\|302\|401"; then
        log "✅ ArgoCD server (${ARGOCD_SERVER}) is reachable"
    else
        warning "⚠️  ArgoCD server might not be accessible"
    fi
    
    # Test Helm repo
    if curl -s -o /dev/null -w "%{http_code}" ${HELM_REPO}/index.yaml | grep -q "200\|404"; then
        log "✅ Helm repository (${HELM_REPO}) is reachable"
    else
        warning "⚠️  Helm repository might not be accessible"
    fi
    
    # Test Docker registry
    if curl -k -s -o /dev/null -w "%{http_code}" https://${DOCKER_REGISTRY}/v2/ | grep -q "200\|401"; then
        log "✅ Docker registry (${DOCKER_REGISTRY}) is reachable"
    else
        warning "⚠️  Docker registry might not be accessible"
    fi
}

# Create namespace if it doesn't exist
create_namespace() {
    log "Creating namespace ${NAMESPACE}..."
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
}

# Setup registry credentials
setup_registry_credentials() {
    log "Setting up registry credentials..."
    
    # Check if credentials exist
    if kubectl get secret regcred -n ${NAMESPACE} &> /dev/null; then
        log "Registry credentials already exist"
    else
        if [[ -z "$DOCKER_USERNAME" ]] || [[ -z "$DOCKER_PASSWORD" ]]; then
            warning "DOCKER_USERNAME or DOCKER_PASSWORD not set. Skipping registry credential setup."
            return
        fi
        
        kubectl create secret docker-registry regcred \
            --docker-server=${DOCKER_REGISTRY} \
            --docker-username=${DOCKER_USERNAME} \
            --docker-password=${DOCKER_PASSWORD} \
            --namespace=${NAMESPACE}
        
        log "Registry credentials created"
    fi
}

# Add Helm repository
setup_helm_repo() {
    if command -v helm &> /dev/null; then
        log "Adding Helm repository..."
        helm repo add jclee-charts ${HELM_REPO} || true
        helm repo update
        log "Helm repository configured"
    fi
}

# Deploy ArgoCD application
deploy_argocd_app() {
    log "Deploying ArgoCD application..."
    
    # Apply ArgoCD application
    kubectl apply -f argocd/blacklist-app-jclee.yaml
    
    log "ArgoCD application deployed"
    
    # Check application status
    if command -v argocd &> /dev/null; then
        log "Waiting for application to sync..."
        sleep 5
        
        # Try to login to ArgoCD (may require manual auth)
        if argocd login ${ARGOCD_SERVER} --grpc-web --insecure --username admin 2>/dev/null; then
            argocd app sync ${APP_NAME} || true
            argocd app wait ${APP_NAME} --timeout 300 || true
        else
            warning "Could not login to ArgoCD. Please check the application status manually."
        fi
    fi
}

# Deploy Helm chart (alternative method)
deploy_helm_chart() {
    if command -v helm &> /dev/null && [[ "$1" == "--helm" ]]; then
        log "Deploying via Helm chart..."
        
        # Package local chart
        if [[ -d "charts/blacklist" ]]; then
            helm package charts/blacklist
            
            # Push to repository if possible
            if command -v helm-push &> /dev/null; then
                helm push blacklist-*.tgz jclee-charts
            else
                warning "helm-push plugin not installed. Cannot push chart to repository."
            fi
        fi
        
        # Deploy from repository
        helm upgrade --install ${APP_NAME} jclee-charts/blacklist \
            --namespace ${NAMESPACE} \
            --create-namespace \
            --set image.repository=${DOCKER_REGISTRY}/jclee94/blacklist \
            --set image.tag=latest
        
        log "Helm deployment completed"
    fi
}

# Configure ArgoCD to use Helm repository
configure_argocd_helm() {
    log "Configuring ArgoCD to use Helm repository..."
    kubectl apply -f argocd/helm-repo-config.yaml
}

# Main deployment flow
main() {
    log "Starting deployment to jclee.me infrastructure"
    
    check_prerequisites
    test_connectivity
    create_namespace
    setup_registry_credentials
    setup_helm_repo
    configure_argocd_helm
    
    # Choose deployment method
    if [[ "$1" == "--helm" ]]; then
        deploy_helm_chart --helm
    else
        deploy_argocd_app
    fi
    
    log "Deployment completed!"
    log ""
    log "Access points:"
    log "  - ArgoCD: https://${ARGOCD_SERVER}"
    log "  - Application: https://blacklist.jclee.me (once deployed)"
    log ""
    log "To check status:"
    log "  kubectl get pods -n ${NAMESPACE}"
    log "  argocd app get ${APP_NAME}"
}

# Run main function
main "$@"
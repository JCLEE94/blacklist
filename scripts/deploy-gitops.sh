#!/bin/bash

# GitOps Deployment Script
# Ensures successful GitOps deployment

set -e

echo "🚀 GitOps Deployment Script"
echo "=========================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
        exit 1
    fi
    
    # Check if ArgoCD CLI is installed (optional)
    if command -v argocd &> /dev/null; then
        echo -e "${GREEN}✅ ArgoCD CLI found${NC}"
        ARGOCD_CLI=true
    else
        echo -e "${YELLOW}⚠️ ArgoCD CLI not found (optional)${NC}"
        ARGOCD_CLI=false
    fi
    
    echo -e "${GREEN}✅ Prerequisites check complete${NC}"
}

# Deploy K8s manifests
deploy_k8s() {
    echo -e "${YELLOW}📦 Deploying Kubernetes manifests...${NC}"
    
    # Apply manifests using Kustomize
    kubectl apply -k k8s/manifests/
    
    echo -e "${GREEN}✅ Kubernetes manifests deployed${NC}"
}

# Deploy ArgoCD application
deploy_argocd() {
    echo -e "${YELLOW}🔄 Deploying ArgoCD application...${NC}"
    
    # Check if ArgoCD namespace exists
    if kubectl get namespace argocd &> /dev/null; then
        echo "ArgoCD namespace found"
        
        # Apply ArgoCD application
        kubectl apply -f k8s/manifests/00-argocd-app.yaml
        
        echo -e "${GREEN}✅ ArgoCD application deployed${NC}"
        
        # Sync if ArgoCD CLI is available
        if [ "$ARGOCD_CLI" = true ]; then
            echo "Syncing ArgoCD application..."
            argocd app sync blacklist --timeout 300 || true
            argocd app wait blacklist --health --timeout 300 || true
        fi
    else
        echo -e "${YELLOW}⚠️ ArgoCD namespace not found. Skipping ArgoCD deployment.${NC}"
        echo "To install ArgoCD:"
        echo "kubectl create namespace argocd"
        echo "kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
    fi
}

# Check deployment status
check_status() {
    echo -e "${YELLOW}📊 Checking deployment status...${NC}"
    
    # Check pods
    echo "Pods in blacklist namespace:"
    kubectl get pods -n blacklist
    
    # Check services
    echo ""
    echo "Services:"
    kubectl get svc -n blacklist
    
    # Check ingress
    echo ""
    echo "Ingress:"
    kubectl get ingress -n blacklist
    
    # Get pod logs (last 10 lines)
    echo ""
    echo "Recent logs from blacklist pod:"
    kubectl logs -n blacklist -l app.kubernetes.io/name=blacklist --tail=10 || true
}

# Main execution
main() {
    echo "Starting GitOps deployment for Blacklist application"
    echo ""
    
    check_prerequisites
    echo ""
    
    # Parse arguments
    case "${1:-all}" in
        k8s)
            deploy_k8s
            ;;
        argocd)
            deploy_argocd
            ;;
        status)
            check_status
            ;;
        all)
            deploy_k8s
            echo ""
            deploy_argocd
            echo ""
            check_status
            ;;
        *)
            echo "Usage: $0 [k8s|argocd|status|all]"
            echo "  k8s    - Deploy Kubernetes manifests only"
            echo "  argocd - Deploy ArgoCD application only"
            echo "  status - Check deployment status"
            echo "  all    - Deploy everything (default)"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}🎉 Deployment script completed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Check application health: curl http://blacklist.jclee.me/health"
    echo "2. View ArgoCD dashboard: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "3. Monitor pods: kubectl logs -f -n blacklist -l app.kubernetes.io/name=blacklist"
}

# Run main function
main "$@"
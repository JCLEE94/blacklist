#!/bin/bash

# GitOps Setup Script with External ArgoCD
# This script configures GitOps using argo.jclee.me

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"
APP_NAMESPACE="blacklist"
REPO_URL="git@github.com:JCLEE94/blacklist.git"
REGISTRY="registry.jclee.me"
CHART_REPO="charts.jclee.me"

echo -e "${BLUE}=== GitOps Setup with External ArgoCD ===${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command_exists kubectl; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

if ! command_exists argocd; then
    echo -e "${YELLOW}Warning: ArgoCD CLI not found. Installing...${NC}"
    curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    chmod +x /tmp/argocd
    sudo mv /tmp/argocd /usr/local/bin/argocd
    echo -e "${GREEN}ArgoCD CLI installed${NC}"
fi

# 1. Login to external ArgoCD
echo -e "\n${YELLOW}1. Logging in to ArgoCD at $ARGOCD_SERVER...${NC}"
argocd login $ARGOCD_SERVER \
    --username $ARGOCD_USERNAME \
    --password $ARGOCD_PASSWORD \
    --grpc-web

# 2. Create application namespace if not exists
echo -e "\n${YELLOW}2. Creating application namespace...${NC}"
kubectl create namespace $APP_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 3. Create registry secret with authentication
echo -e "\n${YELLOW}3. Creating registry secret...${NC}"
kubectl create secret docker-registry regcred \
    --docker-server=$REGISTRY \
    --docker-username=admin \
    --docker-password=bingogo1 \
    --docker-email=admin@jclee.me \
    -n $APP_NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

# 4. Add Git repository to ArgoCD
echo -e "\n${YELLOW}4. Adding Git repository to ArgoCD...${NC}"
if argocd repo list | grep -q "$REPO_URL"; then
    echo -e "${GREEN}Repository already added${NC}"
else
    # Check if SSH key exists
    if [ ! -f ~/.ssh/id_rsa ]; then
        echo -e "${RED}Error: SSH key not found. Please setup GitHub SSH key first${NC}"
        exit 1
    fi
    
    argocd repo add $REPO_URL --ssh-private-key-path ~/.ssh/id_rsa
fi

# 5. Add Helm repository to ArgoCD
echo -e "\n${YELLOW}5. Adding Helm repository to ArgoCD...${NC}"

# Create repository secret for charts.jclee.me
cat <<EOF > /tmp/helm-repo-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: charts-jclee-me
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  url: https://$CHART_REPO
  name: jclee-charts
  username: admin
  password: bingogo1
EOF

# Apply the secret (requires access to ArgoCD namespace)
if kubectl get namespace argocd >/dev/null 2>&1; then
    kubectl apply -f /tmp/helm-repo-secret.yaml
    echo -e "${GREEN}✓ Helm repository secret created${NC}"
else
    echo -e "${YELLOW}⚠ Cannot create Helm repo secret - ArgoCD namespace not accessible${NC}"
    echo -e "  You may need to add the Helm repository manually in ArgoCD UI"
fi

rm -f /tmp/helm-repo-secret.yaml

# 6. Create ArgoCD application
echo -e "\n${YELLOW}6. Creating ArgoCD application...${NC}"

# Update ArgoCD application to use external server
cat <<EOF > /tmp/blacklist-app-external.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: blacklist
  namespace: argocd
  annotations:
    # Image Updater settings
    argocd-image-updater.argoproj.io/image-list: blacklist=$REGISTRY/blacklist:latest
    argocd-image-updater.argoproj.io/write-back-method: git
    argocd-image-updater.argoproj.io/git-branch: main
    argocd-image-updater.argoproj.io/blacklist.update-strategy: latest
    argocd-image-updater.argoproj.io/blacklist.pull-secret: namespace:blacklist:regcred
    # Helm specific settings
    argocd-image-updater.argoproj.io/blacklist.helm.image-name: image.repository
    argocd-image-updater.argoproj.io/blacklist.helm.image-tag: image.tag
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  
  source:
    repoURL: https://$CHART_REPO
    chart: blacklist
    targetRevision: "*"
    helm:
      values: |
        image:
          repository: $REGISTRY/blacklist
          tag: latest
        
        imagePullSecrets:
          - name: regcred
        
        service:
          type: NodePort
          nodePort: 32452
        
        config:
          logLevel: WARNING
          flaskEnv: production
          collectionEnabled: true
        
        persistence:
          enabled: true
          size: 20Gi
  
  destination:
    server: https://kubernetes.default.svc
    namespace: blacklist
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - ApplyOutOfSyncOnly=true
      - ServerSideApply=true
    
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 1m
EOF

# Create application via ArgoCD CLI
argocd app create -f /tmp/blacklist-app-external.yaml
rm -f /tmp/blacklist-app-external.yaml

# 7. Sync application
echo -e "\n${YELLOW}7. Syncing application...${NC}"
argocd app sync blacklist

# 8. Check application status
echo -e "\n${YELLOW}8. Checking application status...${NC}"
argocd app get blacklist

echo -e "\n${GREEN}=== GitOps Setup Complete ===${NC}"
echo -e "${BLUE}ArgoCD Server: https://$ARGOCD_SERVER${NC}"
echo -e "${BLUE}Username: $ARGOCD_USERNAME${NC}"
echo -e "${BLUE}Password: $ARGOCD_PASSWORD${NC}"
echo -e "\n${BLUE}To check application status:${NC}"
echo -e "  argocd app get blacklist"
echo -e "  kubectl get pods -n blacklist"
echo -e "\n${BLUE}To view ArgoCD dashboard:${NC}"
echo -e "  Open: https://$ARGOCD_SERVER"
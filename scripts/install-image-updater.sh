#!/bin/bash

# Install ArgoCD Image Updater
# This enables automatic image updates in GitOps workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Installing ArgoCD Image Updater ===${NC}"

# Check if ArgoCD is installed
if ! kubectl get namespace argocd >/dev/null 2>&1; then
    echo -e "${RED}Error: ArgoCD is not installed. Please run setup-gitops.sh first${NC}"
    exit 1
fi

# Install Image Updater
echo -e "\n${YELLOW}Installing ArgoCD Image Updater...${NC}"
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml

# Wait for deployment
echo -e "\n${YELLOW}Waiting for Image Updater to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/argocd-image-updater -n argocd

# Configure Image Updater for registry.jclee.me
echo -e "\n${YELLOW}Configuring Image Updater for registry.jclee.me...${NC}"

# Create ConfigMap for registries configuration
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-image-updater-config
  namespace: argocd
data:
  registries.conf: |
    registries:
    - name: registry.jclee.me
      api_url: https://registry.jclee.me
      prefix: registry.jclee.me
      insecure: yes
      defaultns: library
      default: true
    - name: Docker Hub
      api_url: https://registry-1.docker.io
      prefix: docker.io
      insecure: no
      defaultns: library
      default: false
  
  log.level: debug
EOF

# Restart Image Updater to apply configuration
echo -e "\n${YELLOW}Restarting Image Updater...${NC}"
kubectl rollout restart deployment/argocd-image-updater -n argocd
kubectl rollout status deployment/argocd-image-updater -n argocd

# Create RBAC for Image Updater to write back to Git
echo -e "\n${YELLOW}Configuring RBAC for Git write-back...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-image-updater
  namespace: argocd
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argocd-image-updater
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["argoproj.io"]
  resources: ["applications"]
  verbs: ["get", "list", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argocd-image-updater
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: argocd-image-updater
subjects:
- kind: ServiceAccount
  name: argocd-image-updater
  namespace: argocd
EOF

# Check installation
echo -e "\n${YELLOW}Verifying installation...${NC}"
if kubectl get deployment argocd-image-updater -n argocd >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ArgoCD Image Updater installed successfully${NC}"
    
    # Show logs
    echo -e "\n${BLUE}Recent logs:${NC}"
    kubectl logs deployment/argocd-image-updater -n argocd --tail=20
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== Installation Complete ===${NC}"
echo -e "${BLUE}Image Updater will now:${NC}"
echo -e "- Monitor registry.jclee.me for new images"
echo -e "- Automatically update applications with image updater annotations"
echo -e "- Write back changes to Git repository"
echo -e "\n${BLUE}To check Image Updater logs:${NC}"
echo -e "  kubectl logs -f deployment/argocd-image-updater -n argocd"
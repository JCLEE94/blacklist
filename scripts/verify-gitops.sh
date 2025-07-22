#!/bin/bash

# GitOps Verification Script
# This script verifies that GitOps is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GitOps Verification ===${NC}"

# 1. Check ArgoCD installation
echo -e "\n${YELLOW}1. Checking ArgoCD installation...${NC}"
if kubectl get namespace argocd >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ArgoCD namespace exists${NC}"
    kubectl get pods -n argocd --no-headers | while read line; do
        POD=$(echo $line | awk '{print $1}')
        STATUS=$(echo $line | awk '{print $3}')
        if [ "$STATUS" = "Running" ]; then
            echo -e "${GREEN}✓ $POD is running${NC}"
        else
            echo -e "${RED}✗ $POD status: $STATUS${NC}"
        fi
    done
else
    echo -e "${RED}✗ ArgoCD is not installed${NC}"
    exit 1
fi

# 2. Check ArgoCD application
echo -e "\n${YELLOW}2. Checking ArgoCD application...${NC}"
if kubectl get application blacklist -n argocd >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Blacklist application exists in ArgoCD${NC}"
    
    # Get application details
    APP_STATUS=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.sync.status}')
    APP_HEALTH=$(kubectl get application blacklist -n argocd -o jsonpath='{.status.health.status}')
    
    if [ "$APP_STATUS" = "Synced" ]; then
        echo -e "${GREEN}✓ Application sync status: $APP_STATUS${NC}"
    else
        echo -e "${YELLOW}⚠ Application sync status: $APP_STATUS${NC}"
    fi
    
    if [ "$APP_HEALTH" = "Healthy" ]; then
        echo -e "${GREEN}✓ Application health: $APP_HEALTH${NC}"
    else
        echo -e "${YELLOW}⚠ Application health: $APP_HEALTH${NC}"
    fi
else
    echo -e "${RED}✗ Blacklist application not found in ArgoCD${NC}"
fi

# 3. Check Kubernetes resources
echo -e "\n${YELLOW}3. Checking Kubernetes resources...${NC}"
NAMESPACE="blacklist"

if kubectl get namespace $NAMESPACE >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Application namespace exists${NC}"
    
    # Check deployments
    echo -e "\n  ${BLUE}Deployments:${NC}"
    kubectl get deployments -n $NAMESPACE --no-headers | while read line; do
        DEPLOYMENT=$(echo $line | awk '{print $1}')
        READY=$(echo $line | awk '{print $2}')
        echo -e "    $DEPLOYMENT: $READY"
    done
    
    # Check pods
    echo -e "\n  ${BLUE}Pods:${NC}"
    kubectl get pods -n $NAMESPACE --no-headers | while read line; do
        POD=$(echo $line | awk '{print $1}')
        STATUS=$(echo $line | awk '{print $3}')
        if [ "$STATUS" = "Running" ]; then
            echo -e "    ${GREEN}✓ $POD is running${NC}"
        else
            echo -e "    ${RED}✗ $POD status: $STATUS${NC}"
        fi
    done
    
    # Check services
    echo -e "\n  ${BLUE}Services:${NC}"
    kubectl get svc -n $NAMESPACE --no-headers | while read line; do
        SERVICE=$(echo $line | awk '{print $1}')
        TYPE=$(echo $line | awk '{print $2}')
        echo -e "    $SERVICE ($TYPE)"
    done
else
    echo -e "${RED}✗ Application namespace not found${NC}"
fi

# 4. Check Git repository configuration
echo -e "\n${YELLOW}4. Checking Git repository...${NC}"
if command -v argocd >/dev/null 2>&1; then
    # Port forward to ArgoCD
    kubectl port-forward svc/argocd-server -n argocd 8081:443 >/dev/null 2>&1 &
    PF_PID=$!
    sleep 3
    
    # Get admin password
    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d)
    
    if [ -n "$ARGOCD_PASSWORD" ]; then
        # Login to ArgoCD
        argocd login localhost:8081 --username admin --password "$ARGOCD_PASSWORD" --insecure >/dev/null 2>&1
        
        # Check repository
        if argocd repo list | grep -q "git@github.com:JCLEE94/blacklist.git"; then
            echo -e "${GREEN}✓ Git repository is configured${NC}"
        else
            echo -e "${RED}✗ Git repository not found${NC}"
        fi
    fi
    
    # Clean up
    kill $PF_PID 2>/dev/null
else
    echo -e "${YELLOW}⚠ ArgoCD CLI not installed, skipping repository check${NC}"
fi

# 5. Check Image Updater
echo -e "\n${YELLOW}5. Checking ArgoCD Image Updater...${NC}"
if kubectl get deployment argocd-image-updater -n argocd >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ArgoCD Image Updater is deployed${NC}"
    
    # Check if application has image updater annotations
    ANNOTATIONS=$(kubectl get application blacklist -n argocd -o jsonpath='{.metadata.annotations}' 2>/dev/null)
    if echo "$ANNOTATIONS" | grep -q "argocd-image-updater"; then
        echo -e "${GREEN}✓ Image Updater annotations are configured${NC}"
    else
        echo -e "${YELLOW}⚠ Image Updater annotations not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ ArgoCD Image Updater not installed${NC}"
    echo -e "  To install: kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml"
fi

# 6. Summary
echo -e "\n${BLUE}=== Summary ===${NC}"
echo -e "${GREEN}GitOps setup verification complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Push code changes to trigger CI/CD pipeline"
echo -e "2. Monitor ArgoCD dashboard for automatic deployment"
echo -e "3. Check application logs: kubectl logs -f deployment/blacklist -n blacklist"
#!/bin/bash
# NodePort 32542 GitOps Deployment Verification Script
# This script verifies the NodePort configuration across K8s and ArgoCD

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}NodePort 32542 GitOps Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check command existence
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${YELLOW}Warning: $1 is not installed${NC}"
        return 1
    fi
    return 0
}

# 1. Check Kubernetes Service Configuration
echo -e "${GREEN}1. Checking Kubernetes Service Configuration...${NC}"
if [ -f "k8s/manifests/07-service.yaml" ]; then
    echo "✓ Service manifest found"
    
    # Check NodePort configuration
    nodeport=$(grep -A1 "nodePort:" k8s/manifests/07-service.yaml | grep "32542" || echo "")
    if [ ! -z "$nodeport" ]; then
        echo -e "${GREEN}✓ NodePort 32542 configured in service manifest${NC}"
    else
        echo -e "${RED}✗ NodePort 32542 not found in service manifest${NC}"
    fi
    
    # Check service type
    service_type=$(grep "type:" k8s/manifests/07-service.yaml | grep "NodePort" || echo "")
    if [ ! -z "$service_type" ]; then
        echo -e "${GREEN}✓ Service type is NodePort${NC}"
    else
        echo -e "${RED}✗ Service type is not NodePort${NC}"
    fi
else
    echo -e "${RED}✗ Service manifest not found${NC}"
fi
echo ""

# 2. Check ArgoCD Application Configuration
echo -e "${GREEN}2. Checking ArgoCD Application Configuration...${NC}"
if [ -f "k8s/argocd/blacklist-app.yaml" ]; then
    echo "✓ ArgoCD application manifest found"
    
    # Check sync policy
    auto_sync=$(grep "automated:" k8s/argocd/blacklist-app.yaml || echo "")
    if [ ! -z "$auto_sync" ]; then
        echo -e "${GREEN}✓ Auto-sync enabled in ArgoCD${NC}"
    else
        echo -e "${YELLOW}⚠ Auto-sync not configured${NC}"
    fi
    
    # Check namespace
    namespace=$(grep "namespace: blacklist" k8s/argocd/blacklist-app.yaml || echo "")
    if [ ! -z "$namespace" ]; then
        echo -e "${GREEN}✓ Correct namespace configured${NC}"
    else
        echo -e "${RED}✗ Namespace not correctly configured${NC}"
    fi
else
    echo -e "${RED}✗ ArgoCD application manifest not found${NC}"
fi
echo ""

# 3. Check Docker Compose Configuration
echo -e "${GREEN}3. Checking Docker Compose Configuration...${NC}"
if [ -f "docker-compose.yml" ]; then
    echo "✓ Docker Compose file found"
    
    # Check port mapping
    port_mapping=$(grep "32542:2542" docker-compose.yml || echo "")
    if [ ! -z "$port_mapping" ]; then
        echo -e "${GREEN}✓ Port mapping 32542:2542 configured${NC}"
    else
        echo -e "${RED}✗ Port mapping not found${NC}"
    fi
else
    echo -e "${RED}✗ Docker Compose file not found${NC}"
fi
echo ""

# 4. Check if kubectl is available and cluster is accessible
echo -e "${GREEN}4. Checking Kubernetes Cluster Access...${NC}"
if check_command kubectl; then
    # Check if we can access the cluster
    if kubectl cluster-info &> /dev/null; then
        echo -e "${GREEN}✓ Kubernetes cluster is accessible${NC}"
        
        # Check if namespace exists
        if kubectl get namespace blacklist &> /dev/null; then
            echo -e "${GREEN}✓ Namespace 'blacklist' exists${NC}"
            
            # Check if service exists
            if kubectl get service blacklist -n blacklist &> /dev/null; then
                echo -e "${GREEN}✓ Service 'blacklist' exists${NC}"
                
                # Get actual NodePort
                actual_nodeport=$(kubectl get service blacklist -n blacklist -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
                if [ "$actual_nodeport" == "32542" ]; then
                    echo -e "${GREEN}✓ NodePort 32542 is active in cluster${NC}"
                    
                    # Get node IPs
                    echo ""
                    echo -e "${BLUE}Service is accessible at:${NC}"
                    kubectl get nodes -o wide | awk 'NR>1 {print "  http://"$6":32542"}' 2>/dev/null || echo "  Unable to retrieve node IPs"
                else
                    echo -e "${YELLOW}⚠ Active NodePort is $actual_nodeport (expected 32542)${NC}"
                fi
            else
                echo -e "${YELLOW}⚠ Service 'blacklist' not found in namespace${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ Namespace 'blacklist' does not exist${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Cannot access Kubernetes cluster${NC}"
    fi
else
    echo -e "${YELLOW}⚠ kubectl not installed - cannot verify cluster state${NC}"
fi
echo ""

# 5. Check ArgoCD Application Status
echo -e "${GREEN}5. Checking ArgoCD Application Status...${NC}"
if check_command argocd; then
    # Check if logged in to ArgoCD
    if argocd app list &> /dev/null; then
        # Check application status
        if argocd app get blacklist &> /dev/null; then
            echo -e "${GREEN}✓ ArgoCD application 'blacklist' found${NC}"
            
            # Get sync status
            sync_status=$(argocd app get blacklist -o json | jq -r '.status.sync.status' 2>/dev/null || echo "Unknown")
            health_status=$(argocd app get blacklist -o json | jq -r '.status.health.status' 2>/dev/null || echo "Unknown")
            
            echo "  Sync Status: $sync_status"
            echo "  Health Status: $health_status"
            
            if [ "$sync_status" == "Synced" ]; then
                echo -e "${GREEN}✓ Application is synced${NC}"
            else
                echo -e "${YELLOW}⚠ Application sync status: $sync_status${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ ArgoCD application 'blacklist' not found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Not logged in to ArgoCD${NC}"
        echo "  Run: argocd login argo.jclee.me"
    fi
else
    echo -e "${YELLOW}⚠ argocd CLI not installed${NC}"
fi
echo ""

# 6. Configuration Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Configuration Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Port Configuration:"
echo "  External Port (NodePort): 32542"
echo "  Internal Port (Container): 2542"
echo ""
echo "GitOps Components:"
echo "  ✓ Kubernetes Service: k8s/manifests/07-service.yaml"
echo "  ✓ ArgoCD Application: k8s/argocd/blacklist-app.yaml"
echo "  ✓ Docker Compose: docker-compose.yml"
echo ""
echo "Deployment Commands:"
echo "  Apply K8s manifests: kubectl apply -k k8s/manifests/"
echo "  Register with ArgoCD: kubectl apply -f k8s/argocd/blacklist-app.yaml"
echo "  Sync ArgoCD app: argocd app sync blacklist"
echo "  Docker deployment: docker-compose up -d"
echo ""

# 7. Test connectivity if service is running
echo -e "${GREEN}7. Testing Service Connectivity...${NC}"
if command -v curl &> /dev/null; then
    # Try localhost first (for Docker Compose)
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:32542/health | grep -q "200"; then
        echo -e "${GREEN}✓ Service is accessible at http://localhost:32542${NC}"
    else
        echo -e "${YELLOW}⚠ Service not accessible at localhost:32542${NC}"
    fi
    
    # Try to get node IP if kubectl is available
    if check_command kubectl; then
        node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || \
                  kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "")
        if [ ! -z "$node_ip" ]; then
            if curl -s -o /dev/null -w "%{http_code}" http://$node_ip:32542/health --max-time 5 | grep -q "200"; then
                echo -e "${GREEN}✓ Service is accessible at http://$node_ip:32542${NC}"
            else
                echo -e "${YELLOW}⚠ Service not accessible at $node_ip:32542${NC}"
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠ curl not installed - cannot test connectivity${NC}"
fi
echo ""

echo -e "${GREEN}Verification complete!${NC}"
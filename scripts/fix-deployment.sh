#!/bin/bash
# Fix CI/CD deployment issues

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

print_step "Fixing CI/CD Deployment Issues"
echo "================================"

# 1. Create registry secret
print_step "Creating registry secret..."
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=qws9411 \
  --docker-password=bingogo1 \
  -n blacklist \
  --dry-run=client -o yaml | kubectl apply -f -

print_success "Registry secret created"

# 2. Fix deployment to use registry secret
print_step "Updating deployment to use registry secret..."
kubectl patch deployment blacklist -n blacklist -p '{
  "spec": {
    "template": {
      "spec": {
        "imagePullSecrets": [
          {"name": "regcred"}
        ]
      }
    }
  }
}'

print_success "Deployment patched with imagePullSecrets"

# 3. Check deployment status
print_step "Checking deployment status..."
kubectl rollout status deployment/blacklist -n blacklist --timeout=300s

# 4. Get pod status
kubectl get pods -n blacklist

# 5. If still failing, restart deployment
if ! kubectl get pods -n blacklist | grep -q "Running"; then
    print_warning "Pods not running, restarting deployment..."
    kubectl rollout restart deployment/blacklist -n blacklist
    kubectl rollout status deployment/blacklist -n blacklist --timeout=300s
fi

print_success "Deployment fix completed!"
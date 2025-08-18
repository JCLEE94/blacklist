#!/bin/bash

# K8s Manifest Apply Script
# 표준화된 순서대로 매니페스트 적용

set -e

MANIFESTS_DIR="manifests"

echo "🚀 Applying Kubernetes manifests..."

# Apply using Kustomize
echo "📦 Applying with Kustomize..."
kubectl apply -k $MANIFESTS_DIR/

# Apply ArgoCD app separately (if using GitOps)
if [ "$1" == "--with-argocd" ]; then
    echo "🔄 Applying ArgoCD application..."
    kubectl apply -f $MANIFESTS_DIR/00-argocd-app.yaml
fi

echo "✅ All manifests applied successfully!"

# Check deployment status
echo ""
echo "📊 Checking deployment status..."
kubectl get all -n blacklist
kubectl get ingress -n blacklist

echo ""
echo "🔍 Pod status:"
kubectl get pods -n blacklist -o wide

echo ""
echo "✨ Deployment complete!"
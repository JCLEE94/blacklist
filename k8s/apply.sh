#!/bin/bash

# K8s Manifest Apply Script
# 표준화된 순서대로 매니페스트 적용

set -e

MANIFESTS_DIR="manifests"

echo "🚀 Applying Kubernetes manifests..."

# Apply in order
kubectl apply -f $MANIFESTS_DIR/01-namespace.yaml
kubectl apply -f $MANIFESTS_DIR/02-configmap.yaml
kubectl apply -f $MANIFESTS_DIR/03-secret.yaml
kubectl apply -f $MANIFESTS_DIR/04-pvc.yaml
kubectl apply -f $MANIFESTS_DIR/05-serviceaccount.yaml
kubectl apply -f $MANIFESTS_DIR/09-redis.yaml
kubectl apply -f $MANIFESTS_DIR/06-deployment.yaml
kubectl apply -f $MANIFESTS_DIR/07-service.yaml
kubectl apply -f $MANIFESTS_DIR/08-ingress.yaml

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
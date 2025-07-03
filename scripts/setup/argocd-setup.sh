#!/bin/bash

# ArgoCD CI/CD Pipeline Setup Script
# This script configures ArgoCD for automated deployment

set -e

# Configuration
ARGOCD_SERVER="argo.jclee.me"
ADMIN_USER="admin"
ADMIN_PASS="bingogo1"
NEW_USER="jclee"
NEW_USER_PASS="bingogo1"
GITHUB_USER="JCLEE94"
GITHUB_TOKEN="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"
REGISTRY_URL="registry.jclee.me"
REGISTRY_USER="qws9411"
REGISTRY_PASS="bingogo1"
NAMESPACE="argocd"
APP_NAME="blacklist"
APP_NAMESPACE="blacklist"

echo "🚀 Starting ArgoCD CI/CD Pipeline Setup..."

# 1. Login to ArgoCD
echo "📋 Step 1: Logging in to ArgoCD..."
argocd login $ARGOCD_SERVER --username $ADMIN_USER --password $ADMIN_PASS --insecure

# 2. Create user account
echo "📋 Step 2: Creating user account..."
kubectl patch configmap/argocd-cm -n $NAMESPACE --type merge -p '{
  "data": {
    "accounts.'$NEW_USER'": "apiKey, login",
    "accounts.'$NEW_USER'.enabled": "true"
  }
}'

# Set password for new user
argocd account update-password --account $NEW_USER --current-password $ADMIN_PASS --new-password $NEW_USER_PASS

# 3. Create GitHub repository credential
echo "📋 Step 3: Adding GitHub repository..."
argocd repo add https://github.com/$GITHUB_USER/blacklist.git \
  --username $GITHUB_USER \
  --password $GITHUB_TOKEN \
  --insecure-skip-server-verification

# 4. Create Docker registry secret
echo "📋 Step 4: Creating Docker registry secret..."
kubectl create secret docker-registry regcred \
  --docker-server=$REGISTRY_URL \
  --docker-username=$REGISTRY_USER \
  --docker-password=$REGISTRY_PASS \
  -n $APP_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 5. Create ArgoCD repository secret for private registry
echo "📋 Step 5: Configuring ArgoCD for private registry..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: private-registry
  namespace: $NAMESPACE
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  url: https://$REGISTRY_URL
  username: $REGISTRY_USER
  password: $REGISTRY_PASS
EOF

# 6. Create ArgoCD Application
echo "📋 Step 6: Creating ArgoCD Application..."
cat <<EOF > /tmp/argocd-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $APP_NAME
  namespace: $NAMESPACE
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/$GITHUB_USER/blacklist.git
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: $APP_NAMESPACE
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 3
EOF

kubectl apply -f /tmp/argocd-app.yaml

# 7. Configure ArgoCD Image Updater
echo "📋 Step 7: Installing ArgoCD Image Updater..."
kubectl apply -n $NAMESPACE -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml

# Wait for image updater to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-image-updater -n $NAMESPACE --timeout=300s

# 8. Configure image updater for our application
echo "📋 Step 8: Configuring image updater for automatic deployments..."
kubectl patch application $APP_NAME -n $NAMESPACE --type merge -p '{
  "metadata": {
    "annotations": {
      "argocd-image-updater.argoproj.io/image-list": "blacklist='$REGISTRY_URL'/blacklist:~latest",
      "argocd-image-updater.argoproj.io/blacklist.update-strategy": "latest",
      "argocd-image-updater.argoproj.io/blacklist.pull-secret": "pullsecret:blacklist/regcred",
      "argocd-image-updater.argoproj.io/write-back-method": "git",
      "argocd-image-updater.argoproj.io/git-branch": "main"
    }
  }
}'

# 9. Create RBAC policy for user
echo "📋 Step 9: Setting up RBAC policies..."
kubectl patch configmap/argocd-rbac-cm -n $NAMESPACE --type merge -p '{
  "data": {
    "policy.csv": "p, '$NEW_USER', applications, *, */*, allow\np, '$NEW_USER', clusters, *, *, allow\np, '$NEW_USER', repositories, *, *, allow\np, '$NEW_USER', certificates, *, *, allow\np, '$NEW_USER', projects, *, *, allow\ng, '$NEW_USER', role:admin"
  }
}'

# 10. Sync application
echo "📋 Step 10: Triggering initial sync..."
argocd app sync $APP_NAME

# Wait for sync to complete
argocd app wait $APP_NAME --sync

# 11. Verify deployment
echo "📋 Step 11: Verifying deployment..."
kubectl get pods -n $APP_NAMESPACE
argocd app get $APP_NAME

echo "✅ ArgoCD CI/CD Pipeline setup completed!"
echo ""
echo "📌 Important Information:"
echo "   - ArgoCD Server: https://$ARGOCD_SERVER"
echo "   - Username: $NEW_USER"
echo "   - Password: $NEW_USER_PASS"
echo "   - Application: $APP_NAME"
echo "   - Auto-sync: Enabled"
echo "   - Image Updater: Configured for $REGISTRY_URL/blacklist"
echo ""
echo "🔄 The pipeline will automatically:"
echo "   1. Monitor GitHub for code changes"
echo "   2. Detect new Docker images in the registry"
echo "   3. Update and deploy automatically"
echo "   4. Self-heal on configuration drift"
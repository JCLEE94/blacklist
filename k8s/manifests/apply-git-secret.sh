#!/bin/bash
# Apply Git Secret for ArgoCD with environment variable

if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN environment variable is not set"
  echo "Usage: export GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE"
  exit 1
fi

# Create the secret directly in cluster
kubectl create secret generic private-repo-blacklist \
  --namespace=argocd \
  --from-literal=type=git \
  --from-literal=url=https://github.com/JCLEE94/blacklist.git \
  --from-literal=username=JCLEE94 \
  --from-literal=password="$GITHUB_TOKEN" \
  --from-literal=insecure=false \
  --from-literal=enableLfs=false \
  --dry-run=client -o yaml | \
kubectl label -f - --local -o yaml argocd.argoproj.io/secret-type=repository | \
kubectl annotate -f - --local -o yaml argocd.argoproj.io/sync-wave="-10" | \
kubectl apply -f -

echo "Git secret applied successfully"
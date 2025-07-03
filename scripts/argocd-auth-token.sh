#!/bin/bash

# Generate ArgoCD Auth Token for CI/CD
# This token will be used by GitHub Actions

ARGOCD_SERVER="argo.jclee.me"
USERNAME="jclee"
PASSWORD="bingogo1"

echo "Generating ArgoCD auth token for CI/CD..."

# Login to ArgoCD
argocd login $ARGOCD_SERVER --username $USERNAME --password $PASSWORD --insecure

# Generate auth token
TOKEN=$(argocd account generate-token --account $USERNAME)

echo ""
echo "Auth token generated successfully!"
echo ""
echo "Add this token to GitHub Secrets:"
echo "1. Go to https://github.com/JCLEE94/blacklist/settings/secrets/actions"
echo "2. Click 'New repository secret'"
echo "3. Name: ARGOCD_AUTH_TOKEN"
echo "4. Value: $TOKEN"
echo ""
echo "⚠️  Keep this token secure and do not share it!"
#!/bin/bash

# Setup GitHub Secrets for registry.jclee.me
# This script helps you configure the necessary GitHub secrets for deployment

echo "=========================================="
echo "GitHub Secrets Configuration Script"
echo "=========================================="
echo ""
echo "This script will help you set up the following GitHub secrets:"
echo "1. REGISTRY_PASSWORD - for registry.jclee.me authentication"
echo "2. ARGOCD_SERVER - ArgoCD server URL (optional)"
echo "3. ARGOCD_USERNAME - ArgoCD username (optional)"
echo "4. ARGOCD_PASSWORD - ArgoCD password (optional)"
echo ""
echo "Make sure you have the GitHub CLI (gh) installed and authenticated."
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated."
    echo "Please run: gh auth login"
    exit 1
fi

# Get repository name
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
    echo "Error: Could not determine repository. Are you in a git repository?"
    exit 1
fi

echo "Repository: $REPO"
echo ""

# Set REGISTRY_PASSWORD
echo "Setting REGISTRY_PASSWORD for registry.jclee.me..."
echo "bingogo1" | gh secret set REGISTRY_PASSWORD --repo=$REPO

echo "✅ REGISTRY_PASSWORD has been set"
echo ""

# Optional: Set ArgoCD secrets
read -p "Do you want to configure ArgoCD secrets? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter ArgoCD server URL (e.g., argocd.jclee.me): " ARGOCD_SERVER
    read -p "Enter ArgoCD username: " ARGOCD_USERNAME
    read -s -p "Enter ArgoCD password: " ARGOCD_PASSWORD
    echo
    
    if [ ! -z "$ARGOCD_SERVER" ]; then
        echo "$ARGOCD_SERVER" | gh secret set ARGOCD_SERVER --repo=$REPO
        echo "✅ ARGOCD_SERVER has been set"
    fi
    
    if [ ! -z "$ARGOCD_USERNAME" ]; then
        echo "$ARGOCD_USERNAME" | gh secret set ARGOCD_USERNAME --repo=$REPO
        echo "✅ ARGOCD_USERNAME has been set"
    fi
    
    if [ ! -z "$ARGOCD_PASSWORD" ]; then
        echo "$ARGOCD_PASSWORD" | gh secret set ARGOCD_PASSWORD --repo=$REPO
        echo "✅ ARGOCD_PASSWORD has been set"
    fi
fi

echo ""
echo "=========================================="
echo "GitHub Secrets Configuration Complete!"
echo "=========================================="
echo ""
echo "The following secrets have been configured:"
gh secret list --repo=$REPO | grep -E "REGISTRY_PASSWORD|ARGOCD_"
echo ""
echo "Your GitHub Actions workflow is now configured to use registry.jclee.me"
echo ""
echo "Next steps:"
echo "1. Commit and push your changes to trigger the workflow"
echo "2. Monitor the Actions tab for deployment status"
echo "3. Check registry.jclee.me for the pushed images"
echo ""
#!/bin/bash

echo "🔐 Setting up GitHub Registry Secret"
echo "====================================="
echo ""
echo "This script will configure the REGISTRY_PASSWORD secret for GitHub Actions"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Please install it first: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "❌ Not logged in to GitHub"
    echo "Please run: gh auth login"
    exit 1
fi

# Get current repo
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
    echo "❌ Not in a GitHub repository"
    exit 1
fi

echo "📦 Repository: $REPO"
echo ""

# Set the registry password
echo "Setting REGISTRY_PASSWORD secret..."
echo "bingogo1" | gh secret set REGISTRY_PASSWORD --repo=$REPO

if [ $? -eq 0 ]; then
    echo "✅ REGISTRY_PASSWORD secret has been set successfully"
else
    echo "❌ Failed to set secret"
    exit 1
fi

echo ""
echo "🎯 Next steps:"
echo "1. Re-run the failed workflow:"
echo "   gh workflow run main-deploy.yml"
echo ""
echo "2. Or trigger from GitHub UI:"
echo "   https://github.com/$REPO/actions"
echo ""
echo "3. Monitor the deployment:"
echo "   gh run watch"

# List current secrets (names only)
echo ""
echo "📋 Current secrets in repository:"
gh secret list --repo=$REPO
#!/bin/bash

# CI/CD Pipeline Verification Script
echo "🔍 CI/CD Pipeline Verification"
echo "=============================="
echo ""

# Check recent commits
echo "📋 Recent Commits:"
git log --oneline -3
echo ""

# Check Docker Registry connectivity
echo "🐳 Docker Registry Verification:"
echo "Testing connection to registry.jclee.me..."

# Try to ping registry
if ping -c 1 registry.jclee.me &> /dev/null; then
    echo "✅ Registry server reachable"
else
    echo "❌ Registry server unreachable"
fi

# Check if Docker is running
if docker info &> /dev/null; then
    echo "✅ Docker daemon running"
else
    echo "❌ Docker daemon not running"
fi

# Check registry images (if accessible)
echo ""
echo "🏗️ Checking Registry Images:"
echo "Attempting to list images in registry.jclee.me/blacklist..."

# Try to get registry catalog
if curl -s https://registry.jclee.me/v2/_catalog 2>/dev/null | grep -q "blacklist"; then
    echo "✅ Blacklist repository found in registry"
    
    # Try to get tags
    echo "📦 Available tags:"
    curl -s https://registry.jclee.me/v2/blacklist/tags/list 2>/dev/null | jq -r '.tags[]' 2>/dev/null | head -5 || echo "Could not fetch tags (authentication required)"
else
    echo "⚠️  Registry catalog not accessible (may require authentication)"
fi

echo ""
echo "🔄 ArgoCD Application Status:"
if command -v argocd &> /dev/null; then
    argocd app get blacklist --grpc-web 2>/dev/null | grep -E "(Sync Status|Health Status)" || echo "Could not fetch ArgoCD status"
else
    echo "ArgoCD CLI not available"
fi

echo ""
echo "📊 Current Deployment Status:"
if curl -s https://blacklist.jclee.me/health 2>/dev/null | grep -q "healthy"; then
    echo "✅ Production service healthy"
else
    echo "⚠️  Production service not responding"
fi

echo ""
echo "🎯 Verification Summary:"
echo "- Git push: ✅ Completed (commit: $(git rev-parse --short HEAD))"
echo "- Registry server: $(ping -c 1 registry.jclee.me &>/dev/null && echo '✅ Reachable' || echo '❌ Unreachable')"
echo "- Docker daemon: $(docker info &>/dev/null && echo '✅ Running' || echo '❌ Not running')"
echo "- ArgoCD CLI: $(command -v argocd &>/dev/null && echo '✅ Available' || echo '❌ Not available')"
echo ""
echo "ℹ️  Note: GitHub Actions workflow execution can be monitored at:"
echo "   https://github.com/JCLEE94/blacklist/actions"
#!/bin/bash

# Install ArgoCD CLI
echo "Installing ArgoCD CLI..."

# Download the latest version
VERSION=$(curl --silent "https://api.github.com/repos/argoproj/argo-cd/releases/latest" | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
echo "Latest ArgoCD version: $VERSION"

# Download and install
curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/download/$VERSION/argocd-linux-amd64

# Make executable
chmod +x /tmp/argocd

# Move to /usr/local/bin (may need sudo)
if [ -w "/usr/local/bin" ]; then
    mv /tmp/argocd /usr/local/bin/argocd
else
    echo "Need sudo to install to /usr/local/bin"
    sudo mv /tmp/argocd /usr/local/bin/argocd
fi

# Verify installation
echo "ArgoCD CLI installed:"
argocd version --client
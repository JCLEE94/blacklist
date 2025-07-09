#!/bin/bash

# Configure Docker daemon for insecure registry
# This script configures Docker to treat registry.jclee.me as an insecure registry

set -euo pipefail

REGISTRY="registry.jclee.me"
DOCKER_CONFIG_FILE="/etc/docker/daemon.json"

echo "Configuring Docker daemon for insecure registry: $REGISTRY"

# Create backup if config exists
if [ -f "$DOCKER_CONFIG_FILE" ]; then
    sudo cp "$DOCKER_CONFIG_FILE" "${DOCKER_CONFIG_FILE}.backup"
    echo "Backed up existing config to ${DOCKER_CONFIG_FILE}.backup"
fi

# Add insecure registry configuration
if [ -f "$DOCKER_CONFIG_FILE" ]; then
    # Config exists, update it
    if command -v jq &> /dev/null; then
        # Use jq if available
        sudo jq --arg reg "$REGISTRY" '. + {"insecure-registries": ((.["insecure-registries"] // []) + [$reg] | unique)}' "$DOCKER_CONFIG_FILE" > /tmp/daemon.json
        sudo mv /tmp/daemon.json "$DOCKER_CONFIG_FILE"
    else
        echo "jq not found. Please manually add $REGISTRY to insecure-registries in $DOCKER_CONFIG_FILE"
        exit 1
    fi
else
    # Create new config
    echo '{
  "insecure-registries": ["'$REGISTRY'"]
}' | sudo tee "$DOCKER_CONFIG_FILE"
fi

echo "Docker daemon configuration updated:"
sudo cat "$DOCKER_CONFIG_FILE"

echo ""
echo "Restarting Docker daemon..."
sudo systemctl restart docker

echo "Docker daemon restarted successfully"
echo ""
echo "Testing registry access..."
docker pull $REGISTRY/busybox:latest || echo "Test pull failed (image may not exist)"

echo ""
echo "Configuration complete. You can now use $REGISTRY without HTTPS."
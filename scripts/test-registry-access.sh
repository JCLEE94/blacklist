#!/bin/bash

# Test registry access with various methods
set -euo pipefail

REGISTRY="registry.jclee.me"

echo "Testing registry access: $REGISTRY"
echo "=================================="

# Test 1: HTTP access
echo ""
echo "1. Testing HTTP access..."
curl -v http://$REGISTRY/v2/ 2>&1 | grep -E "(< HTTP|Location:|< location:)" || echo "HTTP test failed"

# Test 2: HTTPS access
echo ""
echo "2. Testing HTTPS access..."
curl -v https://$REGISTRY/v2/ 2>&1 | grep -E "(< HTTP|Location:|< location:)" || echo "HTTPS test failed"

# Test 3: Check if behind Cloudflare
echo ""
echo "3. Checking for Cloudflare Access..."
response=$(curl -sI https://$REGISTRY/v2/)
if echo "$response" | grep -q "cloudflareaccess.com"; then
    echo "⚠️  Registry is behind Cloudflare Access!"
    echo "Redirect URL:"
    echo "$response" | grep -i "location:" || true
else
    echo "✓ Registry is not behind Cloudflare Access"
fi

# Test 4: Docker registry API
echo ""
echo "4. Testing Docker Registry API..."
echo "Catalog endpoint:"
curl -s https://$REGISTRY/v2/_catalog | jq . 2>/dev/null || echo "Failed to get catalog"

# Test 5: Test with skopeo if available
echo ""
echo "5. Testing with skopeo (if available)..."
if command -v skopeo &> /dev/null; then
    skopeo inspect --tls-verify=false docker://$REGISTRY/busybox:latest 2>&1 || echo "Skopeo test failed"
else
    echo "Skopeo not installed"
fi

# Test 6: Direct registry push test
echo ""
echo "6. Testing direct Docker operations..."
echo "Pulling test image..."
docker pull busybox:latest

echo "Tagging for registry..."
docker tag busybox:latest $REGISTRY/test:latest

echo "Attempting push..."
docker push $REGISTRY/test:latest 2>&1 || echo "Push test failed"

echo ""
echo "=================================="
echo "Test complete"
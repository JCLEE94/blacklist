#!/bin/bash
# Post-deployment verification script for Blacklist System
# This script runs comprehensive health checks after deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
LOCAL_PORT=32542
PROD_URL="https://blacklist.jclee.me"
MAX_RETRIES=30
RETRY_INTERVAL=10

echo "🔍 POST-DEPLOYMENT VERIFICATION STARTED"
echo "========================================"
echo "Project: Blacklist Management System"
echo "Time: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
echo "========================================"

# Function to check endpoint health
check_endpoint() {
    local url="$1"
    local name="$2"
    local retries="$3"
    local interval="$4"
    
    echo "🏥 Checking $name health: $url"
    
    for i in $(seq 1 $retries); do
        if curl -sf "$url/health" > /dev/null 2>&1; then
            echo "✅ $name is healthy (attempt $i/$retries)"
            return 0
        fi
        
        if [ $i -eq $retries ]; then
            echo "❌ $name failed health check after $retries attempts"
            return 1
        fi
        
        echo "⏳ $name not ready yet, waiting ${interval}s (attempt $i/$retries)"
        sleep $interval
    done
}

# Function to run detailed API tests
run_api_tests() {
    local base_url="$1"
    local name="$2"
    
    echo "🧪 Running API tests for $name..."
    
    # Test basic health endpoint
    if ! curl -sf "$base_url/health" | jq . > /dev/null 2>&1; then
        echo "❌ Basic health check failed for $name"
        return 1
    fi
    
    # Test detailed health endpoint (if available)
    if curl -sf "$base_url/api/health" > /dev/null 2>&1; then
        echo "✅ Detailed health endpoint available"
    else
        echo "ℹ️ Detailed health endpoint not available (this is okay)"
    fi
    
    # Test blacklist API
    if curl -sf "$base_url/api/blacklist/active" > /dev/null 2>&1; then
        echo "✅ Blacklist API responding"
    else
        echo "⚠️ Blacklist API not responding (might be expected in test env)"
    fi
    
    echo "✅ API tests completed for $name"
    return 0
}

# Function to check Docker Compose status
check_docker_compose() {
    echo "🐳 Checking Docker Compose deployment..."
    
    if ! command -v docker-compose > /dev/null 2>&1; then
        echo "ℹ️ docker-compose not available, skipping local checks"
        return 0
    fi
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        echo "✅ Docker Compose services are running"
        
        # Show service status
        echo "📊 Service Status:"
        docker-compose ps
        
        return 0
    else
        echo "⚠️ Docker Compose services not running locally"
        return 1
    fi
}

# Function to check production deployment
check_production() {
    echo "🌐 Checking production deployment..."
    
    if check_endpoint "$PROD_URL" "Production" $MAX_RETRIES $RETRY_INTERVAL; then
        run_api_tests "$PROD_URL" "Production"
        return $?
    else
        return 1
    fi
}

# Function to check local deployment
check_local() {
    echo "🏠 Checking local deployment..."
    
    local local_url="http://localhost:$LOCAL_PORT"
    
    if check_endpoint "$local_url" "Local" 5 2; then
        run_api_tests "$local_url" "Local"
        return $?
    else
        echo "ℹ️ Local deployment not available (this is normal for CI/CD)"
        return 0
    fi
}

# Function to check registry images
check_registry_images() {
    echo "📦 Checking registry images..."
    
    local registry="registry.jclee.me"
    local image_name="blacklist"
    
    # Try to pull latest image to verify it exists
    if docker pull "$registry/$image_name:latest" > /dev/null 2>&1; then
        echo "✅ Latest image available in registry"
        
        # Check image metadata
        docker inspect "$registry/$image_name:latest" | jq -r '.[0].Config.Labels | to_entries[] | "\(.key): \(.value)"' 2>/dev/null || true
        
        return 0
    else
        echo "❌ Failed to pull latest image from registry"
        return 1
    fi
}

# Main verification flow
main() {
    local overall_status=0
    local results=()
    
    echo ""
    echo "🚀 Starting comprehensive verification..."
    echo ""
    
    # Check registry images
    if check_registry_images; then
        results+=("✅ Registry Images")
    else
        results+=("❌ Registry Images")
        overall_status=1
    fi
    
    echo ""
    
    # Check production deployment
    if check_production; then
        results+=("✅ Production Deployment")
    else
        results+=("❌ Production Deployment")
        overall_status=1
    fi
    
    echo ""
    
    # Check local deployment (optional)
    if check_local; then
        results+=("✅ Local Deployment")
    else
        results+=("⚠️ Local Deployment (optional)")
    fi
    
    echo ""
    
    # Check Docker Compose (optional)
    if check_docker_compose; then
        results+=("✅ Docker Compose")
    else
        results+=("⚠️ Docker Compose (optional)")
    fi
    
    # Print final results
    echo ""
    echo "📋 VERIFICATION RESULTS"
    echo "======================="
    
    for result in "${results[@]}"; do
        echo "$result"
    done
    
    echo ""
    
    if [ $overall_status -eq 0 ]; then
        echo "🎉 POST-DEPLOYMENT VERIFICATION PASSED"
        echo "All critical systems are healthy and responding correctly."
    else
        echo "❌ POST-DEPLOYMENT VERIFICATION FAILED"
        echo "Some critical systems are not responding correctly."
        echo "Please check the logs and investigate the issues."
    fi
    
    echo ""
    echo "🔗 Useful Links:"
    echo "Production: $PROD_URL"
    echo "Local: http://localhost:$LOCAL_PORT (if running)"
    echo "Portfolio: https://qws941.github.io/blacklist/"
    echo "========================================"
    
    exit $overall_status
}

# Run with error handling
if ! main "$@"; then
    echo ""
    echo "💡 TROUBLESHOOTING TIPS:"
    echo "1. Check Docker Compose logs: docker-compose logs"
    echo "2. Verify network connectivity: ping $PROD_URL"
    echo "3. Check service status: docker-compose ps"
    echo "4. Manual health check: curl $PROD_URL/health"
    echo ""
    exit 1
fi
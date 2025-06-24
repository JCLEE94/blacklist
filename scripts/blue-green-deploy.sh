#!/bin/bash
# Blue-Green Deployment Script
# Usage: ./blue-green-deploy.sh [blue|green] [IMAGE_TAG]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_DIR/deployment"

COLOR=${1:-blue}
IMAGE_TAG=${2:-latest}
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Function to get current active color
get_active_color() {
    if docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" ps app-blue | grep -q "Up"; then
        if docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" ps app-green | grep -q "Up"; then
            # Both are up, check nginx config
            if grep -q "app-blue:8541" "$DEPLOYMENT_DIR/nginx-blue-green.conf"; then
                echo "blue"
            else
                echo "green"
            fi
        else
            echo "blue"
        fi
    elif docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" ps app-green | grep -q "Up"; then
        echo "green"
    else
        echo "none"
    fi
}

# Function to wait for service health
wait_for_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    log "Waiting for $service to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" exec -T "$service" curl -f http://localhost:8541/health > /dev/null 2>&1; then
            log "$service is healthy!"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts..."
        sleep 10
        ((attempt++))
    done
    
    error "$service failed to become healthy after $max_attempts attempts"
}

# Function to switch nginx to target color
switch_nginx() {
    local target_color=$1
    
    log "Switching nginx to $target_color environment..."
    
    # Create backup of current config
    cp "$DEPLOYMENT_DIR/nginx-blue-green.conf" "$DEPLOYMENT_DIR/nginx-blue-green.conf.backup"
    
    # Update nginx config
    if [ "$target_color" = "blue" ]; then
        sed -i 's/server app-green:8541/# server app-green:8541/' "$DEPLOYMENT_DIR/nginx-blue-green.conf"
        sed -i 's/# server app-blue:8541/server app-blue:8541/' "$DEPLOYMENT_DIR/nginx-blue-green.conf"
    else
        sed -i 's/server app-blue:8541/# server app-blue:8541/' "$DEPLOYMENT_DIR/nginx-blue-green.conf"
        sed -i 's/# server app-green:8541/server app-green:8541/' "$DEPLOYMENT_DIR/nginx-blue-green.conf"
    fi
    
    # Reload nginx
    docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" exec nginx nginx -s reload
    
    log "Nginx switched to $target_color environment"
}

# Function to rollback nginx config
rollback_nginx() {
    warn "Rolling back nginx configuration..."
    
    if [ -f "$DEPLOYMENT_DIR/nginx-blue-green.conf.backup" ]; then
        cp "$DEPLOYMENT_DIR/nginx-blue-green.conf.backup" "$DEPLOYMENT_DIR/nginx-blue-green.conf"
        docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" exec nginx nginx -s reload
        log "Nginx configuration rolled back"
    else
        error "No backup configuration found for rollback"
    fi
}

# Function to perform smoke tests
smoke_tests() {
    local target_url=$1
    
    log "Running smoke tests against $target_url..."
    
    # Basic endpoints test
    local endpoints=("/health" "/api/stats" "/api/collection/status")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$target_url$endpoint" > /dev/null; then
            log "✅ $endpoint - OK"
        else
            error "❌ $endpoint - FAILED"
        fi
    done
    
    log "All smoke tests passed!"
}

# Main deployment function
deploy() {
    local target_color=$1
    local image_tag=$2
    local current_active
    
    current_active=$(get_active_color)
    log "Current active environment: $current_active"
    log "Deploying to: $target_color"
    log "Image tag: $image_tag"
    
    # Set environment variables
    export REGISTRY="$REGISTRY"
    export IMAGE_NAME="$IMAGE_NAME"
    
    if [ "$target_color" = "blue" ]; then
        export BLUE_VERSION="$image_tag"
        export GREEN_VERSION="${GREEN_VERSION:-latest}"
    else
        export GREEN_VERSION="$image_tag"
        export BLUE_VERSION="${BLUE_VERSION:-latest}"
    fi
    
    # Pull new image
    log "Pulling image: $REGISTRY/$IMAGE_NAME:$image_tag"
    docker pull "$REGISTRY/$IMAGE_NAME:$image_tag"
    
    # Start target environment
    log "Starting $target_color environment..."
    docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" up -d "app-$target_color"
    
    # Wait for target environment to be healthy
    wait_for_health "app-$target_color"
    
    # Run smoke tests on target environment directly
    local target_port
    if [ "$target_color" = "blue" ]; then
        target_port=$(docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" port app-blue 8541 | cut -d: -f2)
    else
        target_port=$(docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" port app-green 8541 | cut -d: -f2)
    fi
    
    smoke_tests "http://localhost:$target_port"
    
    # Switch traffic to target environment
    switch_nginx "$target_color"
    
    # Run smoke tests on public endpoint
    smoke_tests "http://localhost:2541"
    
    # Stop old environment if different
    if [ "$current_active" != "none" ] && [ "$current_active" != "$target_color" ]; then
        log "Stopping $current_active environment..."
        docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" stop "app-$current_active"
    fi
    
    log "🎉 Blue-green deployment completed successfully!"
    log "Active environment: $target_color"
    log "Application URL: http://localhost:2541"
}

# Function to show status
show_status() {
    log "Blue-Green Deployment Status"
    echo "==============================="
    
    local current_active
    current_active=$(get_active_color)
    echo "Active environment: $current_active"
    
    echo ""
    echo "Container Status:"
    docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" ps
    
    echo ""
    echo "Direct Access URLs:"
    echo "  Blue:  http://localhost:2541/blue/health"
    echo "  Green: http://localhost:2541/green/health"
    echo "  Load Balancer: http://localhost:2541/health"
}

# Function to cleanup
cleanup() {
    log "Cleaning up blue-green deployment..."
    
    docker-compose -f "$DEPLOYMENT_DIR/docker-compose.blue-green.yml" down --remove-orphans
    
    # Remove backup files
    rm -f "$DEPLOYMENT_DIR/nginx-blue-green.conf.backup"
    
    log "Cleanup completed"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy "$COLOR" "$IMAGE_TAG"
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup
        ;;
    "rollback")
        if [ -f "$DEPLOYMENT_DIR/nginx-blue-green.conf.backup" ]; then
            rollback_nginx
        else
            error "No backup found. Cannot rollback."
        fi
        ;;
    *)
        echo "Usage: $0 [deploy|status|cleanup|rollback] [blue|green] [image_tag]"
        echo ""
        echo "Commands:"
        echo "  deploy [blue|green] [tag]  - Deploy to specified environment"
        echo "  status                     - Show current deployment status"
        echo "  cleanup                    - Clean up all environments"
        echo "  rollback                   - Rollback to previous configuration"
        echo ""
        echo "Examples:"
        echo "  $0 deploy blue latest"
        echo "  $0 deploy green v1.2.3"
        echo "  $0 status"
        exit 1
        ;;
esac
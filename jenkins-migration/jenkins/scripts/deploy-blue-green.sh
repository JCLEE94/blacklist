#!/bin/bash

#################################################################################
# Blue-Green Deployment Script for Blacklist Management System
# Usage: ./deploy-blue-green.sh <version>
#################################################################################

set -e

# Configuration
VERSION=${1:-latest}
REGISTRY="registry.jclee.me"
IMAGE_NAME="blacklist"
PRODUCTION_PORT=32542
BLUE_PORT=32543
GREEN_PORT=32544
HEALTH_CHECK_RETRIES=12
HEALTH_CHECK_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check container health
check_health() {
    local port=$1
    local retries=$2
    
    for i in $(seq 1 $retries); do
        if curl -f http://localhost:${port}/health > /dev/null 2>&1; then
            return 0
        fi
        echo -e "${YELLOW}Health check attempt ${i}/${retries}...${NC}"
        sleep ${HEALTH_CHECK_INTERVAL}
    done
    return 1
}

# Function to get current deployment color
get_current_color() {
    if docker ps --format '{{.Names}}' | grep -q "blacklist-blue"; then
        echo "blue"
    elif docker ps --format '{{.Names}}' | grep -q "blacklist-green"; then
        echo "green"
    else
        echo "none"
    fi
}

# Function to deploy new version
deploy_new_version() {
    local color=$1
    local port=$2
    
    echo -e "${BLUE}Deploying to ${color} environment (port ${port})...${NC}"
    
    # Stop and remove old container if exists
    docker stop blacklist-${color} 2>/dev/null || true
    docker rm blacklist-${color} 2>/dev/null || true
    
    # Pull latest image
    docker pull ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    
    # Run new container
    docker run -d \
        --name blacklist-${color} \
        --network blacklist-network \
        -p ${port}:2541 \
        -e PORT=2541 \
        -e FLASK_ENV=production \
        -e DATABASE_URL=postgresql://blacklist:password@postgres:5432/blacklist \
        -e REDIS_URL=redis://redis:6379/0 \
        -v blacklist-data:/app/instance \
        --restart unless-stopped \
        --health-cmd="curl -f http://localhost:2541/health || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    
    echo -e "${GREEN}Container started successfully${NC}"
}

# Function to switch traffic
switch_traffic() {
    local new_color=$1
    local old_color=$2
    
    echo -e "${YELLOW}Switching traffic from ${old_color} to ${new_color}...${NC}"
    
    # Update nginx or load balancer configuration
    # For simplicity, we're using port-based switching
    
    # Stop old main container
    docker stop blacklist 2>/dev/null || true
    docker rm blacklist 2>/dev/null || true
    
    # Create new main container pointing to new color
    docker run -d \
        --name blacklist \
        --network blacklist-network \
        -p ${PRODUCTION_PORT}:2541 \
        -e PORT=2541 \
        -e FLASK_ENV=production \
        -e DATABASE_URL=postgresql://blacklist:password@postgres:5432/blacklist \
        -e REDIS_URL=redis://redis:6379/0 \
        -v blacklist-data:/app/instance \
        --restart unless-stopped \
        ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    
    echo -e "${GREEN}Traffic switched successfully${NC}"
}

# Function to cleanup old deployment
cleanup_old_deployment() {
    local color=$1
    
    echo -e "${YELLOW}Cleaning up ${color} deployment...${NC}"
    docker stop blacklist-${color} 2>/dev/null || true
    docker rm blacklist-${color} 2>/dev/null || true
    echo -e "${GREEN}Cleanup completed${NC}"
}

# Function to rollback deployment
rollback() {
    local color=$1
    
    echo -e "${RED}Rolling back to ${color} deployment...${NC}"
    
    # Restore previous deployment
    if [ "$color" != "none" ]; then
        switch_traffic $color $new_color
        cleanup_old_deployment $new_color
    fi
    
    echo -e "${RED}Rollback completed${NC}"
    exit 1
}

# Main deployment logic
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Blue-Green Deployment v${VERSION}${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Ensure Docker network exists
    docker network create blacklist-network 2>/dev/null || true
    
    # Get current deployment state
    current_color=$(get_current_color)
    echo -e "${BLUE}Current deployment: ${current_color}${NC}"
    
    # Determine new deployment color
    if [ "$current_color" == "blue" ]; then
        new_color="green"
        new_port=${GREEN_PORT}
        old_color="blue"
    elif [ "$current_color" == "green" ]; then
        new_color="blue"
        new_port=${BLUE_PORT}
        old_color="green"
    else
        # First deployment
        new_color="blue"
        new_port=${BLUE_PORT}
        old_color="none"
    fi
    
    echo -e "${BLUE}New deployment will be: ${new_color}${NC}"
    
    # Deploy new version
    deploy_new_version $new_color $new_port
    
    # Health check new deployment
    echo -e "${YELLOW}Performing health check on ${new_color} environment...${NC}"
    if check_health $new_port $HEALTH_CHECK_RETRIES; then
        echo -e "${GREEN}Health check passed!${NC}"
        
        # Smoke tests
        echo -e "${YELLOW}Running smoke tests...${NC}"
        if curl -s http://localhost:${new_port}/api/health | grep -q "healthy"; then
            echo -e "${GREEN}Smoke tests passed!${NC}"
            
            # Switch traffic
            switch_traffic $new_color $old_color
            
            # Verify production deployment
            echo -e "${YELLOW}Verifying production deployment...${NC}"
            if check_health $PRODUCTION_PORT 3; then
                echo -e "${GREEN}Production deployment verified!${NC}"
                
                # Cleanup old deployment
                if [ "$old_color" != "none" ]; then
                    cleanup_old_deployment $old_color
                fi
                
                echo -e "${GREEN}========================================${NC}"
                echo -e "${GREEN}Deployment completed successfully!${NC}"
                echo -e "${GREEN}Version: ${VERSION}${NC}"
                echo -e "${GREEN}Environment: ${new_color}${NC}"
                echo -e "${GREEN}========================================${NC}"
            else
                echo -e "${RED}Production verification failed!${NC}"
                rollback $old_color
            fi
        else
            echo -e "${RED}Smoke tests failed!${NC}"
            rollback $old_color
        fi
    else
        echo -e "${RED}Health check failed!${NC}"
        rollback $old_color
    fi
}

# Run main function
main
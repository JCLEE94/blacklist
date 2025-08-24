#!/bin/bash

# Standalone Docker Network Setup for Blacklist Service
# Creates network infrastructure for running 3 containers without docker-compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NETWORK_NAME="blacklist-standalone"
SUBNET="172.25.0.0/16"
GATEWAY="172.25.0.1"

# Container IP assignments
POSTGRES_IP="172.25.0.10"
REDIS_IP="172.25.0.20"
APP_IP="172.25.0.30"

echo -e "${BLUE}=== Blacklist Standalone Network Setup ===${NC}"
echo "Network: $NETWORK_NAME"
echo "Subnet: $SUBNET"
echo "Gateway: $GATEWAY"
echo ""

# Function to check if network exists
check_network_exists() {
    docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"
}

# Function to create network
create_network() {
    echo -e "${YELLOW}Creating Docker network: $NETWORK_NAME${NC}"
    docker network create \
        --driver bridge \
        --subnet=$SUBNET \
        --gateway=$GATEWAY \
        --attachable \
        $NETWORK_NAME
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Network created successfully${NC}"
    else
        echo -e "${RED}✗ Failed to create network${NC}"
        exit 1
    fi
}

# Function to remove existing network
remove_network() {
    echo -e "${YELLOW}Removing existing network: $NETWORK_NAME${NC}"
    
    # Stop containers using the network
    CONTAINERS=$(docker ps -q --filter "network=$NETWORK_NAME" 2>/dev/null || true)
    if [ ! -z "$CONTAINERS" ]; then
        echo -e "${YELLOW}Stopping containers using the network...${NC}"
        docker stop $CONTAINERS || true
    fi
    
    # Remove network
    docker network rm $NETWORK_NAME 2>/dev/null || true
    echo -e "${GREEN}✓ Existing network removed${NC}"
}

# Function to show network info
show_network_info() {
    echo -e "${BLUE}=== Network Information ===${NC}"
    docker network inspect $NETWORK_NAME --format="{{json .}}" | jq -r '
        "Network Name: " + .Name,
        "Driver: " + .Driver,
        "Subnet: " + .IPAM.Config[0].Subnet,
        "Gateway: " + .IPAM.Config[0].Gateway,
        "Scope: " + .Scope
    ' 2>/dev/null || {
        echo "Network Name: $NETWORK_NAME"
        echo "Driver: bridge"
        echo "Subnet: $SUBNET"
        echo "Gateway: $GATEWAY"
        echo "Scope: local"
    }
    echo ""
    echo -e "${BLUE}=== IP Assignments ===${NC}"
    echo "PostgreSQL: $POSTGRES_IP (blacklist-postgresql-standalone)"
    echo "Redis: $REDIS_IP (blacklist-redis-standalone)"
    echo "Application: $APP_IP (blacklist-app-standalone)"
    echo ""
}

# Function to test network connectivity
test_network() {
    echo -e "${BLUE}=== Testing Network Connectivity ===${NC}"
    
    # Create test containers
    echo -e "${YELLOW}Creating test containers...${NC}"
    
    # Test PostgreSQL connectivity
    docker run --rm --network=$NETWORK_NAME --name=test-postgres -d \
        -e POSTGRES_PASSWORD=test postgres:15-alpine sleep 30 || true
    
    # Test Redis connectivity  
    docker run --rm --network=$NETWORK_NAME --name=test-redis -d \
        redis:7-alpine sleep 30 || true
    
    sleep 3
    
    # Test network communication
    if docker run --rm --network=$NETWORK_NAME alpine ping -c 2 $POSTGRES_IP > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL network reachable${NC}"
    else
        echo -e "${RED}✗ PostgreSQL network unreachable${NC}"
    fi
    
    if docker run --rm --network=$NETWORK_NAME alpine ping -c 2 $REDIS_IP > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis network reachable${NC}"
    else
        echo -e "${RED}✗ Redis network unreachable${NC}"
    fi
    
    # Cleanup test containers
    docker stop test-postgres test-redis 2>/dev/null || true
    echo -e "${GREEN}✓ Network connectivity test completed${NC}"
}

# Function to save network configuration
save_config() {
    CONFIG_FILE="config/standalone-network.env"
    mkdir -p "$(dirname "$CONFIG_FILE")"
    
    cat > "$CONFIG_FILE" << EOF
# Standalone Network Configuration
# Generated on $(date)
NETWORK_NAME=$NETWORK_NAME
SUBNET=$SUBNET
GATEWAY=$GATEWAY

# Container IP Assignments
POSTGRES_IP=$POSTGRES_IP
REDIS_IP=$REDIS_IP
APP_IP=$APP_IP

# Container Names
POSTGRES_CONTAINER=blacklist-postgresql-standalone
REDIS_CONTAINER=blacklist-redis-standalone
APP_CONTAINER=blacklist-app-standalone

# Database Configuration
DATABASE_URL=postgresql://blacklist_user:blacklist_standalone_password_change_me@$POSTGRES_IP:5432/blacklist
REDIS_URL=redis://$REDIS_IP:6379/0
EOF
    
    echo -e "${GREEN}✓ Configuration saved to $CONFIG_FILE${NC}"
}

# Main execution
case "${1:-create}" in
    create)
        if check_network_exists; then
            echo -e "${YELLOW}Network $NETWORK_NAME already exists${NC}"
            read -p "Remove and recreate? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                remove_network
                create_network
            else
                echo -e "${BLUE}Using existing network${NC}"
            fi
        else
            create_network
        fi
        save_config
        show_network_info
        ;;
        
    remove)
        if check_network_exists; then
            remove_network
            rm -f config/standalone-network.env
            echo -e "${GREEN}✓ Network and configuration removed${NC}"
        else
            echo -e "${YELLOW}Network $NETWORK_NAME does not exist${NC}"
        fi
        ;;
        
    test)
        if check_network_exists; then
            test_network
        else
            echo -e "${RED}✗ Network $NETWORK_NAME does not exist. Run 'create' first.${NC}"
            exit 1
        fi
        ;;
        
    info)
        if check_network_exists; then
            show_network_info
        else
            echo -e "${RED}✗ Network $NETWORK_NAME does not exist${NC}"
            exit 1
        fi
        ;;
        
    *)
        echo "Usage: $0 {create|remove|test|info}"
        echo ""
        echo "Commands:"
        echo "  create  - Create standalone network (default)"
        echo "  remove  - Remove network and cleanup"
        echo "  test    - Test network connectivity"
        echo "  info    - Show network information"
        exit 1
        ;;
esac

echo -e "${GREEN}=== Network setup completed successfully ===${NC}"
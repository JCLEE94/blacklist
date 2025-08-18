#!/bin/bash
# Configure Network Access for Blacklist Service
# Ensures service is accessible at 192.168.50.X:32542

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Network Access Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get local IP address
LOCAL_IP=$(ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
echo -e "${GREEN}Local IP Address: $LOCAL_IP${NC}"
echo ""

# 1. Check Docker port binding
echo -e "${GREEN}1. Checking Docker Port Binding...${NC}"
if docker ps | grep -q blacklist; then
    PORT_BINDING=$(docker port blacklist 2542 2>/dev/null || echo "Not bound")
    echo "   Container: blacklist"
    echo "   Port Binding: $PORT_BINDING"
    
    if echo "$PORT_BINDING" | grep -q "0.0.0.0:32542"; then
        echo -e "${GREEN}   ✓ Port 32542 is bound to all interfaces${NC}"
    else
        echo -e "${RED}   ✗ Port binding issue detected${NC}"
        echo "   Restarting container with correct binding..."
        docker-compose down
        docker-compose up -d
    fi
else
    echo -e "${YELLOW}   ⚠ Container not running. Starting...${NC}"
    docker-compose up -d
fi
echo ""

# 2. Check network interfaces
echo -e "${GREEN}2. Network Interface Status...${NC}"
ip -4 addr show | grep inet | grep -v "127.0.0.1" | while read -r line; do
    IP=$(echo "$line" | awk '{print $2}' | cut -d'/' -f1)
    IFACE=$(echo "$line" | awk '{print $NF}')
    echo "   Interface: $IFACE - IP: $IP"
done
echo ""

# 3. Check firewall status
echo -e "${GREEN}3. Checking Firewall Status...${NC}"
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | grep "Status:" || echo "Status: unknown")
    echo "   UFW $UFW_STATUS"
    
    if echo "$UFW_STATUS" | grep -q "active"; then
        # Check if port 32542 is allowed
        if sudo ufw status | grep -q "32542"; then
            echo -e "${GREEN}   ✓ Port 32542 is allowed in UFW${NC}"
        else
            echo -e "${YELLOW}   ⚠ Adding UFW rule for port 32542${NC}"
            echo "   Run: sudo ufw allow 32542/tcp"
        fi
    fi
elif command -v firewall-cmd &> /dev/null; then
    if sudo firewall-cmd --list-ports 2>/dev/null | grep -q "32542/tcp"; then
        echo -e "${GREEN}   ✓ Port 32542 is allowed in firewalld${NC}"
    else
        echo -e "${YELLOW}   ⚠ Add firewalld rule:${NC}"
        echo "   sudo firewall-cmd --add-port=32542/tcp --permanent"
        echo "   sudo firewall-cmd --reload"
    fi
else
    echo "   No firewall detected (ufw/firewalld)"
fi
echo ""

# 4. Test connectivity
echo -e "${GREEN}4. Testing Service Connectivity...${NC}"
echo ""

# Test localhost
echo -n "   Testing localhost:32542... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:32542/health | grep -q "200"; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

# Test local IP
echo -n "   Testing $LOCAL_IP:32542... "
if curl -s -o /dev/null -w "%{http_code}" http://$LOCAL_IP:32542/health | grep -q "200"; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

# Test from external perspective (if possible)
echo ""
echo -e "${GREEN}5. External Access Points:${NC}"
echo "   The service should be accessible at:"
echo ""
echo -e "${BLUE}   Primary: http://$LOCAL_IP:32542${NC}"
echo -e "${BLUE}   Docker:  http://localhost:32542${NC}"

# Show all possible access URLs
if [ -f /etc/hostname ]; then
    HOSTNAME=$(cat /etc/hostname)
    echo -e "${BLUE}   Hostname: http://$HOSTNAME:32542${NC}"
fi
echo ""

# 6. Network diagnostics
echo -e "${GREEN}6. Network Diagnostics...${NC}"
echo "   Port 32542 listeners:"
ss -tlnp 2>/dev/null | grep 32542 | while read -r line; do
    echo "   $line"
done
echo ""

# 7. Container network info
echo -e "${GREEN}7. Container Network Information...${NC}"
if docker ps | grep -q blacklist; then
    CONTAINER_ID=$(docker ps -q -f name=blacklist)
    CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_ID)
    echo "   Container ID: $CONTAINER_ID"
    echo "   Container IP: $CONTAINER_IP"
    echo "   Network: $(docker inspect -f '{{range $key, $_ := .NetworkSettings.Networks}}{{$key}}{{end}}' $CONTAINER_ID)"
fi
echo ""

# 8. Quick test endpoints
echo -e "${GREEN}8. Quick Test Commands:${NC}"
echo ""
echo "   # Test health endpoint"
echo "   curl http://$LOCAL_IP:32542/health | jq"
echo ""
echo "   # Test API endpoints"
echo "   curl http://$LOCAL_IP:32542/api/blacklist/active"
echo "   curl http://$LOCAL_IP:32542/api/collection/status | jq"
echo ""
echo "   # Test from another machine in network"
echo "   curl http://$LOCAL_IP:32542/health"
echo ""

# 9. Troubleshooting tips
echo -e "${YELLOW}9. Troubleshooting Tips:${NC}"
echo ""
echo "   If service is not accessible from other machines:"
echo "   1. Check firewall: sudo ufw allow 32542/tcp"
echo "   2. Check Docker: docker-compose restart"
echo "   3. Check logs: docker logs blacklist --tail 50"
echo "   4. Verify binding: netstat -tlnp | grep 32542"
echo ""

echo -e "${GREEN}Configuration check complete!${NC}"
echo ""
echo -e "${BLUE}Service Access URL: http://$LOCAL_IP:32542${NC}"
#!/bin/bash
# Blacklist Management System - Standalone Start Script
# Version: 1.0.40 - No Docker Compose required

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
NETWORK="blacklist-network"

show_usage() {
    echo -e "${BLUE}🚀 Blacklist Management System${NC}"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start      - Start all services"
    echo "  stop       - Stop all services"
    echo "  restart    - Restart all services"
    echo "  status     - Show service status"
    echo "  logs       - Show application logs"
    echo "  health     - Check application health"
    echo "  update     - Pull latest images and restart"
    echo "  clean      - Remove stopped containers and unused images"
    echo "  watchtower - Enable auto-update with Watchtower"
}

start_services() {
    echo -e "${GREEN}🚀 Starting Blacklist Services${NC}"
    echo "================================"
    
    # Run the full startup script
    ./docker-run.sh
}

stop_services() {
    echo -e "${YELLOW}🛑 Stopping Blacklist Services${NC}"
    echo "==============================="
    
    docker stop blacklist 2>/dev/null || echo "Blacklist container already stopped"
    docker stop postgres 2>/dev/null || echo "PostgreSQL container already stopped" 
    docker stop redis 2>/dev/null || echo "Redis container already stopped"
    docker stop watchtower 2>/dev/null || echo "Watchtower container already stopped"
    
    echo -e "${GREEN}✅ All services stopped${NC}"
}

restart_services() {
    echo -e "${BLUE}🔄 Restarting Blacklist Services${NC}"
    echo "================================="
    
    stop_services
    sleep 2
    start_services
}

show_status() {
    echo -e "${BLUE}📊 Service Status${NC}"
    echo "=================="
    
    if docker ps | grep -q blacklist; then
        echo -e "Blacklist:  ${GREEN}✅ Running${NC}"
    else
        echo -e "Blacklist:  ${RED}❌ Stopped${NC}"
    fi
    
    if docker ps | grep -q postgres; then
        echo -e "PostgreSQL: ${GREEN}✅ Running${NC}"
    else
        echo -e "PostgreSQL: ${RED}❌ Stopped${NC}"
    fi
    
    if docker ps | grep -q redis; then
        echo -e "Redis:      ${GREEN}✅ Running${NC}"
    else
        echo -e "Redis:      ${RED}❌ Stopped${NC}"
    fi
    
    if docker ps | grep -q watchtower; then
        echo -e "Watchtower: ${GREEN}✅ Running${NC}"
    else
        echo -e "Watchtower: ${YELLOW}⚠️  Stopped${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Container Details:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}" | grep -E "(blacklist|postgres|redis|watchtower|NAMES)"
}

show_logs() {
    if docker ps | grep -q blacklist; then
        echo -e "${BLUE}📜 Blacklist Logs (last 50 lines):${NC}"
        docker logs --tail 50 -f blacklist
    else
        echo -e "${RED}❌ Blacklist container is not running${NC}"
    fi
}

check_health() {
    echo -e "${BLUE}🏥 Health Check${NC}"
    echo "==============="
    
    if docker ps | grep -q blacklist; then
        echo "Checking application health..."
        sleep 2
        
        if curl -s http://localhost:32542/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Application is healthy${NC}"
            echo ""
            echo "Response:"
            curl -s http://localhost:32542/health | jq '.' 2>/dev/null || curl -s http://localhost:32542/health
        else
            echo -e "${RED}❌ Application health check failed${NC}"
        fi
    else
        echo -e "${RED}❌ Blacklist container is not running${NC}"
    fi
}

update_services() {
    echo -e "${BLUE}🔄 Updating Services${NC}"
    echo "===================="
    
    echo "Pulling latest images..."
    docker pull registry.jclee.me/blacklist:latest
    docker pull postgres:15-alpine
    docker pull redis:7-alpine
    
    echo "Restarting services..."
    restart_services
    
    echo -e "${GREEN}✅ Update completed${NC}"
}

clean_services() {
    echo -e "${YELLOW}🧹 Cleaning Up${NC}"
    echo "==============="
    
    echo "Removing stopped containers..."
    docker container prune -f
    
    echo "Removing unused images..."
    docker image prune -f
    
    echo "Removing unused volumes..."
    docker volume prune -f
    
    echo "Removing unused networks..."
    docker network prune -f
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

enable_watchtower() {
    echo -e "${BLUE}🔄 Enabling Watchtower Auto-Update${NC}"
    echo "==================================="
    
    ./watchtower-enable.sh
}

# Main command handling
case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    health)
        check_health
        ;;
    update)
        update_services
        ;;
    clean)
        clean_services
        ;;
    watchtower)
        enable_watchtower
        ;;
    *)
        show_usage
        ;;
esac
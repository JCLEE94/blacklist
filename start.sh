#!/bin/bash
# Blacklist Management System - Docker Compose Manager
# Replacement for commands/scripts/start.sh

set -e

COMMAND=${1:-help}

case $COMMAND in
    start)
        echo "Starting Blacklist services..."
        docker-compose up -d
        echo "Services started! Check status with: ./start.sh status"
        ;;
    stop)
        echo "Stopping Blacklist services..."
        docker-compose down
        ;;
    restart)
        echo "Restarting Blacklist services..."
        docker-compose restart
        ;;
    logs)
        echo "Following logs..."
        docker-compose logs -f
        ;;
    status)
        echo "Service status:"
        docker-compose ps
        ;;
    update)
        echo "Updating services..."
        docker-compose pull
        docker-compose up -d
        ;;
    clean)
        echo "Cleaning up resources..."
        docker-compose down --volumes --remove-orphans
        docker system prune -f
        ;;
    help|*)
        echo "Blacklist Management System - Docker Compose Manager"
        echo "Usage: ./start.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Follow service logs"
        echo "  status   - Show service status"
        echo "  update   - Pull latest images and restart"
        echo "  clean    - Clean up containers and volumes"
        echo "  help     - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./start.sh start     # Start services"
        echo "  ./start.sh logs      # Watch logs"
        echo "  ./start.sh update    # Update to latest"
        ;;
esac
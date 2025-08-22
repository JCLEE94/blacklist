#!/bin/bash
# Blacklist Management System - Standalone Docker Manager
# Direct docker commands only - NO docker-compose

set -e

COMMAND=${1:-help}
CONTAINER_NAME="blacklist"
IMAGE_NAME="blacklist:standalone"
PORT="${PORT:-32542}"

case $COMMAND in
    start)
        echo "Starting Blacklist container..."
        docker run -d \
            --name ${CONTAINER_NAME} \
            -p ${PORT}:2542 \
            -v blacklist-data:/app/data \
            -v blacklist-logs:/app/logs \
            --restart unless-stopped \
            ${IMAGE_NAME}
        echo "Container started! Check status with: ./start.sh status"
        ;;
    stop)
        echo "Stopping Blacklist container..."
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
        ;;
    restart)
        echo "Restarting Blacklist container..."
        docker restart ${CONTAINER_NAME}
        ;;
    logs)
        echo "Following logs..."
        docker logs -f ${CONTAINER_NAME}
        ;;
    status)
        echo "Container status:"
        docker ps -a | grep ${CONTAINER_NAME} || echo "Container not found"
        ;;
    update)
        echo "Updating container..."
        docker pull ${IMAGE_NAME}
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
        docker run -d \
            --name ${CONTAINER_NAME} \
            -p ${PORT}:2542 \
            -v blacklist-data:/app/data \
            -v blacklist-logs:/app/logs \
            --restart unless-stopped \
            ${IMAGE_NAME}
        ;;
    clean)
        echo "Cleaning up resources..."
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
        docker volume rm blacklist-data blacklist-logs 2>/dev/null || true
        docker system prune -f
        ;;
    build)
        echo "Building standalone image..."
        docker build -f Dockerfile.standalone -t ${IMAGE_NAME} .
        ;;
    help|*)
        echo "Blacklist Management System - Standalone Docker Manager"
        echo "Usage: ./start.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start    - Start container"
        echo "  stop     - Stop container"
        echo "  restart  - Restart container"
        echo "  logs     - Follow container logs"
        echo "  status   - Show container status"
        echo "  update   - Pull latest image and restart"
        echo "  clean    - Clean up container and volumes"
        echo "  build    - Build standalone image"
        echo "  help     - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./start.sh build     # Build image"
        echo "  ./start.sh start     # Start container"
        echo "  ./start.sh logs      # Watch logs"
        ;;
esac
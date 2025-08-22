#!/bin/bash
# Docker Environment Management Script
# Version: v1.0.37
# Purpose: Unified Docker Compose management for all environments

set -e

# Default values
ENVIRONMENT=${ENVIRONMENT:-production}
COMPOSE_FILE="docker-compose.unified.yml"
PROJECT_NAME="blacklist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Docker Environment Management Script

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    start [ENV]         Start services in specified environment (default: production)
    stop                Stop all services
    restart [ENV]       Restart services in specified environment
    logs [SERVICE]      Show logs for service (default: all services)
    status              Show status of all services
    ps                  Show running containers
    clean               Clean up stopped containers and unused resources
    reset               Reset all services (stop, remove, clean)
    env [ENV]           Show current environment configuration
    switch [ENV]        Switch to different environment
    profiles            List available profiles
    health              Check health of all services
    update              Pull latest images and restart
    backup              Backup volumes data
    restore             Restore volumes data from backup

ENVIRONMENTS:
    development         Development environment (.env.development.new)
    production          Production environment (.env.production.new)
    testing             Testing environment (.env.testing)
    custom              Use existing .env file

PROFILES:
    core                Main application services (blacklist, redis, postgresql)
    watchtower          Auto-update service
    monitoring          Prometheus and Grafana monitoring
    all                 All services (default)

EXAMPLES:
    $0 start development                    # Start in development mode
    $0 start production --profile monitoring # Start production with monitoring
    $0 logs blacklist                       # Show logs for blacklist service
    $0 switch development                   # Switch to development environment
    $0 clean                               # Clean up resources

ENVIRONMENT VARIABLES:
    ENVIRONMENT         Target environment (development/production/testing/custom)
    PROFILE             Docker compose profile to use
    COMPOSE_FILE        Docker compose file to use (default: docker-compose.unified.yml)
    PROJECT_NAME        Docker compose project name (default: blacklist)

EOF
}

# Environment setup function
setup_environment() {
    local env=$1
    local env_file=""
    
    case $env in
        development)
            env_file=".env.development.new"
            ;;
        production)
            env_file=".env.production.new"
            ;;
        testing)
            env_file=".env.testing"
            ;;
        custom)
            env_file=".env"
            ;;
        *)
            error "Unknown environment: $env"
            error "Available environments: development, production, testing, custom"
            exit 1
            ;;
    esac
    
    if [[ ! -f "$env_file" ]]; then
        error "Environment file not found: $env_file"
        
        if [[ "$env_file" != ".env" ]]; then
            warning "Creating $env_file from .env.unified..."
            if [[ -f ".env.unified" ]]; then
                cp ".env.unified" "$env_file"
                success "Created $env_file from .env.unified"
                warning "Please review and modify $env_file for your $env environment"
            else
                error ".env.unified not found. Cannot create environment file."
                exit 1
            fi
        else
            error "Please create .env file or use: $0 switch [environment]"
            exit 1
        fi
    fi
    
    # Copy to .env for docker-compose
    cp "$env_file" ".env"
    log "Using environment: $env ($env_file)"
    
    # Export environment
    export ENVIRONMENT=$env
    
    # Show key configuration
    local external_port=$(grep "^EXTERNAL_PORT=" .env | cut -d'=' -f2)
    local deployment_env=$(grep "^DEPLOYMENT_ENV=" .env | cut -d'=' -f2 | head -1)
    local collection_enabled=$(grep "^COLLECTION_ENABLED=" .env | cut -d'=' -f2 | head -1)
    
    log "Configuration: Port=${external_port:-32542}, Deployment=${deployment_env:-unknown}, Collection=${collection_enabled:-unknown}"
}

# Docker compose wrapper
dc() {
    local profiles=""
    if [[ -n "${PROFILE}" ]]; then
        case "${PROFILE}" in
            core)
                profiles=""
                ;;
            watchtower)
                profiles="--profile watchtower"
                ;;
            monitoring)
                profiles="--profile monitoring"
                ;;
            all)
                profiles="--profile watchtower --profile monitoring"
                ;;
            *)
                profiles="--profile ${PROFILE}"
                ;;
        esac
    fi
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" $profiles "$@"
}

# Command implementations
cmd_start() {
    local env=${1:-$ENVIRONMENT}
    setup_environment "$env"
    
    log "Creating data directories..."
    mkdir -p data/{blacklist,redis,postgresql,prometheus,grafana} logs
    
    log "Starting services..."
    dc up -d
    
    log "Waiting for services to be healthy..."
    sleep 10
    
    cmd_health
    success "Services started successfully"
    
    # Show access information
    local external_port=$(grep "^EXTERNAL_PORT=" .env | cut -d'=' -f2)
    echo
    success "Access URLs:"
    success "  Application: http://localhost:${external_port:-32542}"
    success "  Health Check: http://localhost:${external_port:-32542}/health"
    
    if dc config --services | grep -q prometheus 2>/dev/null; then
        local prometheus_port=$(grep "^PROMETHEUS_PORT=" .env | cut -d'=' -f2)
        success "  Prometheus: http://localhost:${prometheus_port:-9090}"
    fi
    
    if dc config --services | grep -q grafana 2>/dev/null; then
        local grafana_port=$(grep "^GRAFANA_PORT=" .env | cut -d'=' -f2)
        success "  Grafana: http://localhost:${grafana_port:-3000}"
    fi
}

cmd_stop() {
    log "Stopping services..."
    dc stop
    success "Services stopped"
}

cmd_restart() {
    local env=${1:-$ENVIRONMENT}
    log "Restarting services..."
    cmd_stop
    sleep 5
    cmd_start "$env"
}

cmd_logs() {
    local service=${1:-}
    if [[ -n "$service" ]]; then
        log "Showing logs for $service..."
        dc logs -f "$service"
    else
        log "Showing logs for all services..."
        dc logs -f
    fi
}

cmd_status() {
    log "Service status:"
    dc ps
    echo
    log "Container status:"
    docker ps --filter "label=com.docker.compose.project=$PROJECT_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

cmd_ps() {
    dc ps
}

cmd_clean() {
    log "Cleaning up..."
    dc down --remove-orphans
    docker system prune -f
    success "Cleanup completed"
}

cmd_reset() {
    warning "This will remove all containers and data. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log "Resetting all services..."
        dc down -v --remove-orphans
        docker system prune -f
        success "Reset completed"
    else
        log "Reset cancelled"
    fi
}

cmd_env() {
    local env=${1:-$ENVIRONMENT}
    setup_environment "$env"
    
    echo "Current environment configuration:"
    echo "=================================="
    grep -E "^[A-Z_]+=" .env | sort
}

cmd_switch() {
    local env=${1:-}
    if [[ -z "$env" ]]; then
        error "Please specify environment: development, production, testing, or custom"
        exit 1
    fi
    
    setup_environment "$env"
    success "Switched to $env environment"
    
    # Restart if services are running
    if dc ps -q | grep -q .; then
        warning "Services are running. Do you want to restart them? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            cmd_restart "$env"
        fi
    fi
}

cmd_profiles() {
    echo "Available profiles:"
    echo "=================="
    echo "core        - Main application services (blacklist, redis, postgresql)"
    echo "watchtower  - Auto-update service"
    echo "monitoring  - Prometheus and Grafana monitoring"
    echo "all         - All services (default)"
    echo
    echo "Usage: PROFILE=monitoring $0 start"
    echo "   or: $0 start production --profile monitoring"
}

cmd_health() {
    log "Checking service health..."
    
    local external_port=$(grep "^EXTERNAL_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "32542")
    
    # Check main application
    if curl -f -s "http://localhost:${external_port}/health" > /dev/null; then
        success "Application: Healthy"
    else
        error "Application: Unhealthy (http://localhost:${external_port}/health)"
    fi
    
    # Check database
    if dc exec -T postgresql pg_isready > /dev/null 2>&1; then
        success "PostgreSQL: Healthy"
    else
        error "PostgreSQL: Unhealthy"
    fi
    
    # Check redis
    if dc exec -T redis redis-cli ping > /dev/null 2>&1; then
        success "Redis: Healthy"
    else
        error "Redis: Unhealthy"
    fi
}

cmd_update() {
    log "Pulling latest images..."
    dc pull
    
    log "Restarting services with new images..."
    dc up -d
    
    success "Update completed"
}

cmd_backup() {
    local backup_dir="backup/$(date +%Y%m%d_%H%M%S)"
    log "Creating backup in $backup_dir..."
    
    mkdir -p "$backup_dir"
    
    # Backup volumes
    for volume in blacklist-data blacklist-logs blacklist-redis-data blacklist-postgresql-data; do
        if docker volume inspect "$volume" > /dev/null 2>&1; then
            log "Backing up volume: $volume"
            docker run --rm -v "$volume":/source -v "$PWD/$backup_dir":/backup alpine tar czf "/backup/$volume.tar.gz" -C /source .
        fi
    done
    
    # Backup configuration
    cp .env "$backup_dir/"
    
    success "Backup created in $backup_dir"
}

cmd_restore() {
    local backup_dir=${1:-}
    if [[ -z "$backup_dir" ]] || [[ ! -d "$backup_dir" ]]; then
        error "Please specify a valid backup directory"
        exit 1
    fi
    
    warning "This will restore data from $backup_dir. Current data will be overwritten. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "Restore cancelled"
        exit 0
    fi
    
    log "Stopping services..."
    dc stop
    
    # Restore volumes
    for backup_file in "$backup_dir"/*.tar.gz; do
        if [[ -f "$backup_file" ]]; then
            local volume=$(basename "$backup_file" .tar.gz)
            log "Restoring volume: $volume"
            docker run --rm -v "$volume":/target -v "$PWD/$backup_dir":/backup alpine sh -c "rm -rf /target/* && tar xzf /backup/$volume.tar.gz -C /target"
        fi
    done
    
    # Restore configuration
    if [[ -f "$backup_dir/.env" ]]; then
        cp "$backup_dir/.env" .env
    fi
    
    log "Starting services..."
    dc start
    
    success "Restore completed"
}

# Parse arguments
COMMAND=${1:-help}
shift || true

# Handle profile flag
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --profile=*)
            PROFILE="${1#*=}"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

# Execute command
case $COMMAND in
    start)
        cmd_start "$@"
        ;;
    stop)
        cmd_stop "$@"
        ;;
    restart)
        cmd_restart "$@"
        ;;
    logs)
        cmd_logs "$@"
        ;;
    status)
        cmd_status "$@"
        ;;
    ps)
        cmd_ps "$@"
        ;;
    clean)
        cmd_clean "$@"
        ;;
    reset)
        cmd_reset "$@"
        ;;
    env)
        cmd_env "$@"
        ;;
    switch)
        cmd_switch "$@"
        ;;
    profiles)
        cmd_profiles "$@"
        ;;
    health)
        cmd_health "$@"
        ;;
    update)
        cmd_update "$@"
        ;;
    backup)
        cmd_backup "$@"
        ;;
    restore)
        cmd_restore "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $COMMAND"
        echo
        show_help
        exit 1
        ;;
esac
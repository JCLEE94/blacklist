#!/bin/bash

# Enhanced Auto-Rollback System
# Intelligent rollback with Docker Compose support, health monitoring, and notification system

echo "🔄 Enhanced Auto-Rollback System"
echo "==============================="
echo ""

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
NAMESPACE="blacklist"
APP_NAME="blacklist"
COMPOSE_FILE="docker-compose.yml"
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_DELAY=15
ROLLBACK_TIMEOUT=300
API_BASE_URL="http://localhost:32542"
BACKUP_IMAGE_TAG="stable"
NOTIFICATION_ENABLED=true

# State tracking
ROLLBACK_REASON=""
ROLLBACK_START_TIME=""
ORIGINAL_IMAGE=""
ROLLBACK_IMAGE=""
DRY_RUN=false

# Initialize logging
echo "# Auto-Rollback Log - $(date)" > rollback.log
echo "[]" > rollback_events.json

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [STEP] $1" >> rollback.log
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> rollback.log
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1" >> rollback.log
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> rollback.log
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> rollback.log
}

log_rollback_event() {
    local event="$1"
    local details="$2"
    
    # Create JSON event
    local json_event="{\"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\", \"event\": \"$event\", \"details\": \"$details\", \"image_original\": \"$ORIGINAL_IMAGE\", \"image_rollback\": \"$ROLLBACK_IMAGE\"}"
    
    # Add to events array (simple append)
    echo "$json_event" >> rollback_events.json
}

send_notification() {
    local title="$1"
    local message="$2"
    local severity="$3"  # info, warning, error, success
    
    if [ "$NOTIFICATION_ENABLED" = "true" ]; then
        print_info "NOTIFICATION [$severity]: $title - $message"
        
        # Log structured notification
        log_rollback_event "notification_sent" "$title: $message (severity: $severity)"
        
        # Webhook notification example (configure WEBHOOK_URL)
        if [ -n "$WEBHOOK_URL" ]; then
            curl -X POST "$WEBHOOK_URL" -H "Content-Type: application/json" \
              -d "{\"title\": \"$title\", \"message\": \"$message\", \"severity\": \"$severity\", \"service\": \"blacklist\"}" \
              --connect-timeout 5 --max-time 10 2>/dev/null || print_warning "Webhook notification failed"
        fi
    fi
}

check_docker_compose_health() {
    local max_retries="$1"
    local delay="$2"
    
    print_step "Checking Docker Compose services health..."
    
    for ((i=1; i<=max_retries; i++)); do
        print_info "Health check attempt $i/$max_retries"
        
        # Check if containers are running
        local containers_up=$(docker-compose ps --filter status=running 2>/dev/null | wc -l)
        if [ "$containers_up" -gt 1 ]; then  # Header + at least 1 container
            # Check API health
            local health_status=$(curl -s "$API_BASE_URL/health" 2>/dev/null | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
            if [ "$health_status" = "healthy" ]; then
                print_success "Services are healthy (status: $health_status)"
                return 0
            else
                print_warning "API status: $health_status"
            fi
        else
            print_warning "No containers running"
        fi
        
        if [ $i -lt $max_retries ]; then
            print_warning "Health check failed, retrying in ${delay}s..."
            sleep $delay
        fi
    done
    
    print_error "Health check failed after $max_retries attempts"
    return 1
}

get_current_image() {
    if [ -f "$COMPOSE_FILE" ]; then
        grep "image:" "$COMPOSE_FILE" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'"
    else
        echo "unknown"
    fi
}

backup_current_deployment() {
    print_step "Backing up current deployment configuration..."
    
    # Backup docker-compose.yml
    if [ -f "$COMPOSE_FILE" ]; then
        local backup_file="$COMPOSE_FILE.rollback-backup-$(date +%s)"
        if [ "$DRY_RUN" = "false" ]; then
            cp "$COMPOSE_FILE" "$backup_file"
            print_success "Docker Compose configuration backed up to $backup_file"
        else
            print_info "[DRY RUN] Would backup $COMPOSE_FILE to $backup_file"
        fi
    fi
    
    # Get and backup current image
    ORIGINAL_IMAGE=$(get_current_image)
    if [ "$ORIGINAL_IMAGE" != "unknown" ]; then
        print_info "Current image: $ORIGINAL_IMAGE"
        
        if [ "$DRY_RUN" = "false" ]; then
            local stable_tag="${ORIGINAL_IMAGE%:*}:$BACKUP_IMAGE_TAG"
            if docker tag "$ORIGINAL_IMAGE" "$stable_tag" 2>/dev/null; then
                print_success "Tagged current image as stable: $stable_tag"
            else
                print_warning "Failed to tag current image as stable"
            fi
        else
            print_info "[DRY RUN] Would tag $ORIGINAL_IMAGE as ${ORIGINAL_IMAGE%:*}:$BACKUP_IMAGE_TAG"
        fi
    fi
}

detect_rollback_target() {
    print_step "Detecting rollback target..."
    
    local base_image="${ORIGINAL_IMAGE%:*}"
    
    # Try to find stable tagged image first
    local stable_image="$base_image:$BACKUP_IMAGE_TAG"
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "$stable_image"; then
        echo "$stable_image"
        return 0
    fi
    
    # Try previous versions from registry
    local previous_tags=("v1.0.37" "v1.0.37" "latest-stable" "previous")
    
    for tag in "${previous_tags[@]}"; do
        local candidate_image="$base_image:$tag"
        print_info "Trying rollback target: $candidate_image"
        
        if [ "$DRY_RUN" = "false" ]; then
            if timeout 30 docker pull "$candidate_image" > /dev/null 2>&1; then
                print_success "Found rollback target: $candidate_image"
                echo "$candidate_image"
                return 0
            fi
        else
            print_info "[DRY RUN] Would try to pull $candidate_image"
        fi
    done
    
    # Fallback to local images
    local local_images=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "$base_image" | grep -v "$ORIGINAL_IMAGE" | head -1)
    if [ -n "$local_images" ]; then
        print_success "Using local image as rollback target: $local_images"
        echo "$local_images"
        return 0
    fi
    
    print_error "No suitable rollback target found"
    echo "unknown"
    return 1
}

perform_docker_rollback() {
    local target_image="$1"
    
    print_step "Performing Docker Compose rollback..."
    ROLLBACK_IMAGE="$target_image"
    
    if [ "$DRY_RUN" = "true" ]; then
        print_info "[DRY RUN] Would perform rollback to: $target_image"
        print_info "[DRY RUN] Steps:"
        print_info "[DRY RUN]   1. Stop services: docker-compose down --remove-orphans"
        print_info "[DRY RUN]   2. Update compose file image to: $target_image"
        print_info "[DRY RUN]   3. Pull image: docker-compose pull"
        print_info "[DRY RUN]   4. Start services: docker-compose up -d"
        return 0
    fi
    
    # Stop current services gracefully
    print_info "Stopping current services..."
    timeout 60 docker-compose down --remove-orphans || {
        print_warning "Graceful shutdown failed, forcing stop"
        docker-compose kill
        docker-compose rm -f
    }
    
    # Update image in compose file
    if [ -f "$COMPOSE_FILE" ]; then
        if [ "$target_image" != "unknown" ]; then
            # Create backup of current compose file
            cp "$COMPOSE_FILE" "$COMPOSE_FILE.pre-rollback"
            
            # Update the image
            sed -i "s|image:.*|image: $target_image|g" "$COMPOSE_FILE"
            print_success "Updated compose file with rollback image: $target_image"
        fi
    fi
    
    # Pull rollback image
    print_info "Pulling rollback image..."
    if timeout 120 docker-compose pull; then
        print_success "Rollback image pulled successfully"
    else
        print_warning "Failed to pull rollback image, using local copy"
    fi
    
    # Start services with rollback image
    print_info "Starting services with rollback image..."
    docker-compose up -d
    
    log_rollback_event "rollback_performed" "Docker Compose rollback to $target_image"
}

verify_rollback_success() {
    print_step "Verifying rollback success..."
    
    if [ "$DRY_RUN" = "true" ]; then
        print_info "[DRY RUN] Would verify rollback success"
        return 0
    fi
    
    # Wait for services to start
    print_info "Waiting for services to initialize..."
    sleep 15
    
    # Comprehensive health check
    if check_docker_compose_health 8 10; then
        print_success "Rollback verification successful"
        
        # Get final status
        local health_response=$(curl -s "$API_BASE_URL/api/health" 2>/dev/null || echo "{}")
        local status=$(echo "$health_response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        local total_ips=$(echo "$health_response" | jq -r '.metrics.total_ips // "unknown"' 2>/dev/null || echo "unknown")
        
        print_success "Service status: $status"
        print_success "Total IPs in system: $total_ips"
        
        log_rollback_event "rollback_verified" "Service healthy after rollback - status: $status, IPs: $total_ips"
        return 0
    else
        print_error "Rollback verification failed"
        log_rollback_event "rollback_failed" "Service unhealthy after rollback"
        
        # Attempt emergency recovery
        print_warning "Attempting emergency recovery..."
        send_notification "Rollback Failed" "Emergency recovery needed for blacklist system" "error"
        return 1
    fi
}

generate_rollback_report() {
    print_step "Generating rollback report..."
    
    local rollback_end_time=$(date)
    local report_file="rollback_report_$(date +%s).txt"
    local duration="unknown"
    
    if [ -n "$ROLLBACK_START_TIME" ]; then
        duration="$(($(date +%s) - $(date -d "$ROLLBACK_START_TIME" +%s)))s"
    fi
    
    cat > "$report_file" << EOF
BLACKLIST SYSTEM ROLLBACK REPORT
================================

Rollback Date: $rollback_end_time
Rollback Duration: $duration
Reason: $ROLLBACK_REASON
Dry Run: $DRY_RUN

IMAGES:
- Original: $ORIGINAL_IMAGE
- Rollback: $ROLLBACK_IMAGE

DOCKER SERVICES STATUS:
$(docker-compose ps 2>/dev/null || echo "Unable to get service status")

HEALTH CHECK RESULT:
$(curl -s "$API_BASE_URL/api/health" 2>/dev/null | jq '.' 2>/dev/null || echo "Health check unavailable")

RECENT LOGS:
$(tail -20 rollback.log 2>/dev/null || echo "No logs available")

EVENTS:
$(tail -10 rollback_events.json 2>/dev/null || echo "No events logged")
EOF

    print_success "Rollback report generated: $report_file"
    
    # Send completion notification
    local status="completed"
    if [ "$DRY_RUN" = "true" ]; then
        status="simulated"
    fi
    
    send_notification "Rollback $status" "System rollback $status: $ORIGINAL_IMAGE → $ROLLBACK_IMAGE" "info"
    
    return 0
}

execute_rollback() {
    local reason="$1"
    local target_image="$2"
    
    ROLLBACK_REASON="$reason"
    ROLLBACK_START_TIME=$(date)
    
    print_step "Starting rollback process..."
    print_info "Reason: $reason"
    
    send_notification "Rollback Started" "Initiating rollback due to: $reason" "warning"
    log_rollback_event "rollback_initiated" "$reason"
    
    # Step 1: Backup current deployment
    backup_current_deployment
    
    # Step 2: Determine rollback target
    if [ -n "$target_image" ] && [ "$target_image" != "auto" ]; then
        ROLLBACK_IMAGE="$target_image"
        print_info "Using specified rollback target: $target_image"
    else
        ROLLBACK_IMAGE=$(detect_rollback_target)
        if [ "$ROLLBACK_IMAGE" = "unknown" ]; then
            print_error "Cannot determine rollback target"
            send_notification "Rollback Failed" "No suitable rollback target found" "error"
            return 1
        fi
    fi
    
    # Step 3: Perform rollback
    if ! perform_docker_rollback "$ROLLBACK_IMAGE"; then
        print_error "Rollback execution failed"
        send_notification "Rollback Failed" "Rollback execution failed" "error"
        return 1
    fi
    
    # Step 4: Verify rollback success
    if ! verify_rollback_success; then
        print_error "Rollback verification failed"
        return 1
    fi
    
    # Step 5: Generate report
    generate_rollback_report
    
    print_success "Rollback completed successfully!"
    return 0
}

check_health_and_rollback() {
    print_step "Performing health check..."
    
    # Get current image for tracking
    ORIGINAL_IMAGE=$(get_current_image)
    
    if check_docker_compose_health $HEALTH_CHECK_RETRIES $HEALTH_CHECK_DELAY; then
        print_success "System is healthy, no rollback needed"
        
        # Still generate a status report
        local status_file="health_status_$(date +%s).txt"
        cat > "$status_file" << EOF
BLACKLIST SYSTEM HEALTH STATUS
==============================

Check Date: $(date)
Current Image: $ORIGINAL_IMAGE

HEALTH CHECK: PASSED
$(curl -s "$API_BASE_URL/api/health" 2>/dev/null | jq '.' 2>/dev/null || echo "Detailed health unavailable")

DOCKER SERVICES:
$(docker-compose ps)
EOF
        print_info "Health status report: $status_file"
        return 0
    else
        print_warning "System health check failed, initiating rollback"
        execute_rollback "Health check failure" "auto"
        return $?
    fi
}

show_usage() {
    cat << EOF
Enhanced Auto-Rollback System for Blacklist Management

Usage: $0 [OPTIONS]

Options:
  --check-health          Perform health check, rollback if unhealthy
  --force-rollback        Force immediate rollback to last stable version
  --rollback-to IMAGE     Rollback to specific image
  --dry-run              Simulate rollback without making changes
  --enable-notifications  Enable webhook notifications (default: true)
  --disable-notifications Disable notifications
  --status               Show current system status
  --help                 Show this help message

Examples:
  $0 --check-health              # Health check with auto-rollback if needed
  $0 --force-rollback           # Immediate rollback to stable version
  $0 --rollback-to registry.jclee.me/blacklist:v1.0.37
  $0 --dry-run --force-rollback # Simulate rollback process
  $0 --status                   # Show current system status

Environment Variables:
  WEBHOOK_URL               Webhook endpoint for notifications
  API_BASE_URL             API endpoint for health checks (default: http://localhost:32542)
  HEALTH_CHECK_RETRIES     Number of health check retries (default: 10)
  BACKUP_IMAGE_TAG         Tag for stable image backup (default: stable)

EOF
}

show_status() {
    print_step "Current System Status"
    
    local current_image=$(get_current_image)
    echo "Current Image: $current_image"
    
    echo ""
    echo "Docker Services:"
    docker-compose ps 2>/dev/null || echo "Unable to get service status"
    
    echo ""
    echo "Health Status:"
    local health_response=$(curl -s "$API_BASE_URL/api/health" 2>/dev/null || echo "{}")
    if [ "$health_response" != "{}" ]; then
        echo "$health_response" | jq '.' 2>/dev/null || echo "$health_response"
    else
        echo "Health check unavailable"
    fi
    
    echo ""
    echo "Recent Images:"
    docker images | grep -E "(blacklist|registry.jclee.me)" | head -5
}

# Main script logic
main() {
    local action=""
    local target_image=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-health)
                action="check_health"
                shift
                ;;
            --force-rollback)
                action="force_rollback"
                shift
                ;;
            --rollback-to)
                action="rollback_to"
                target_image="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --enable-notifications)
                NOTIFICATION_ENABLED=true
                shift
                ;;
            --disable-notifications)
                NOTIFICATION_ENABLED=false
                shift
                ;;
            --status)
                action="status"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Execute action
    case $action in
        "check_health")
            check_health_and_rollback
            ;;
        "force_rollback")
            execute_rollback "Manual rollback requested" "auto"
            ;;
        "rollback_to")
            if [ -z "$target_image" ]; then
                print_error "Target image not specified"
                exit 1
            fi
            execute_rollback "Manual rollback to specific image" "$target_image"
            ;;
        "status")
            show_status
            ;;
        "")
            print_warning "No action specified, defaulting to health check"
            check_health_and_rollback
            ;;
        *)
            print_error "Unknown action: $action"
            show_usage
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    command -v docker >/dev/null 2>&1 || missing_deps+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing_deps+=("docker-compose")
    command -v curl >/dev/null 2>&1 || missing_deps+=("curl")
    command -v jq >/dev/null 2>&1 || missing_deps+=("jq")
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_info "Please install missing dependencies and try again"
        exit 1
    fi
}

# Error handling
set -eE
trap 'print_error "Script failed at line $LINENO"' ERR

# Initialize
check_dependencies

# Run main logic
main "$@"
#!/bin/bash

# Deployment Troubleshooting Tool
# Comprehensive diagnostic and repair tool for blacklist system issues

echo "🔧 Deployment Troubleshooting Tool"
echo "=================================="
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
API_BASE_URL="http://localhost:32542"
COMPOSE_FILE="docker-compose.yml"
LOG_DIR="logs"
DIAGNOSTIC_OUTPUT="diagnostic_report_$(date +%s).txt"

# Initialize diagnostic log
echo "# Troubleshooting Session - $(date)" > "$DIAGNOSTIC_OUTPUT"

print_section() {
    echo -e "${BLUE}$1${NC}"
    echo "$1" >> "$DIAGNOSTIC_OUTPUT"
    echo "$(printf '=%.0s' {1..${#1}})" >> "$DIAGNOSTIC_OUTPUT"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
    echo "[STEP] $1" >> "$DIAGNOSTIC_OUTPUT"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[SUCCESS] $1" >> "$DIAGNOSTIC_OUTPUT"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[WARNING] $1" >> "$DIAGNOSTIC_OUTPUT"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[ERROR] $1" >> "$DIAGNOSTIC_OUTPUT"
}

print_info() {
    echo -e "   $1"
    echo "   $1" >> "$DIAGNOSTIC_OUTPUT"
}

collect_system_info() {
    print_section "SYSTEM INFORMATION"
    
    print_step "Collecting system information..."
    
    # Basic system info
    {
        echo "Date: $(date)"
        echo "Hostname: $(hostname)"
        echo "OS: $(uname -a)"
        echo "User: $(whoami)"
        echo "Working Directory: $(pwd)"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    # Docker info
    print_info "Docker version and info:"
    {
        echo "Docker Version:"
        docker --version 2>&1 || echo "Docker not available"
        echo ""
        echo "Docker Compose Version:"
        docker-compose --version 2>&1 || echo "Docker Compose not available"
        echo ""
        echo "Docker Info:"
        docker info 2>&1 | head -20 || echo "Docker daemon not running"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    # Disk space
    print_info "Disk space:"
    {
        echo "Disk Usage:"
        df -h . 2>&1 || echo "Unable to get disk usage"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    # Memory info
    print_info "Memory usage:"
    {
        echo "Memory Usage:"
        free -h 2>&1 || echo "Unable to get memory info"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    print_success "System information collected"
}

check_docker_services() {
    print_section "DOCKER SERVICES DIAGNOSIS"
    
    print_step "Checking Docker services..."
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        return 1
    fi
    
    print_info "Docker Compose file found: $COMPOSE_FILE"
    
    # Check Docker daemon
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker daemon is not running"
        {
            echo "Docker daemon is not running"
            echo "Solution: Start Docker service with: sudo systemctl start docker"
            echo ""
        } >> "$DIAGNOSTIC_OUTPUT"
        return 1
    fi
    
    print_success "Docker daemon is running"
    
    # Get container status
    print_info "Container status:"
    {
        echo "Container Status:"
        docker-compose ps 2>&1
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    # Check individual services
    local services=("blacklist" "redis" "postgresql")
    for service in "${services[@]}"; do
        print_info "Checking service: $service"
        
        local status=$(docker-compose ps "$service" 2>/dev/null | grep -v "Name" | awk '{print $4}' || echo "not found")
        
        if [[ "$status" == *"Up"* ]]; then
            print_success "$service is running"
            
            # Get service logs (last 20 lines)
            {
                echo "$service logs (last 20 lines):"
                docker-compose logs --tail=20 "$service" 2>&1 || echo "Unable to get logs for $service"
                echo ""
            } >> "$DIAGNOSTIC_OUTPUT"
            
        else
            print_warning "$service is not running (status: $status)"
            
            # Get service logs for troubleshooting
            {
                echo "$service logs (last 50 lines for troubleshooting):"
                docker-compose logs --tail=50 "$service" 2>&1 || echo "Unable to get logs for $service"
                echo ""
            } >> "$DIAGNOSTIC_OUTPUT"
        fi
    done
}

check_network_connectivity() {
    print_section "NETWORK CONNECTIVITY CHECK"
    
    print_step "Checking network connectivity..."
    
    # Check port availability
    local ports=("32542" "32543" "6379")
    for port in "${ports[@]}"; do
        print_info "Checking port $port:"
        
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            print_success "Port $port is listening"
        else
            print_warning "Port $port is not listening"
        fi
    done
    
    # Check API connectivity
    print_info "Testing API connectivity:"
    
    local endpoints=("/health" "/api/health" "/api/blacklist/active")
    for endpoint in "${endpoints[@]}"; do
        local url="$API_BASE_URL$endpoint"
        print_info "Testing: $url"
        
        local response_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 "$url" 2>/dev/null || echo "000")
        
        if [ "$response_code" = "200" ]; then
            print_success "$endpoint: HTTP $response_code (OK)"
        elif [ "$response_code" = "503" ]; then
            print_warning "$endpoint: HTTP $response_code (Service Unavailable)"
        else
            print_error "$endpoint: HTTP $response_code (Error)"
        fi
        
        echo "   $endpoint: HTTP $response_code" >> "$DIAGNOSTIC_OUTPUT"
    done
    
    # Test internal container connectivity
    print_info "Testing internal container network:"
    {
        echo "Docker Network Information:"
        docker network ls 2>&1 || echo "Unable to list networks"
        echo ""
        docker network inspect blacklist-network 2>&1 || echo "blacklist-network not found"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
}

check_database_connectivity() {
    print_section "DATABASE CONNECTIVITY CHECK"
    
    print_step "Checking database connectivity..."
    
    # PostgreSQL connection test
    print_info "Testing PostgreSQL connection:"
    
    if docker-compose exec -T postgresql pg_isready -U blacklist_user -d blacklist > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
        
        # Test basic query
        local table_count=$(docker-compose exec -T postgresql psql -U blacklist_user -d blacklist -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs || echo "0")
        print_info "Database tables: $table_count"
        
        local blacklist_count=$(docker-compose exec -T postgresql psql -U blacklist_user -d blacklist -t -c "SELECT COUNT(*) FROM blacklist_entries;" 2>/dev/null | xargs || echo "error")
        if [ "$blacklist_count" != "error" ]; then
            print_info "Blacklist entries: $blacklist_count"
        else
            print_warning "Unable to count blacklist entries (table may not exist)"
        fi
        
    else
        print_error "PostgreSQL connection failed"
        
        # Additional diagnostics
        {
            echo "PostgreSQL Diagnostics:"
            docker-compose logs --tail=30 postgresql 2>&1
            echo ""
        } >> "$DIAGNOSTIC_OUTPUT"
    fi
    
    # Redis connection test
    print_info "Testing Redis connection:"
    
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is responding"
        
        local redis_info=$(docker-compose exec -T redis redis-cli info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
        print_info "Redis memory usage: $redis_info"
        
    else
        print_error "Redis connection failed"
        
        # Additional diagnostics
        {
            echo "Redis Diagnostics:"
            docker-compose logs --tail=30 redis 2>&1
            echo ""
        } >> "$DIAGNOSTIC_OUTPUT"
    fi
}

check_application_health() {
    print_section "APPLICATION HEALTH CHECK"
    
    print_step "Checking application health..."
    
    # Detailed health check
    local health_response=$(curl -s "$API_BASE_URL/api/health" 2>/dev/null || echo "{}")
    
    if echo "$health_response" | jq . > /dev/null 2>&1; then
        print_success "API is responding with valid JSON"
        
        local status=$(echo "$health_response" | jq -r '.status // "unknown"')
        local total_ips=$(echo "$health_response" | jq -r '.metrics.total_ips // "unknown"')
        local collection_enabled=$(echo "$health_response" | jq -r '.components.collection.status // "unknown"')
        
        print_info "System status: $status"
        print_info "Total IPs: $total_ips"
        print_info "Collection status: $collection_enabled"
        
        # Store detailed health info
        {
            echo "Application Health Details:"
            echo "$health_response" | jq . 2>/dev/null || echo "$health_response"
            echo ""
        } >> "$DIAGNOSTIC_OUTPUT"
        
    else
        print_error "API health check failed or returned invalid response"
        
        {
            echo "Raw Health Response:"
            echo "$health_response"
            echo ""
        } >> "$DIAGNOSTIC_OUTPUT"
    fi
    
    # Check build info
    print_info "Checking build information:"
    
    local build_response_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/build-info" 2>/dev/null || echo "000")
    if [ "$build_response_code" = "200" ]; then
        print_success "Build info endpoint is accessible"
    else
        print_warning "Build info endpoint returned: HTTP $build_response_code"
    fi
}

check_resource_usage() {
    print_section "RESOURCE USAGE CHECK"
    
    print_step "Checking resource usage..."
    
    # Docker container resources
    print_info "Container resource usage:"
    {
        echo "Container Resource Usage:"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" 2>&1 || echo "Unable to get container stats"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    # System resources
    print_info "System resource usage:"
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo "unknown")
    print_info "CPU usage: ${cpu_usage}%"
    
    # Memory usage
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}' 2>/dev/null || echo "unknown")
    print_info "Memory usage: ${mem_usage}%"
    
    # Disk usage for current directory
    local disk_usage=$(df . | tail -1 | awk '{print $5}' 2>/dev/null || echo "unknown")
    print_info "Disk usage (current dir): $disk_usage"
    
    # Check for disk space issues
    local disk_avail=$(df . | tail -1 | awk '{print $4}' 2>/dev/null || echo "0")
    if [ "$disk_avail" -lt 1048576 ]; then  # Less than 1GB
        print_warning "Low disk space: only ${disk_avail}KB available"
    fi
}

check_logs_for_errors() {
    print_section "LOG ANALYSIS"
    
    print_step "Analyzing logs for common errors..."
    
    # Check application logs
    local log_files=()
    if [ -d "$LOG_DIR" ]; then
        log_files=($(find "$LOG_DIR" -name "*.log" -type f 2>/dev/null | head -5))
    fi
    
    # Add docker compose logs
    print_info "Checking Docker container logs for errors:"
    
    local services=("blacklist" "redis" "postgresql")
    for service in "${services[@]}"; do
        print_info "Analyzing $service logs:"
        
        local error_count=$(docker-compose logs --tail=100 "$service" 2>&1 | grep -i -E "(error|exception|failed|critical)" | wc -l || echo "0")
        
        if [ "$error_count" -gt 0 ]; then
            print_warning "Found $error_count potential error(s) in $service logs"
            
            {
                echo "$service Error Analysis (last 100 lines):"
                docker-compose logs --tail=100 "$service" 2>&1 | grep -i -E "(error|exception|failed|critical)" | tail -10
                echo ""
            } >> "$DIAGNOSTIC_OUTPUT"
        else
            print_success "No obvious errors found in $service logs"
        fi
    done
    
    # Check for common error patterns
    print_info "Checking for common issues:"
    
    # Check for port conflicts
    local port_conflicts=$(docker-compose logs blacklist 2>&1 | grep -i "port.*already in use" | wc -l || echo "0")
    if [ "$port_conflicts" -gt 0 ]; then
        print_warning "Port conflict detected"
        echo "   Suggested solution: Check if port 32542 is already in use: netstat -tuln | grep 32542"
    fi
    
    # Check for database connection issues
    local db_connection_errors=$(docker-compose logs blacklist 2>&1 | grep -i -E "(database.*connection|connection.*database|could not connect)" | wc -l || echo "0")
    if [ "$db_connection_errors" -gt 0 ]; then
        print_warning "Database connection issues detected"
        echo "   Suggested solution: Restart PostgreSQL service: docker-compose restart postgresql"
    fi
    
    # Check for memory issues
    local memory_errors=$(docker-compose logs 2>&1 | grep -i -E "(out of memory|memory.*error|killed)" | wc -l || echo "0")
    if [ "$memory_errors" -gt 0 ]; then
        print_warning "Memory-related issues detected"
        echo "   Suggested solution: Check system memory and consider increasing Docker memory limits"
    fi
}

generate_repair_suggestions() {
    print_section "REPAIR SUGGESTIONS"
    
    print_step "Generating repair suggestions based on findings..."
    
    {
        echo "AUTOMATED REPAIR COMMANDS"
        echo "========================"
        echo ""
        echo "# Basic service restart sequence:"
        echo "docker-compose down"
        echo "docker-compose pull"
        echo "docker-compose up -d"
        echo ""
        echo "# Database reset (CAUTION: This will delete all data):"
        echo "docker-compose down"
        echo "docker volume rm blacklist_postgresql-data 2>/dev/null || true"
        echo "docker-compose up -d"
        echo "python3 commands/utils/init_database.py"
        echo ""
        echo "# Force rebuild and restart:"
        echo "docker-compose down"
        echo "docker-compose build --no-cache"
        echo "docker-compose up -d"
        echo ""
        echo "# Clear Docker system cache:"
        echo "docker system prune -f"
        echo "docker volume prune -f"
        echo ""
        echo "# Check and fix permissions:"
        echo "sudo chown -R \$USER:\$USER ."
        echo "chmod +x scripts/*.sh"
        echo ""
        echo "# Environment file check:"
        echo "cp .env.example .env"
        echo "nano .env  # Configure your settings"
        echo ""
    } >> "$DIAGNOSTIC_OUTPUT"
    
    print_success "Repair suggestions added to diagnostic report"
}

run_quick_fixes() {
    print_section "QUICK FIXES"
    
    print_step "Applying quick fixes..."
    
    local fixes_applied=0
    
    # Fix 1: Check and create missing directories
    local required_dirs=("logs" "data" "data/postgresql" "data/redis")
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            print_info "Creating missing directory: $dir"
            mkdir -p "$dir"
            ((fixes_applied++))
        fi
    done
    
    # Fix 2: Fix script permissions
    if [ -d "scripts" ]; then
        print_info "Fixing script permissions..."
        find scripts -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null && ((fixes_applied++))
    fi
    
    # Fix 3: Clear any lock files
    local lock_files=(".env.lock" "deployment.lock")
    for lock_file in "${lock_files[@]}"; do
        if [ -f "$lock_file" ]; then
            print_info "Removing lock file: $lock_file"
            rm -f "$lock_file" && ((fixes_applied++))
        fi
    done
    
    # Fix 4: Restart unhealthy containers
    local unhealthy_containers=$(docker-compose ps | grep -E "(unhealthy|exited)" | awk '{print $1}' || true)
    if [ -n "$unhealthy_containers" ]; then
        print_info "Restarting unhealthy containers..."
        for container in $unhealthy_containers; do
            docker-compose restart "$container" 2>/dev/null && ((fixes_applied++))
        done
    fi
    
    if [ $fixes_applied -gt 0 ]; then
        print_success "Applied $fixes_applied quick fixes"
        
        # Wait for services to restart
        print_info "Waiting for services to stabilize..."
        sleep 10
        
        # Quick health check
        local health_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/health" 2>/dev/null || echo "000")
        if [ "$health_code" = "200" ]; then
            print_success "Services appear to be healthy after fixes"
        else
            print_warning "Services may still need attention (health check: $health_code)"
        fi
    else
        print_info "No quick fixes were needed"
    fi
}

interactive_mode() {
    print_section "INTERACTIVE TROUBLESHOOTING"
    
    echo "Select troubleshooting actions:"
    echo "1. Run comprehensive diagnostics"
    echo "2. Apply quick fixes only"
    echo "3. Restart all services"
    echo "4. Reset database (WARNING: Data loss)"
    echo "5. View live logs"
    echo "6. Exit"
    echo ""
    
    read -p "Enter your choice (1-6): " choice
    
    case $choice in
        1)
            run_full_diagnostics
            ;;
        2)
            run_quick_fixes
            ;;
        3)
            print_info "Restarting all services..."
            docker-compose restart
            print_success "Services restarted"
            ;;
        4)
            read -p "Are you sure you want to reset the database? (y/N): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                print_warning "Resetting database..."
                docker-compose down
                docker volume rm $(docker volume ls -q | grep postgresql) 2>/dev/null || true
                docker-compose up -d
                print_success "Database reset complete"
            else
                print_info "Database reset cancelled"
            fi
            ;;
        5)
            echo "Press Ctrl+C to stop viewing logs"
            docker-compose logs -f
            ;;
        6)
            echo "Exiting troubleshooter"
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            interactive_mode
            ;;
    esac
}

run_full_diagnostics() {
    print_step "Running comprehensive diagnostics..."
    
    collect_system_info
    check_docker_services
    check_network_connectivity
    check_database_connectivity  
    check_application_health
    check_resource_usage
    check_logs_for_errors
    generate_repair_suggestions
}

show_usage() {
    cat << EOF
Deployment Troubleshooting Tool

Usage: $0 [OPTIONS]

Options:
  --full              Run full diagnostic suite
  --quick-fix         Apply quick fixes only
  --interactive       Interactive troubleshooting mode
  --restart-services  Restart all Docker services
  --check-health      Quick health check only
  --view-logs         View recent logs
  --reset-db          Reset database (WARNING: Data loss)
  --help              Show this help message

Examples:
  $0 --full           # Complete diagnostic report
  $0 --quick-fix      # Apply common fixes
  $0 --interactive    # Interactive mode with menu
  $0 --check-health   # Quick status check

Output:
  Diagnostic report saved to: $DIAGNOSTIC_OUTPUT

EOF
}

# Main script logic
main() {
    local action=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                action="full"
                shift
                ;;
            --quick-fix)
                action="quick_fix"
                shift
                ;;
            --interactive)
                action="interactive"
                shift
                ;;
            --restart-services)
                action="restart"
                shift
                ;;
            --check-health)
                action="health"
                shift
                ;;
            --view-logs)
                action="logs"
                shift
                ;;
            --reset-db)
                action="reset_db"
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
        "full")
            run_full_diagnostics
            ;;
        "quick_fix")
            run_quick_fixes
            ;;
        "interactive")
            interactive_mode
            ;;
        "restart")
            print_info "Restarting all services..."
            docker-compose restart
            print_success "Services restarted"
            ;;
        "health")
            print_step "Quick health check..."
            local health_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/health" 2>/dev/null || echo "000")
            if [ "$health_code" = "200" ]; then
                print_success "System is healthy (HTTP $health_code)"
            else
                print_warning "System may have issues (HTTP $health_code)"
            fi
            ;;
        "logs")
            docker-compose logs -f --tail=50
            ;;
        "reset_db")
            read -p "Are you sure you want to reset the database? (y/N): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                print_warning "Resetting database..."
                docker-compose down
                docker volume rm $(docker volume ls -q | grep postgresql) 2>/dev/null || true
                docker-compose up -d
                print_success "Database reset complete"
            fi
            ;;
        "")
            print_warning "No action specified, running interactive mode"
            interactive_mode
            ;;
        *)
            print_error "Unknown action: $action"
            show_usage
            exit 1
            ;;
    esac
    
    # Show diagnostic report location
    if [ -f "$DIAGNOSTIC_OUTPUT" ]; then
        echo ""
        print_success "Diagnostic report saved to: $DIAGNOSTIC_OUTPUT"
        echo ""
        echo "To view the full report:"
        echo "  cat $DIAGNOSTIC_OUTPUT"
        echo ""
        echo "To share the report:"
        echo "  cat $DIAGNOSTIC_OUTPUT | curl -F 'sprunge=<-' http://sprunge.us"
    fi
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
trap 'print_error "Troubleshooting script failed at line $LINENO"' ERR

# Initialize
check_dependencies

# Run main logic
main "$@"
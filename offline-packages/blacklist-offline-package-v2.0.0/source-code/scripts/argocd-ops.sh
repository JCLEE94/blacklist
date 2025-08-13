#!/bin/bash

# ArgoCD GitOps Operations Script
# Usage: ./scripts/argocd-ops.sh [command]

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# ArgoCD Configuration
ARGOCD_SERVER=${ARGOCD_SERVER:-"argo.jclee.me"}
APP_NAME="blacklist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to get ArgoCD token
get_argocd_token() {
    if [ -z "$ARGOCD_TOKEN" ]; then
        log_info "Getting ArgoCD token..."
        local response=$(curl -k -s -X POST "https://${ARGOCD_SERVER}/api/v1/session" \
            -H "Content-Type: application/json" \
            -d '{"username":"admin","password":"bingogo1"}')
        
        ARGOCD_TOKEN=$(echo "$response" | jq -r '.token // empty')
        
        if [ -z "$ARGOCD_TOKEN" ] || [ "$ARGOCD_TOKEN" = "null" ]; then
            log_error "Failed to get ArgoCD token"
            echo "Response: $response"
            exit 1
        fi
        
        log_success "ArgoCD token obtained"
    fi
    
    export ARGOCD_TOKEN
}

# Function to make ArgoCD API calls
argocd_api() {
    local method="${1:-GET}"
    local endpoint="$2"
    local data="$3"
    
    get_argocd_token
    
    local curl_cmd="curl -k -s -X $method"
    curl_cmd="$curl_cmd -H 'Authorization: Bearer $ARGOCD_TOKEN'"
    curl_cmd="$curl_cmd -H 'Content-Type: application/json'"
    
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi
    
    curl_cmd="$curl_cmd https://${ARGOCD_SERVER}/api/v1$endpoint"
    
    eval $curl_cmd
}

# Function to check application status
check_app_status() {
    log_info "Checking $APP_NAME application status..."
    
    local response=$(argocd_api GET "/applications/$APP_NAME")
    
    if echo "$response" | jq -e '.status' > /dev/null 2>&1; then
        local sync_status=$(echo "$response" | jq -r '.status.sync.status // "Unknown"')
        local health_status=$(echo "$response" | jq -r '.status.health.status // "Unknown"')
        local revision=$(echo "$response" | jq -r '.status.sync.revision // "Unknown"')
        
        echo
        log_info "=== $APP_NAME Application Status ==="
        echo "Sync Status:   $sync_status"
        echo "Health Status: $health_status"
        echo "Revision:      ${revision:0:12}..."
        
        # Check for conditions/errors
        local conditions=$(echo "$response" | jq -r '.status.conditions // [] | length')
        if [ "$conditions" -gt 0 ]; then
            log_warning "Application has conditions/errors:"
            echo "$response" | jq -r '.status.conditions[] | "  - \(.type): \(.message)"'
        fi
        
        # Show resources status
        log_info "Resources Status:"
        echo "$response" | jq -r '.status.resources[] | "  \(.kind)/\(.name): \(.status)"' | head -10
        
        echo
    else
        log_error "Application not found or API error"
        echo "Response: $response"
        exit 1
    fi
}

# Function to sync application
sync_app() {
    log_info "Syncing $APP_NAME application..."
    
    local response=$(argocd_api POST "/applications/$APP_NAME/sync" '{"prune": true, "dryRun": false}')
    
    if echo "$response" | jq -e '.metadata' > /dev/null 2>&1; then
        log_success "Sync initiated successfully"
        
        # Wait a moment and check status
        sleep 3
        check_app_status
    else
        log_error "Failed to sync application"
        echo "Response: $response"
        exit 1
    fi
}

# Function to force refresh
refresh_app() {
    log_info "Refreshing $APP_NAME application..."
    
    local response=$(argocd_api POST "/applications/$APP_NAME/sync" '{"prune": false, "dryRun": false, "syncOptions": ["Validate=false"]}')
    
    if echo "$response" | jq -e '.metadata' > /dev/null 2>&1; then
        log_success "Refresh initiated successfully"
        sleep 2
        check_app_status
    else
        log_error "Failed to refresh application"
        echo "Response: $response"
        exit 1
    fi
}

# Function to list all applications
list_apps() {
    log_info "Listing all ArgoCD applications..."
    
    local response=$(argocd_api GET "/applications")
    
    if echo "$response" | jq -e '.items' > /dev/null 2>&1; then
        echo
        log_info "=== ArgoCD Applications ==="
        echo "$response" | jq -r '.items[] | "\(.metadata.name): \(.status.sync.status // "Unknown") / \(.status.health.status // "Unknown")"'
        echo
    else
        log_error "Failed to list applications"
        echo "Response: $response"
        exit 1
    fi
}

# Function to show application configuration
show_config() {
    log_info "Showing $APP_NAME configuration..."
    
    local response=$(argocd_api GET "/applications/$APP_NAME")
    
    if echo "$response" | jq -e '.spec' > /dev/null 2>&1; then
        echo
        log_info "=== $APP_NAME Configuration ==="
        echo "Repository: $(echo "$response" | jq -r '.spec.source.repoURL')"
        echo "Path:       $(echo "$response" | jq -r '.spec.source.path')"
        echo "Revision:   $(echo "$response" | jq -r '.spec.source.targetRevision')"
        echo "Project:    $(echo "$response" | jq -r '.spec.project')"
        echo "Namespace:  $(echo "$response" | jq -r '.spec.destination.namespace')"
        echo
        
        # Show sync policy
        log_info "Sync Policy:"
        echo "$response" | jq '.spec.syncPolicy'
        echo
    else
        log_error "Application not found or API error"
        echo "Response: $response"
        exit 1
    fi
}

# Function to fix application configuration
fix_app_config() {
    log_info "Fixing $APP_NAME application configuration..."
    
    # Check current app source path
    local response=$(argocd_api GET "/applications/$APP_NAME")
    local current_path=$(echo "$response" | jq -r '.spec.source.path')
    
    log_info "Current source path: $current_path"
    
    # The application is currently pointing to helm-chart/blacklist
    # But our new structure uses chart/blacklist
    if [ "$current_path" = "helm-chart/blacklist" ]; then
        log_warning "Application is using old path structure. Need to update to chart/blacklist"
        
        # This would require updating the ArgoCD application
        # For now, just show the issue
        log_info "Please update the ArgoCD application to use 'chart/blacklist' path"
    fi
}

# Function to show deployment history
show_history() {
    log_info "Showing $APP_NAME deployment history..."
    
    local response=$(argocd_api GET "/applications/$APP_NAME")
    
    if echo "$response" | jq -e '.status.history' > /dev/null 2>&1; then
        echo
        log_info "=== $APP_NAME Deployment History ==="
        echo "$response" | jq -r '.status.history[] | "ID: \(.id) | Revision: \(.revision[0:12]) | Deployed: \(.deployedAt)"' | tail -5
        echo
    else
        log_warning "No deployment history found"
    fi
}

# Main command dispatcher
case "${1:-status}" in
    "status"|"st")
        check_app_status
        ;;
    "sync"|"sy")
        sync_app
        ;;
    "refresh"|"rf")
        refresh_app
        ;;
    "list"|"ls")
        list_apps
        ;;
    "config"|"cfg")
        show_config
        ;;
    "fix")
        fix_app_config
        ;;
    "history"|"hist")
        show_history
        ;;
    "help"|"-h"|"--help")
        echo "ArgoCD GitOps Operations"
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  status, st    - Check application status (default)"
        echo "  sync, sy      - Sync application"
        echo "  refresh, rf   - Refresh application"
        echo "  list, ls      - List all applications"
        echo "  config, cfg   - Show application configuration"
        echo "  fix           - Fix application configuration"
        echo "  history, hist - Show deployment history"
        echo "  help          - Show this help"
        echo
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
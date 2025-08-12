#!/bin/bash

# ArgoCD Integration Script for Blacklist Management System
# Comprehensive CI/CD pipeline integration with AutoSync configuration
# =================================================================

set -euo pipefail

# Configuration
ARGOCD_SERVER="${ARGOCD_SERVER:-argo.jclee.me}"
ARGOCD_INTERNAL="${ARGOCD_INTERNAL:-192.168.50.110:31017}"
PROJECT_NAME="blacklist"
NAMESPACE="blacklist"
GIT_REPO="https://github.com/JCLEE94/blacklist.git"
HELM_CHART_PATH="helm-chart/blacklist"
REGISTRY="registry.jclee.me"
IMAGE_NAME="jclee94/blacklist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_tools=()
    
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v argocd >/dev/null 2>&1 || missing_tools+=("argocd")
    command -v curl >/dev/null 2>&1 || missing_tools+=("curl")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    log "All prerequisites satisfied"
    return 0
}

# Test ArgoCD connectivity
test_argocd_connectivity() {
    log "Testing ArgoCD connectivity..."
    
    # Try external endpoint first
    if curl -k -s --connect-timeout 5 "https://${ARGOCD_SERVER}/api/version" >/dev/null 2>&1; then
        log "External ArgoCD endpoint (${ARGOCD_SERVER}) is accessible"
        return 0
    else
        warn "External ArgoCD endpoint not accessible"
    fi
    
    # Try internal endpoint
    if curl -k -s --connect-timeout 5 "http://${ARGOCD_INTERNAL}/api/version" >/dev/null 2>&1; then
        log "Internal ArgoCD endpoint (${ARGOCD_INTERNAL}) is accessible"
        return 0
    else
        warn "Internal ArgoCD endpoint not accessible"
    fi
    
    error "Neither ArgoCD endpoint is accessible"
    return 1
}

# Login to ArgoCD
argocd_login() {
    log "Attempting ArgoCD login..."
    
    # Try external login first
    if argocd login "${ARGOCD_SERVER}" --username admin --password "${ARGOCD_PASS:-bingogo1}" --insecure 2>/dev/null; then
        log "Successfully logged into external ArgoCD"
        return 0
    else
        warn "External ArgoCD login failed"
    fi
    
    # Try internal login
    if argocd login "${ARGOCD_INTERNAL}" --username admin --password "${ARGOCD_PASS:-bingogo1}" --insecure 2>/dev/null; then
        log "Successfully logged into internal ArgoCD"
        return 0
    else
        warn "Internal ArgoCD login failed"
    fi
    
    error "Failed to login to any ArgoCD endpoint"
    return 1
}

# Check if application exists
check_application_exists() {
    log "Checking if ArgoCD application '${PROJECT_NAME}' exists..."
    
    if argocd app get "${PROJECT_NAME}" >/dev/null 2>&1; then
        log "Application '${PROJECT_NAME}' exists"
        return 0
    else
        info "Application '${PROJECT_NAME}' does not exist"
        return 1
    fi
}

# Create or update ArgoCD application
create_or_update_application() {
    log "Creating/updating ArgoCD application..."
    
    # Apply the application configuration
    if kubectl apply -f argocd/application.yaml; then
        log "ArgoCD application configuration applied successfully"
    else
        error "Failed to apply ArgoCD application configuration"
        return 1
    fi
    
    # Wait for application to be recognized
    sleep 10
    
    # Verify application was created
    if argocd app get "${PROJECT_NAME}" >/dev/null 2>&1; then
        log "Application '${PROJECT_NAME}' created/updated successfully"
        return 0
    else
        error "Failed to create/update application"
        return 1
    fi
}

# Configure AutoSync
configure_autosync() {
    log "Configuring AutoSync for application '${PROJECT_NAME}'..."
    
    # Enable automated sync
    if argocd app patch "${PROJECT_NAME}" --patch '[{
        "op": "replace",
        "path": "/spec/syncPolicy",
        "value": {
            "automated": {
                "prune": true,
                "selfHeal": true,
                "allowEmpty": false
            },
            "syncOptions": [
                "CreateNamespace=true",
                "PrunePropagationPolicy=foreground",
                "PruneLast=true"
            ],
            "retry": {
                "limit": 5,
                "backoff": {
                    "duration": "5s",
                    "factor": 2,
                    "maxDuration": "3m"
                }
            }
        }
    }]' --type json; then
        log "AutoSync configured successfully"
    else
        error "Failed to configure AutoSync"
        return 1
    fi
}

# Trigger initial sync
trigger_sync() {
    log "Triggering initial sync..."
    
    if argocd app sync "${PROJECT_NAME}" --prune; then
        log "Sync triggered successfully"
    else
        error "Failed to trigger sync"
        return 1
    fi
}

# Monitor sync status
monitor_sync() {
    log "Monitoring sync status..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local sync_status=$(argocd app get "${PROJECT_NAME}" -o json | jq -r '.status.sync.status // "Unknown"')
        local health_status=$(argocd app get "${PROJECT_NAME}" -o json | jq -r '.status.health.status // "Unknown"')
        
        info "Attempt $attempt/$max_attempts - Sync: $sync_status, Health: $health_status"
        
        if [ "$sync_status" = "Synced" ] && [ "$health_status" = "Healthy" ]; then
            log "Application is synced and healthy!"
            return 0
        fi
        
        if [ "$sync_status" = "OutOfSync" ]; then
            warn "Application is out of sync - triggering resync"
            argocd app sync "${PROJECT_NAME}" --prune || true
        fi
        
        sleep 10
        ((attempt++))
    done
    
    error "Sync monitoring timed out"
    return 1
}

# Generate deployment report
generate_report() {
    log "Generating deployment report..."
    
    local report_file="/tmp/blacklist-deployment-report.json"
    local app_info=$(argocd app get "${PROJECT_NAME}" -o json 2>/dev/null || echo '{}')
    
    # Get current image info
    local current_image="${REGISTRY}/${IMAGE_NAME}:latest"
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    
    # Create comprehensive report
    cat > "$report_file" << EOF
{
    "deployment_report": {
        "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
        "project_name": "${PROJECT_NAME}",
        "git_info": {
            "repository": "${GIT_REPO}",
            "commit": "${git_commit}",
            "branch": "${git_branch}"
        },
        "docker_info": {
            "registry": "${REGISTRY}",
            "image": "${current_image}",
            "build_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        },
        "argocd_info": {
            "server": "${ARGOCD_SERVER}",
            "application_name": "${PROJECT_NAME}",
            "namespace": "${NAMESPACE}",
            "sync_status": $(echo "$app_info" | jq -r '.status.sync.status // "Unknown"' | jq -R .),
            "health_status": $(echo "$app_info" | jq -r '.status.health.status // "Unknown"' | jq -R .),
            "sync_revision": $(echo "$app_info" | jq -r '.status.sync.revision // "Unknown"' | jq -R .),
            "autosync_enabled": $(echo "$app_info" | jq -r '.spec.syncPolicy.automated != null' | jq -R .)
        },
        "kubernetes_info": {
            "cluster": "$(kubectl config current-context 2>/dev/null || echo "unknown")",
            "namespace": "${NAMESPACE}"
        }
    }
}
EOF
    
    # Display formatted report
    echo
    log "🚀 BLACKLIST DEPLOYMENT REPORT"
    echo "=================================="
    echo
    info "📦 Docker Image:"
    echo "- Repository: ${REGISTRY}/${IMAGE_NAME}"
    echo "- Tag: latest"
    echo "- Build: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo
    info "📊 Git Information:"
    echo "- Repository: ${GIT_REPO}"
    echo "- Branch: ${git_branch}"
    echo "- Commit: ${git_commit}"
    echo
    info "☸️ ArgoCD Status:"
    echo "- Server: ${ARGOCD_SERVER}"
    echo "- Application: ${PROJECT_NAME}"
    echo "- Sync Status: $(echo "$app_info" | jq -r '.status.sync.status // "Unknown"')"
    echo "- Health: $(echo "$app_info" | jq -r '.status.health.status // "Unknown"')"
    echo "- AutoSync: $(echo "$app_info" | jq -r '.spec.syncPolicy.automated != null')"
    echo
    info "🌐 Access URLs:"
    echo "- Application: https://blacklist.jclee.me"
    echo "- ArgoCD: https://argo.jclee.me/applications/${PROJECT_NAME}"
    echo "- Registry: https://registry.jclee.me"
    echo
    log "Report saved to: $report_file"
}

# Main execution
main() {
    log "Starting ArgoCD Integration for Blacklist Management System"
    log "=========================================================="
    
    # Execute integration steps
    check_prerequisites || exit 1
    test_argocd_connectivity || exit 1
    
    # Only proceed if ArgoCD is accessible
    if argocd_login; then
        if ! check_application_exists; then
            create_or_update_application || exit 1
        else
            log "Application exists, ensuring it's up to date"
            create_or_update_application || exit 1
        fi
        
        configure_autosync || exit 1
        trigger_sync || exit 1
        monitor_sync || exit 1
        generate_report
        
        log "✅ ArgoCD integration completed successfully!"
    else
        warn "ArgoCD not accessible, applying Kubernetes configuration directly"
        kubectl apply -f argocd/application.yaml || exit 1
        log "✅ Kubernetes configuration applied (ArgoCD integration pending)"
    fi
}

# Execute main function
main "$@"
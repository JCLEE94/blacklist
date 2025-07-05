#!/bin/bash
# Unified management script for blacklist CI/CD pipeline

set -euo pipefail

# Script directory and imports
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/security.sh"
source "${SCRIPT_DIR}/lib/k8s-utils.sh"

# Set error trap
set_error_trap

# Default values
DEFAULT_ENV="dev"
DEFAULT_NAMESPACE="blacklist"

# Global variables
ENV=""
NAMESPACE=""
CLUSTER=""

# Usage information
usage() {
    cat << EOF
Blacklist CI/CD Management Tool

Usage: $0 <command> [options]

Commands:
    init        Initialize the environment (secrets, configs)
    deploy      Deploy the application
    status      Show deployment status
    logs        View application logs
    rollback    Rollback to previous version
    scale       Scale the deployment
    test        Run integration tests
    clean       Clean up resources
    security    Security audit

Options:
    -e, --env <env>         Environment (dev|staging|prod) [default: $DEFAULT_ENV]
    -n, --namespace <ns>    Kubernetes namespace [default: $DEFAULT_NAMESPACE]
    -c, --cluster <name>    Target cluster name
    -h, --help             Show this help message

Examples:
    $0 init                          # Initialize with defaults
    $0 deploy --env prod            # Deploy to production
    $0 status                        # Check deployment status
    $0 logs -f                       # Follow logs
    $0 scale --replicas 5           # Scale to 5 replicas
    $0 rollback --revision 2        # Rollback to revision 2
    $0 security                      # Run security audit

Environment Variables:
    The script uses .env file or environment variables for configuration.
    See .env.example for required variables.

EOF
}

# Parse command line arguments
parse_args() {
    local command="${1:-}"
    shift || true
    
    # Set defaults
    ENV="$DEFAULT_ENV"
    NAMESPACE="$DEFAULT_NAMESPACE"
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -e|--env)
                ENV="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -c|--cluster)
                CLUSTER="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                # Pass remaining args to command functions
                break
                ;;
        esac
    done
    
    # Execute command
    case "$command" in
        init)     cmd_init "$@" ;;
        deploy)   cmd_deploy "$@" ;;
        status)   cmd_status "$@" ;;
        logs)     cmd_logs "$@" ;;
        rollback) cmd_rollback "$@" ;;
        scale)    cmd_scale "$@" ;;
        test)     cmd_test "$@" ;;
        clean)    cmd_clean "$@" ;;
        security) cmd_security "$@" ;;
        "")       usage; exit 1 ;;
        *)        
            print_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Initialize environment
cmd_init() {
    print_step "Initializing environment..."
    
    # Load environment variables
    local env_file=".env"
    if [[ -n "$ENV" ]] && [[ "$ENV" != "dev" ]]; then
        env_file=".env.$ENV"
    fi
    
    if ! load_env "$env_file"; then
        print_error "Failed to load environment file: $env_file"
        print_info "Copy .env.example to $env_file and configure it"
        exit 1
    fi
    
    # Validate credentials
    if ! validate_credentials; then
        exit 1
    fi
    
    # Check Kubernetes connection
    if ! check_k8s_connection; then
        exit 1
    fi
    
    # Create namespace
    print_step "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Create registry secret
    create_registry_secret "$NAMESPACE"
    
    # Initialize ArgoCD if available
    if command -v argocd &> /dev/null; then
        print_step "Setting up ArgoCD..."
        # ArgoCD setup would go here
        print_info "ArgoCD setup skipped (implement based on requirements)"
    fi
    
    print_success "Environment initialized successfully"
}

# Deploy application
cmd_deploy() {
    print_step "Deploying application to $ENV environment..."
    
    # Load environment
    local env_file=".env"
    if [[ -n "$ENV" ]] && [[ "$ENV" != "dev" ]]; then
        env_file=".env.$ENV"
    fi
    load_env "$env_file"
    
    # Validate credentials
    validate_credentials || exit 1
    
    # Check connection
    check_k8s_connection || exit 1
    
    # Apply manifests
    local manifest_path="k8s/"
    if [[ -d "k8s/overlays/$ENV" ]]; then
        manifest_path="k8s/overlays/$ENV"
    fi
    
    print_step "Applying manifests from: $manifest_path"
    apply_manifests "$manifest_path"
    
    # Wait for deployment
    wait_for_deployment "blacklist" "$NAMESPACE"
    
    # Get service URL
    local service_url=$(get_service_url "blacklist" "$NAMESPACE")
    print_success "Deployment completed successfully"
    print_info "Service URL: $service_url"
}

# Show status
cmd_status() {
    print_step "Checking deployment status..."
    
    # Check connection
    check_k8s_connection || exit 1
    
    # Get deployment info
    get_deployment_info "blacklist" "$NAMESPACE"
    
    # Get service URL
    echo ""
    local service_url=$(get_service_url "blacklist" "$NAMESPACE")
    print_info "Service URL: $service_url"
    
    # Check ArgoCD status if available
    if command -v argocd &> /dev/null; then
        echo ""
        print_step "ArgoCD Application Status:"
        argocd app get blacklist --grpc-web 2>/dev/null || print_warning "ArgoCD app not found"
    fi
}

# View logs
cmd_logs() {
    local follow=false
    local tail_lines=100
    
    # Parse logs options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--follow)
                follow=true
                shift
                ;;
            -n|--tail)
                tail_lines="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # Get logs
    get_deployment_logs "blacklist" "$NAMESPACE" "$tail_lines" "$follow"
}

# Rollback deployment
cmd_rollback() {
    local revision=""
    
    # Parse rollback options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -r|--revision)
                revision="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    print_step "Rolling back deployment..."
    
    if [[ -n "$revision" ]]; then
        kubectl rollout undo deployment/blacklist -n "$NAMESPACE" --to-revision="$revision"
    else
        kubectl rollout undo deployment/blacklist -n "$NAMESPACE"
    fi
    
    wait_for_deployment "blacklist" "$NAMESPACE"
    print_success "Rollback completed successfully"
}

# Scale deployment
cmd_scale() {
    local replicas=3
    
    # Parse scale options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -r|--replicas)
                replicas="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    scale_deployment "blacklist" "$replicas" "$NAMESPACE"
}

# Run tests
cmd_test() {
    print_step "Running integration tests..."
    
    # Get service URL
    local service_url=$(get_service_url "blacklist" "$NAMESPACE")
    
    # Basic health check
    print_info "Testing health endpoint..."
    if curl -f "${service_url}/health" > /dev/null 2>&1; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        exit 1
    fi
    
    # Run Python integration tests if available
    if [[ -f "scripts/integration_test_comprehensive.py" ]]; then
        print_info "Running comprehensive integration tests..."
        python3 scripts/integration_test_comprehensive.py
    fi
    
    print_success "All tests passed"
}

# Clean up resources
cmd_clean() {
    print_warning "This will delete all resources in namespace: $NAMESPACE"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleanup cancelled"
        exit 0
    fi
    
    print_step "Cleaning up resources..."
    
    # Delete Kubernetes resources
    delete_resources "k8s/"
    
    # Optionally delete namespace
    read -p "Delete namespace $NAMESPACE? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    fi
    
    print_success "Cleanup completed"
}

# Security audit
cmd_security() {
    print_step "Running security audit..."
    
    # Check for hardcoded secrets
    print_info "Checking for hardcoded secrets..."
    if ! check_hardcoded_secrets "$SCRIPT_DIR"; then
        print_warning "Security issues found in scripts directory"
    fi
    
    # Check Kubernetes security
    print_info "Checking Kubernetes security policies..."
    
    # Check if pods are running as non-root
    local root_pods=$(kubectl get pods -n "$NAMESPACE" -o json | \
        jq -r '.items[] | select(.spec.securityContext.runAsUser == 0 or .spec.securityContext.runAsUser == null) | .metadata.name')
    
    if [[ -n "$root_pods" ]]; then
        print_warning "Pods running as root user:"
        echo "$root_pods"
    else
        print_success "All pods running as non-root"
    fi
    
    # Check for exposed secrets
    print_info "Checking for exposed secrets in environment..."
    kubectl get pods -n "$NAMESPACE" -o json | \
        jq -r '.items[].spec.containers[].env[]? | select(.value != null) | .name' | \
        grep -i -E "(password|token|secret|key)" || true
    
    print_success "Security audit completed"
}

# Main execution
main() {
    # Check for help flag first
    if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi
    
    # Check prerequisites
    local required_commands=("kubectl" "curl" "jq")
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            exit 1
        fi
    done
    
    # Parse arguments and execute
    parse_args "$@"
}

# Run main function
main "$@"
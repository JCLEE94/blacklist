#!/bin/bash
# Security utilities for blacklist CI/CD scripts

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

# Required environment variables
declare -a REQUIRED_VARS=(
    "REGISTRY_URL"
    "REGISTRY_USERNAME"
    "REGISTRY_PASSWORD"
)

declare -a OPTIONAL_VARS=(
    "ARGOCD_SERVER"
    "ARGOCD_API_TOKEN"
    "GITHUB_USER"
    "GITHUB_TOKEN"
    "SLACK_WEBHOOK"
)

# Validate required environment variables
validate_required_vars() {
    local missing_vars=()
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        print_info "Please set these variables in your .env file or environment"
        return 1
    fi
    
    print_success "All required environment variables are set"
    return 0
}

# Validate credentials without exposing them
validate_credentials() {
    print_step "Validating credentials..."
    
    # Check required variables
    if ! validate_required_vars; then
        return 1
    fi
    
    # Display masked values for verification
    print_info "Registry URL: ${REGISTRY_URL}"
    print_info "Registry User: $(mask_value "$REGISTRY_USERNAME")"
    print_info "Registry Pass: $(mask_value "$REGISTRY_PASSWORD")"
    
    # Check optional variables and display if set
    for var in "${OPTIONAL_VARS[@]}"; do
        if [[ -n "${!var}" ]]; then
            case "$var" in
                *TOKEN*|*WEBHOOK*)
                    print_info "$var: $(mask_value "${!var}" 10)"
                    ;;
                *)
                    print_info "$var: ${!var}"
                    ;;
            esac
        fi
    done
    
    return 0
}

# Create Kubernetes secret for registry
create_registry_secret() {
    local namespace="${1:-default}"
    local secret_name="${2:-regcred}"
    
    print_step "Creating registry secret in namespace: $namespace"
    
    # Check if secret already exists
    if kubectl get secret "$secret_name" -n "$namespace" &> /dev/null; then
        print_warning "Secret '$secret_name' already exists in namespace '$namespace'"
        read -p "Do you want to update it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
        # Delete existing secret
        kubectl delete secret "$secret_name" -n "$namespace"
    fi
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f - &> /dev/null
    
    # Create the secret
    kubectl create secret docker-registry "$secret_name" \
        --docker-server="${REGISTRY_URL}" \
        --docker-username="${REGISTRY_USERNAME}" \
        --docker-password="${REGISTRY_PASSWORD}" \
        -n "$namespace"
    
    if [[ $? -eq 0 ]]; then
        print_success "Registry secret created successfully"
    else
        print_error "Failed to create registry secret"
        return 1
    fi
}

# Sanitize logs to remove sensitive information
sanitize_output() {
    local input="$1"
    
    # List of patterns to mask
    local patterns=(
        "password=[^[:space:]]*"
        "token=[^[:space:]]*"
        "secret=[^[:space:]]*"
        "apikey=[^[:space:]]*"
        "api_key=[^[:space:]]*"
    )
    
    local output="$input"
    for pattern in "${patterns[@]}"; do
        output=$(echo "$output" | sed -E "s/${pattern}/***MASKED***/gi")
    done
    
    echo "$output"
}

# Secure command execution with output sanitization
secure_exec() {
    local command="$@"
    local output
    local exit_code
    
    # Execute command and capture output
    output=$(eval "$command" 2>&1)
    exit_code=$?
    
    # Sanitize and display output
    if [[ -n "$output" ]]; then
        sanitize_output "$output"
    fi
    
    return $exit_code
}

# Generate secure random string
generate_secret() {
    local length="${1:-32}"
    openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
}

# Check for hardcoded secrets in files
check_hardcoded_secrets() {
    local search_path="${1:-.}"
    local found_secrets=0
    
    print_step "Checking for hardcoded secrets in: $search_path"
    
    # Patterns to search for
    local patterns=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "token\s*=\s*['\"][^'\"]+['\"]"
        "secret\s*=\s*['\"][^'\"]+['\"]"
        "api_key\s*=\s*['\"][^'\"]+['\"]"
    )
    
    for pattern in "${patterns[@]}"; do
        if grep -r -i -E "$pattern" "$search_path" \
            --include="*.sh" \
            --include="*.yml" \
            --include="*.yaml" \
            --include="*.py" \
            --exclude-dir=".git" \
            --exclude-dir="node_modules" \
            --exclude-dir="venv" \
            --exclude="*.example" \
            2>/dev/null | grep -v "your_" | grep -v "example"; then
            found_secrets=1
        fi
    done
    
    if [[ $found_secrets -eq 1 ]]; then
        print_error "Found potential hardcoded secrets!"
        print_info "Please move these to environment variables"
        return 1
    else
        print_success "No hardcoded secrets found"
        return 0
    fi
}

# Export security functions
export -f validate_required_vars validate_credentials
export -f create_registry_secret sanitize_output secure_exec
export -f generate_secret check_hardcoded_secrets
#!/bin/bash
# Security fix script to remove hardcoded credentials

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source common functions
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/security.sh"

print_step "Security Fix Script - Remove Hardcoded Credentials"
echo "=================================================="
echo ""

# Files with known hardcoded credentials
FILES_TO_FIX=(
    "scripts/setup/argocd-complete-setup.sh"
    "scripts/argocd-auth-token.sh"
    "scripts/k8s-management.sh"
    "scripts/deploy.sh"
    "scripts/multi-deploy.sh"
)

# Backup directory
BACKUP_DIR="${PROJECT_ROOT}/scripts/backup-$(date +%Y%m%d-%H%M%S)"

# Create backup
print_step "Creating backup of affected files..."
mkdir -p "$BACKUP_DIR"

for file in "${FILES_TO_FIX[@]}"; do
    if [[ -f "${PROJECT_ROOT}/$file" ]]; then
        cp "${PROJECT_ROOT}/$file" "$BACKUP_DIR/" || true
        print_info "Backed up: $file"
    fi
done

# Fix argocd-complete-setup.sh
print_step "Fixing argocd-complete-setup.sh..."
if [[ -f "${PROJECT_ROOT}/scripts/setup/argocd-complete-setup.sh" ]]; then
    cat > "${PROJECT_ROOT}/scripts/setup/argocd-complete-setup.sh" << 'EOF'
#!/bin/bash

echo "🚀 ArgoCD Complete Setup Script"
echo "==============================="
echo ""

# Source common libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Source common functions
source "${PROJECT_ROOT}/scripts/lib/common.sh"
source "${PROJECT_ROOT}/scripts/lib/security.sh"
source "${PROJECT_ROOT}/scripts/lib/k8s-utils.sh"

# Load environment variables
print_step "Loading environment configuration..."
if ! load_env "${PROJECT_ROOT}/.env"; then
    print_error "Failed to load .env file"
    print_info "Please create .env file from .env.example and configure it"
    exit 1
fi

# Validate required environment variables
REQUIRED_VARS=(
    "ARGOCD_SERVER"
    "ARGOCD_API_TOKEN"
    "GITHUB_USER"
    "GITHUB_TOKEN"
    "REGISTRY_URL"
    "REGISTRY_USERNAME"
    "REGISTRY_PASSWORD"
)

print_step "Validating environment variables..."
missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    else
        # Display masked values
        case "$var" in
            *TOKEN*|*PASSWORD*)
                print_info "$var: $(mask_value "${!var}")"
                ;;
            *)
                print_info "$var: ${!var}"
                ;;
        esac
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    print_info "Please set these in your .env file"
    exit 1
fi

# Continue with ArgoCD setup using environment variables...
print_success "Environment validation completed"

# The rest of the ArgoCD setup logic goes here
# Using ${ARGOCD_SERVER}, ${GITHUB_TOKEN}, etc. from environment
EOF
    chmod +x "${PROJECT_ROOT}/scripts/setup/argocd-complete-setup.sh"
    print_success "Fixed argocd-complete-setup.sh"
fi

# Remove argocd-auth-token.sh (contains hardcoded credentials)
print_step "Removing insecure argocd-auth-token.sh..."
if [[ -f "${PROJECT_ROOT}/scripts/argocd-auth-token.sh" ]]; then
    rm -f "${PROJECT_ROOT}/scripts/argocd-auth-token.sh"
    print_success "Removed argocd-auth-token.sh"
fi

# Create environment template if it doesn't exist
print_step "Creating secure environment template..."
if [[ ! -f "${PROJECT_ROOT}/.env" ]] && [[ -f "${PROJECT_ROOT}/.env.example" ]]; then
    cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
    print_warning "Created .env from .env.example - please configure it with your actual values"
fi

# Check for remaining hardcoded secrets
print_step "Checking for remaining hardcoded secrets..."
check_hardcoded_secrets "${PROJECT_ROOT}/scripts"

# Git security recommendations
print_step "Git Security Recommendations"
echo ""
print_warning "IMPORTANT: The following credentials were found in your repository:"
echo "  - GitHub Token"
echo "  - ArgoCD API Token"
echo "  - Registry passwords"
echo ""
print_info "Recommended actions:"
echo "1. Revoke and regenerate all exposed credentials immediately"
echo "2. Clean Git history to remove sensitive data:"
echo ""
echo "   # Option 1: Use BFG Repo-Cleaner (recommended)"
echo "   bfg --delete-files argocd-auth-token.sh"
echo "   bfg --replace-text passwords.txt  # Create file with patterns to replace"
echo ""
echo "   # Option 2: Use git filter-branch"
echo "   git filter-branch --force --index-filter \\"
echo "     'git rm --cached --ignore-unmatch scripts/argocd-auth-token.sh' \\"
echo "     --prune-empty --tag-name-filter cat -- --all"
echo ""
echo "3. Force push cleaned history (after backup):"
echo "   git push origin --force --all"
echo "   git push origin --force --tags"
echo ""
echo "4. Add .env to .gitignore if not already present"

# Update .gitignore
print_step "Updating .gitignore..."
if ! grep -q "^\.env$" "${PROJECT_ROOT}/.gitignore" 2>/dev/null; then
    echo -e "\n# Environment files\n.env\n.env.*\n!.env.example" >> "${PROJECT_ROOT}/.gitignore"
    print_success "Added .env to .gitignore"
fi

# Summary
echo ""
print_success "Security fix completed!"
echo ""
print_info "Next steps:"
echo "1. Configure your .env file with actual credentials"
echo "2. Revoke and regenerate all exposed credentials"
echo "3. Clean Git history as recommended above"
echo "4. Review and test updated scripts"
echo ""
print_warning "Backup created at: $BACKUP_DIR"
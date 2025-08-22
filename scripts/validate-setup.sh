#!/bin/bash
# Setup Validation Script
# Version: v1.0.37
# Purpose: Validate unified Docker Compose setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[VALIDATE]${NC} $1"
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

# Validation results
ERRORS=0
WARNINGS=0

check_files() {
    log "Checking required files..."
    
    local required_files=(
        "docker-compose.yml"
        ".env.unified"
        ".env.development.new"
        ".env.production.new"
        ".env.testing"
        "scripts/docker-environment.sh"
        "scripts/migrate-compose.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            success "✓ $file exists"
        else
            error "✗ $file missing"
            ((ERRORS++))
        fi
    done
}

check_docker_compose_syntax() {
    log "Checking Docker Compose syntax..."
    
    # Test with different environment files
    local env_files=(".env.unified" ".env.development.new" ".env.production.new" ".env.testing")
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            log "Testing with $env_file..."
            if cp "$env_file" .env.test && docker-compose -f docker-compose.yml --env-file .env.test config > /dev/null 2>&1; then
                success "✓ $env_file syntax valid"
            else
                error "✗ $env_file syntax error"
                ((ERRORS++))
            fi
            rm -f .env.test
        fi
    done
}

check_environment_variables() {
    log "Checking environment variable completeness..."
    
    local critical_vars=(
        "DEPLOYMENT_ENV"
        "EXTERNAL_PORT"
        "INTERNAL_PORT"
        "POSTGRES_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )
    
    local env_files=(".env.development.new" ".env.production.new" ".env.testing")
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            log "Checking $env_file..."
            for var in "${critical_vars[@]}"; do
                if grep -q "^${var}=" "$env_file"; then
                    success "✓ $env_file has $var"
                else
                    error "✗ $env_file missing $var"
                    ((ERRORS++))
                fi
            done
        fi
    done
}

check_port_conflicts() {
    log "Checking for port conflicts between environments..."
    
    local dev_port=$(grep "^EXTERNAL_PORT=" .env.development.new 2>/dev/null | cut -d'=' -f2 || echo "2542")
    local prod_port=$(grep "^EXTERNAL_PORT=" .env.production.new 2>/dev/null | cut -d'=' -f2 || echo "32542")
    local test_port=$(grep "^EXTERNAL_PORT=" .env.testing 2>/dev/null | cut -d'=' -f2 || echo "12542")
    
    if [[ "$dev_port" != "$prod_port" ]] && [[ "$dev_port" != "$test_port" ]] && [[ "$prod_port" != "$test_port" ]]; then
        success "✓ No port conflicts (dev:$dev_port, prod:$prod_port, test:$test_port)"
    else
        error "✗ Port conflicts detected (dev:$dev_port, prod:$prod_port, test:$test_port)"
        ((ERRORS++))
    fi
}

check_volume_paths() {
    log "Checking volume path configuration..."
    
    local env_files=(".env.development.new" ".env.production.new" ".env.testing")
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            local data_path=$(grep "^DATA_PATH=" "$env_file" 2>/dev/null | cut -d'=' -f2)
            local logs_path=$(grep "^LOGS_PATH=" "$env_file" 2>/dev/null | cut -d'=' -f2)
            
            if [[ -n "$data_path" ]] && [[ -n "$logs_path" ]]; then
                success "✓ $env_file has volume paths configured"
            else
                warning "⚠ $env_file missing volume path configuration"
                ((WARNINGS++))
            fi
        fi
    done
}

check_service_profiles() {
    log "Checking service profiles configuration..."
    
    # Check if profiles are defined in docker-compose.yml
    if grep -q "profiles:" docker-compose.yml; then
        local profiles=$(grep -A1 "profiles:" docker-compose.yml | grep -v "profiles:" | sed 's/.*- //' | sort -u)
        success "✓ Found profiles: $profiles"
    else
        warning "⚠ No profiles found in docker-compose.yml"
        ((WARNINGS++))
    fi
}

check_resource_limits() {
    log "Checking resource limits configuration..."
    
    if grep -q "deploy:" docker-compose.yml && grep -q "resources:" docker-compose.yml; then
        success "✓ Resource limits configured"
    else
        warning "⚠ No resource limits found"
        ((WARNINGS++))
    fi
}

check_script_permissions() {
    log "Checking script permissions..."
    
    local scripts=("scripts/docker-environment.sh" "scripts/migrate-compose.sh" "scripts/validate-setup.sh")
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            if [[ -x "$script" ]]; then
                success "✓ $script is executable"
            else
                error "✗ $script is not executable"
                ((ERRORS++))
            fi
        fi
    done
}

test_management_script() {
    log "Testing management script..."
    
    if [[ -f "scripts/docker-environment.sh" ]]; then
        if ./scripts/docker-environment.sh --help > /dev/null 2>&1; then
            success "✓ Management script works"
        else
            error "✗ Management script fails"
            ((ERRORS++))
        fi
    fi
}

check_security_defaults() {
    log "Checking security defaults..."
    
    # Check for default passwords in production
    if grep -q "change.*production\|default.*password\|admin.*123" .env.production.new 2>/dev/null; then
        warning "⚠ Production file contains default credentials - UPDATE BEFORE USE"
        ((WARNINGS++))
    else
        success "✓ No obvious default credentials in production file"
    fi
    
    # Check for debug mode in production
    if grep -q "DEBUG=true" .env.production.new 2>/dev/null; then
        error "✗ Debug mode enabled in production file"
        ((ERRORS++))
    else
        success "✓ Debug mode disabled in production"
    fi
}

generate_report() {
    local report_file="VALIDATION_REPORT_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
Docker Compose Setup Validation Report
======================================

Validation Date: $(date)
Validation Version: v1.0.37

Summary:
--------
Errors: $ERRORS
Warnings: $WARNINGS

Status: $([ $ERRORS -eq 0 ] && echo "PASS" || echo "FAIL")

Files Checked:
--------------
- docker-compose.yml
- .env.unified
- .env.development.new
- .env.production.new
- .env.testing
- scripts/docker-environment.sh
- scripts/migrate-compose.sh

Validation Areas:
-----------------
1. File existence
2. Docker Compose syntax
3. Environment variables completeness
4. Port conflict detection
5. Volume path configuration
6. Service profiles
7. Resource limits
8. Script permissions
9. Management script functionality
10. Security defaults

Next Steps:
-----------
EOF

    if [[ $ERRORS -gt 0 ]]; then
        cat >> "$report_file" << EOF
❌ ERRORS FOUND: Fix the $ERRORS error(s) before proceeding.
EOF
    else
        cat >> "$report_file" << EOF
✅ VALIDATION PASSED: Setup is ready for use.

Recommended next steps:
1. Review and update credentials in .env.production.new
2. Test with: ./scripts/docker-environment.sh start development
3. Verify services: ./scripts/docker-environment.sh health
EOF
    fi

    if [[ $WARNINGS -gt 0 ]]; then
        cat >> "$report_file" << EOF

⚠️  $WARNINGS warning(s) found - review recommended but not blocking.
EOF
    fi

    log "Report generated: $report_file"
}

# Main execution
main() {
    log "Starting unified Docker Compose setup validation..."
    echo
    
    check_files
    echo
    
    check_docker_compose_syntax
    echo
    
    check_environment_variables
    echo
    
    check_port_conflicts
    echo
    
    check_volume_paths
    echo
    
    check_service_profiles
    echo
    
    check_resource_limits
    echo
    
    check_script_permissions
    echo
    
    test_management_script
    echo
    
    check_security_defaults
    echo
    
    # Summary
    log "Validation Summary:"
    log "Errors: $ERRORS"
    log "Warnings: $WARNINGS"
    
    if [[ $ERRORS -eq 0 ]]; then
        success "✅ VALIDATION PASSED - Setup is ready for use!"
        echo
        success "Next steps:"
        success "1. Review and update credentials in .env.production.new"
        success "2. Test with: ./scripts/docker-environment.sh start development"
        success "3. Check health: ./scripts/docker-environment.sh health"
    else
        error "❌ VALIDATION FAILED - Fix $ERRORS error(s) before proceeding"
        echo
        error "Common fixes:"
        error "1. Create missing files from templates"
        error "2. Check Docker Compose syntax"
        error "3. Set execute permissions on scripts"
    fi
    
    if [[ $WARNINGS -gt 0 ]]; then
        warning "⚠️  $WARNINGS warning(s) found - review recommended"
    fi
    
    generate_report
    
    return $ERRORS
}

main "$@"
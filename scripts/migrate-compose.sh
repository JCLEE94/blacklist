#!/bin/bash
# Docker Compose Migration Script
# Version: v1.0.37
# Purpose: Migrate from multiple compose files to unified setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Migration steps
migrate_compose_files() {
    log "Starting Docker Compose migration..."
    
    # 1. Backup existing files
    log "Step 1: Backing up existing files..."
    mkdir -p archive/docker-compose-backup-$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="archive/docker-compose-backup-$(date +%Y%m%d_%H%M%S)"
    
    [[ -f docker-compose.yml ]] && cp docker-compose.yml "$BACKUP_DIR/"
    [[ -f docker-compose.watchtower.yml ]] && cp docker-compose.watchtower.yml "$BACKUP_DIR/"
    [[ -f docker-compose.performance.yml ]] && cp docker-compose.performance.yml "$BACKUP_DIR/"
    [[ -f .env ]] && cp .env "$BACKUP_DIR/"
    [[ -f .env.example ]] && cp .env.example "$BACKUP_DIR/"
    [[ -f .env.development ]] && cp .env.development "$BACKUP_DIR/"
    [[ -f .env.production ]] && cp .env.production "$BACKUP_DIR/"
    
    success "Backup created in $BACKUP_DIR"
    
    # 2. Replace main docker-compose.yml
    log "Step 2: Replacing main docker-compose.yml..."
    if [[ -f docker-compose.unified.yml ]]; then
        cp docker-compose.unified.yml docker-compose.yml
        success "docker-compose.yml updated with unified configuration"
    else
        error "docker-compose.unified.yml not found!"
        exit 1
    fi
    
    # 3. Setup environment files
    log "Step 3: Setting up environment files..."
    
    # Create .env from .env.unified
    if [[ -f .env.unified ]]; then
        cp .env.unified .env
        success ".env created from .env.unified"
    else
        warning ".env.unified not found, keeping existing .env"
    fi
    
    # Update .env.example
    if [[ -f .env.unified ]]; then
        cp .env.unified .env.example
        success ".env.example updated"
    fi
    
    # 4. Rename old environment-specific files
    log "Step 4: Renaming old environment files..."
    [[ -f .env.development ]] && mv .env.development .env.development.old
    [[ -f .env.production ]] && mv .env.production .env.production.old
    
    # 5. Move deployments directory files
    log "Step 5: Archiving deployments directory..."
    if [[ -d deployments/docker-compose ]]; then
        mv deployments/docker-compose "$BACKUP_DIR/"
        success "deployments/docker-compose archived"
    fi
    
    # 6. Archive old compose files
    log "Step 6: Archiving old compose files..."
    [[ -f docker-compose.watchtower.yml ]] && mv docker-compose.watchtower.yml "$BACKUP_DIR/"
    [[ -f docker-compose.performance.yml ]] && mv docker-compose.performance.yml "$BACKUP_DIR/"
    
    success "Old compose files archived"
}

# Validation function
validate_migration() {
    log "Validating migration..."
    
    local issues=0
    
    # Check required files
    if [[ ! -f docker-compose.yml ]]; then
        error "docker-compose.yml not found"
        ((issues++))
    fi
    
    if [[ ! -f .env ]]; then
        error ".env file not found"
        ((issues++))
    fi
    
    if [[ ! -f scripts/docker-environment.sh ]]; then
        error "scripts/docker-environment.sh not found"
        ((issues++))
    fi
    
    # Check environment files
    if [[ ! -f .env.development.new ]]; then
        warning ".env.development.new not found (will be created from .env.unified)"
    fi
    
    if [[ ! -f .env.production.new ]]; then
        warning ".env.production.new not found (will be created from .env.unified)"
    fi
    
    # Test docker-compose syntax
    if ! docker-compose config > /dev/null 2>&1; then
        error "docker-compose.yml syntax error"
        ((issues++))
    else
        success "docker-compose.yml syntax is valid"
    fi
    
    if [[ $issues -gt 0 ]]; then
        error "Migration validation failed with $issues issues"
        return 1
    else
        success "Migration validation passed"
        return 0
    fi
}

# Generate migration report
generate_report() {
    local report_file="MIGRATION_REPORT_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# Docker Compose Migration Report

**Migration Date**: $(date)
**Migration Version**: v1.0.37

## Summary

The Docker Compose configuration has been successfully unified into a single file with environment-specific overrides.

## Changes Made

### 1. File Structure Changes

#### Old Structure:
- \`docker-compose.yml\` - Main configuration
- \`docker-compose.watchtower.yml\` - Watchtower service
- \`docker-compose.performance.yml\` - Performance optimizations
- \`deployments/docker-compose/\` - Alternative configurations
- Multiple \`.env.*\` files

#### New Structure:
- \`docker-compose.yml\` - Unified configuration with all services
- \`.env.unified\` - Master environment template
- \`.env.development.new\` - Development environment
- \`.env.production.new\` - Production environment
- \`.env.testing\` - Testing environment
- \`scripts/docker-environment.sh\` - Environment management script

### 2. Service Integration

#### Integrated Services:
- **Core Application**: blacklist, redis, postgresql
- **Auto-Update**: watchtower (profile: watchtower)
- **Monitoring**: prometheus, grafana (profile: monitoring)

#### Profile Usage:
\`\`\`bash
# Core services only
docker-compose up -d

# With auto-update
docker-compose --profile watchtower up -d

# With monitoring
docker-compose --profile monitoring up -d

# Everything
docker-compose --profile watchtower --profile monitoring up -d
\`\`\`

### 3. Environment Management

#### New Commands:
\`\`\`bash
# Switch environments
./scripts/docker-environment.sh switch development
./scripts/docker-environment.sh switch production

# Start with specific environment
./scripts/docker-environment.sh start development
./scripts/docker-environment.sh start production

# Environment-specific profiles
PROFILE=monitoring ./scripts/docker-environment.sh start production
\`\`\`

### 4. Environment Variables

All environment variables are now centralized in:
- \`.env.unified\` - Master template with all variables
- Environment-specific files override only necessary values

#### Key Environment Variables:
- \`DEPLOYMENT_ENV\` - Environment type (development/production/testing)
- \`EXTERNAL_PORT\` - Host port mapping
- \`PROFILE\` - Docker compose profile to activate
- Performance and resource limit variables
- All service-specific configurations

### 5. Volume Management

#### Configurable Volume Paths:
- \`DATA_PATH\` - Application data
- \`LOGS_PATH\` - Log files
- \`REDIS_DATA_PATH\` - Redis persistence
- \`POSTGRES_DATA_PATH\` - PostgreSQL data

#### Volume Types:
- \`VOLUME_TYPE=none\` with \`VOLUME_OPTS=bind\` for bind mounts
- Change to \`local\` for named volumes

## Migration Benefits

1. **Single Source of Truth**: One docker-compose.yml for all environments
2. **Environment Isolation**: Clear separation of dev/prod/test configurations
3. **Profile-Based Services**: Optional services via Docker Compose profiles
4. **Resource Management**: Configurable CPU and memory limits
5. **Simplified Operations**: Single management script for all operations

## Usage Examples

\`\`\`bash
# Development workflow
./scripts/docker-environment.sh start development
./scripts/docker-environment.sh logs blacklist
./scripts/docker-environment.sh stop

# Production with monitoring
PROFILE=monitoring ./scripts/docker-environment.sh start production

# Testing
./scripts/docker-environment.sh start testing

# Environment switching
./scripts/docker-environment.sh switch development
./scripts/docker-environment.sh env development
\`\`\`

## Backup Information

Original files have been backed up to:
\`$BACKUP_DIR\`

## Next Steps

1. Review and update environment-specific \`.env.*\` files
2. Test the new configuration in development
3. Update deployment documentation
4. Train team on new commands and structure

## Rollback Procedure

If needed, restore from backup:
\`\`\`bash
cp $BACKUP_DIR/docker-compose.yml ./
cp $BACKUP_DIR/.env ./
\`\`\`

EOF

    success "Migration report generated: $report_file"
}

# Help function
show_help() {
    cat << EOF
Docker Compose Migration Script

USAGE:
    $0 [COMMAND]

COMMANDS:
    migrate     Perform the migration (default)
    validate    Validate migration results
    report      Generate migration report only
    help        Show this help

The migration process:
1. Backs up existing files
2. Replaces docker-compose.yml with unified version
3. Sets up environment files
4. Archives old configuration files
5. Validates the new setup
6. Generates a migration report

EOF
}

# Main execution
COMMAND=${1:-migrate}

case $COMMAND in
    migrate)
        migrate_compose_files
        if validate_migration; then
            generate_report
            echo
            success "Migration completed successfully!"
            echo
            log "Next steps:"
            log "1. Review the new configuration: docker-compose config"
            log "2. Test with: ./scripts/docker-environment.sh start development"
            log "3. Read the migration report for details"
        else
            error "Migration completed but validation failed"
            exit 1
        fi
        ;;
    validate)
        validate_migration
        ;;
    report)
        generate_report
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
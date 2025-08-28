# Unified Docker Compose Configuration

**Version**: v1.0.37  
**Date**: 2025-08-22  
**Status**: Production Ready  

## Overview

The Blacklist Management System now uses a unified Docker Compose configuration that consolidates all deployment scenarios into a single `docker-compose.yml` file with environment-specific overrides.

## Architecture

### Single Source of Truth
- **Main File**: `docker-compose.yml` (unified configuration)
- **Environment Files**: `.env.*` files for environment-specific settings
- **Management Script**: `scripts/docker-environment.sh` for unified operations

### Service Organization
```yaml
Core Services (always included):
  - blacklist      # Main application
  - redis          # Cache layer
  - postgresql     # Database

Optional Services (profiles):
  - watchtower     # Auto-update (profile: watchtower)
  - prometheus     # Metrics (profile: monitoring)
  - grafana        # Visualization (profile: monitoring)
```

## Environment Configuration

### Environment Files

| File | Purpose | Port Range |
|------|---------|------------|
| `.env.unified` | Master template with all variables | - |
| `.env.development.new` | Development environment | 2542-2549 |
| `.env.production.new` | Production environment | 32542-32549 |
| `.env.testing` | Testing environment | 12542-12549 |
| `.env` | Active configuration (auto-generated) | Varies |

### Key Environment Variables

#### Core Configuration
```bash
DEPLOYMENT_ENV=production|development|testing
EXTERNAL_PORT=32542           # Host port
INTERNAL_PORT=2542            # Container port
FLASK_ENV=production|development|testing
DEBUG=true|false
```

#### Database Configuration
```bash
POSTGRES_DB=blacklist
POSTGRES_USER=blacklist_user
POSTGRES_PASSWORD=strong_password_here
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

#### Performance Settings
```bash
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
CPU_LIMIT=1.0
MEMORY_LIMIT=1G
REDIS_MAXMEMORY=1gb
```

#### Service Profiles
```bash
PROFILE=core|watchtower|monitoring|all
```

## Usage Guide

### Quick Start

1. **Choose Environment**:
   ```bash
   ./scripts/docker-environment.sh start development
   ./scripts/docker-environment.sh start production
   ./scripts/docker-environment.sh start testing
   ```

2. **With Specific Profile**:
   ```bash
   PROFILE=monitoring ./scripts/docker-environment.sh start production
   ./scripts/docker-environment.sh start production --profile watchtower
   ```

3. **Environment Switching**:
   ```bash
   ./scripts/docker-environment.sh switch development
   ./scripts/docker-environment.sh switch production
   ```

### Management Commands

#### Basic Operations
```bash
# Start services
./scripts/docker-environment.sh start [environment]

# Stop services
./scripts/docker-environment.sh stop

# Restart services
./scripts/docker-environment.sh restart [environment]

# View logs
./scripts/docker-environment.sh logs [service]

# Check status
./scripts/docker-environment.sh status
```

#### Environment Management
```bash
# Switch environments
./scripts/docker-environment.sh switch development
./scripts/docker-environment.sh switch production

# View environment configuration
./scripts/docker-environment.sh env development

# List available profiles
./scripts/docker-environment.sh profiles
```

#### Maintenance Operations
```bash
# Health check
./scripts/docker-environment.sh health

# Update images
./scripts/docker-environment.sh update

# Clean resources
./scripts/docker-environment.sh clean

# Full reset (with data removal)
./scripts/docker-environment.sh reset

# Backup data
./scripts/docker-environment.sh backup

# Restore data
./scripts/docker-environment.sh restore backup/20250822_143022
```

### Direct Docker Compose Usage

#### Basic Commands
```bash
# Start core services
docker-compose up -d

# Start with watchtower
docker-compose --profile watchtower up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start everything
docker-compose --profile watchtower --profile monitoring up -d
```

#### Environment Override
```bash
# Use specific environment file
cp .env.development.new .env
docker-compose up -d

# Or set environment directly
ENVIRONMENT=development docker-compose up -d
```

## Service Profiles

### Core Profile (Default)
Services: `blacklist`, `redis`, `postgresql`
```bash
docker-compose up -d
```

### Watchtower Profile
Adds: `watchtower` service for auto-updates
```bash
docker-compose --profile watchtower up -d
```

### Monitoring Profile
Adds: `prometheus`, `grafana` services
```bash
docker-compose --profile monitoring up -d
```

### All Services
```bash
docker-compose --profile watchtower --profile monitoring up -d
```

## Port Allocation

### Development Environment
- Application: `2542`
- Redis: `6379`
- PostgreSQL: `5432`
- Prometheus: `9091`
- Grafana: `3001`

### Production Environment
- Application: `32542`
- Redis: `32543`
- PostgreSQL: `32544`
- Prometheus: `9090`
- Grafana: `3000`

### Testing Environment
- Application: `12542`
- Redis: `16379`
- PostgreSQL: `15432`
- Prometheus: `19090`
- Grafana: `13000`

## Volume Configuration

### Configurable Paths
Environment variables control volume mount paths:

```bash
DATA_PATH=./data/blacklist           # Application data
LOGS_PATH=./logs                     # Log files
REDIS_DATA_PATH=./data/redis         # Redis persistence
POSTGRES_DATA_PATH=./data/postgresql # PostgreSQL data
PROMETHEUS_DATA_PATH=./data/prometheus
GRAFANA_DATA_PATH=./data/grafana
```

### Volume Types
```bash
# Bind mounts (default)
VOLUME_TYPE=none
VOLUME_OPTS=bind

# Named volumes
VOLUME_TYPE=local
VOLUME_OPTS=
```

## Resource Management

### CPU and Memory Limits
Each service has configurable resource limits:

```bash
# Main application
CPU_LIMIT=1.0
MEMORY_LIMIT=1G
CPU_RESERVATION=0.5
MEMORY_RESERVATION=512M

# PostgreSQL
POSTGRES_CPU_LIMIT=2.0
POSTGRES_MEMORY_LIMIT=2G

# Redis
REDIS_CPU_LIMIT=1.0
REDIS_MEMORY_LIMIT=1.5G
```

### Performance Optimization
Enable performance mode:
```bash
PERFORMANCE_OPTIMIZED=true
PYTHONOPTIMIZE=2
GUNICORN_PRELOAD_APP=true
```

## Migration from Old Setup

### Automated Migration
```bash
./scripts/migrate-compose.sh
```

This will:
1. Backup existing files
2. Replace configurations
3. Set up environment files
4. Validate the setup
5. Generate migration report

### Manual Migration Steps
1. **Backup existing configuration**:
   ```bash
   mkdir -p backup/$(date +%Y%m%d)
   cp docker-compose*.yml backup/$(date +%Y%m%d)/
   cp .env* backup/$(date +%Y%m%d)/
   ```

2. **Replace main file**:
   ```bash
   cp docker-compose.unified.yml docker-compose.yml
   ```

3. **Setup environment**:
   ```bash
   cp .env.unified .env
   # Edit .env for your environment
   ```

4. **Test the setup**:
   ```bash
   docker-compose config
   ./scripts/docker-environment.sh start development
   ```

## Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check which ports are in use
./scripts/docker-environment.sh env development
netstat -tulpn | grep :2542
```

#### Environment Issues
```bash
# Validate environment
./scripts/docker-environment.sh env production
docker-compose config

# Switch environment
./scripts/docker-environment.sh switch development
```

#### Service Health
```bash
# Check service health
./scripts/docker-environment.sh health
./scripts/docker-environment.sh status

# View logs
./scripts/docker-environment.sh logs blacklist
./scripts/docker-environment.sh logs postgresql
```

### Rollback Procedure
If migration fails:
```bash
# Restore from backup
cp backup/YYYYMMDD/docker-compose.yml ./
cp backup/YYYYMMDD/.env ./
docker-compose up -d
```

## Best Practices

### Development
- Use `development` environment
- Enable debug mode
- Disable collection for safety
- Use lower resource limits

### Production
- Use `production` environment
- Enable monitoring profile
- Set strong passwords
- Configure proper resource limits
- Enable watchtower for auto-updates

### Testing
- Use `testing` environment
- Minimal resource allocation
- Isolated port ranges
- Disable external collections

## Integration with Existing Workflow

### Makefile Integration
Update your Makefile to use the new scripts:
```make
start:
	./scripts/docker-environment.sh start production

dev:
	./scripts/docker-environment.sh start development

stop:
	./scripts/docker-environment.sh stop

logs:
	./scripts/docker-environment.sh logs
```

### CI/CD Integration
Use environment variables in your CI/CD:
```yaml
# GitHub Actions example
- name: Deploy to Production
  run: |
    ./scripts/docker-environment.sh start production
    ./scripts/docker-environment.sh health
```

## Support

For issues with the unified configuration:
1. Check the migration report
2. Validate environment: `./scripts/docker-environment.sh env`
3. Check service health: `./scripts/docker-environment.sh health`
4. Review logs: `./scripts/docker-environment.sh logs`
5. Consult the troubleshooting section

## Version History

- **v1.0.37**: Initial unified configuration
  - Consolidated all compose files
  - Added environment management
  - Integrated resource management
  - Added service profiles
  - Created management scripts
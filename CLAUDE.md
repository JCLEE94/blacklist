# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with multi-source data collection, automated processing, and FortiGate External Connector integration. Features dependency injection architecture, containerized deployment with GitHub Actions CI/CD and Watchtower auto-deployment.

**Current Status (2025.06.27)**: The application has been simplified to a single unified Flask app in `main.py` due to decorator conflicts. The complex multi-module architecture is temporarily disabled.

### Key Architecture Principles:
- **Simplified Entry Point**: `main.py` contains the entire application (temporarily)
- **Original Architecture** (currently disabled):
  - Dependency Injection: Central service container (`src/core/container.py`)
  - Multi-layered Entry Points: `main.py` → `src/core/app_compact.py` → fallback chain
  - Plugin-based IP Sources: Extensible source system in `src/core/ip_sources/`
- **Container-First**: Docker/Podman deployment with automated CI/CD
- **Self-Hosted Runner**: GitHub Actions uses self-hosted runner with specific version requirements

### Production Infrastructure:
- **Docker Registry**: `registry.jclee.me`
- **Production Server**: `192.168.50.215` (port 1111 for SSH, port 2541 for app)
- **Production URL**: `https://blacklist.jclee.me`
- **Default Ports**: DEV=8541, PROD=2541
- **Auto-deployment**: Watchtower monitors registry for updates
- **Timezone**: Asia/Seoul (KST)
- **Reverse Proxy**: NGINX/OpenResty handles HTTPS termination

### Data Sources:
- **REGTECH** (Financial Security Institute) - Requires authentication, ~1,200 IPs
- **SECUDIUM** - Standard authentication (SMS OTP not required)
- **Public Threat Intelligence** - Automated collection

## ⚠️ Critical Issues and Solutions

### 1. Flask Endpoint Conflicts (RESOLVED)
**Problem**: Decorators in `src/utils/unified_decorators.py` caused Flask endpoint registration conflicts.
```
AssertionError: View function mapping is overwriting an existing endpoint function
```

**Solution**: Removed all `@api_endpoint` and `@public_endpoint` decorators from route files. The decorators are currently disabled and return functions unchanged.

### 2. GitHub Actions Runner Compatibility
**Problem**: Self-hosted runner requires specific action versions.
```
Can't find 'action.yml', 'action.yaml' or 'Dockerfile'
```

**Solution**: Use these specific versions in workflows:
```yaml
runs-on: self-hosted
- uses: actions/checkout@v3         # NOT v4
- uses: docker/setup-buildx-action@v2  # NOT v3
- uses: docker/build-push-action@v4    # NOT v5
```

### 3. CI/CD Timeout Issues
**Problem**: Deployment verification times out before Watchtower completes deployment.

**Solution**: Extended all timeout values in `.github/workflows/build-deploy.yml`:
```yaml
TEST_TIMEOUT: 600
BUILD_TIMEOUT: 1200
DEPLOY_TIMEOUT: 600
VERIFY_TIMEOUT: 1200
WATCHTOWER_WAIT_TIME: 120
VERIFY_MAX_ATTEMPTS: 120
```

### 4. Production Server Monitoring
**Problem**: CI/CD was checking local Docker instead of production server.

**Solution**: Monitor production URL directly:
```bash
PRODUCTION_URL="https://blacklist.jclee.me/health"
```

## Development Commands

### Application Startup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database (SQLite with auto-migration)
python3 setup_database.py

# Development server (CURRENT: simplified single-file app)
python3 main.py                    # Default port 8541
python3 main.py --port 8080        # Custom port
python3 main.py --debug            # Debug mode

# Production deployment
gunicorn -w 4 -b 0.0.0.0:2541 --timeout 120 main:application
```

### Container Operations
```bash
# Build and deploy to registry
./manual-deploy.sh                 # Build, push to registry, trigger Watchtower

# Local container development
docker-compose -f deployment/docker-compose.yml up -d --build

# Container logs and debugging
docker logs blacklist -f
docker exec -it blacklist /bin/bash

# Force rebuild (no cache)
docker-compose -f deployment/docker-compose.yml build --no-cache
```

### Data Collection Management
```bash
# Collection system status
curl http://localhost:8541/api/collection/status

# Enable/disable collection (clears existing data)
curl -X POST http://localhost:8541/api/collection/enable
curl -X POST http://localhost:8541/api/collection/disable

# Trigger manual collection
curl -X POST http://localhost:8541/api/collection/regtech/trigger
curl -X POST http://localhost:8541/api/collection/secudium/trigger

# Integration testing
python3 scripts/integration_test_comprehensive.py
```

### Testing
```bash
# All tests
pytest

# Specific test categories
pytest -m "not slow and not integration"    # Unit tests only
pytest tests/test_blacklist_unified.py      # Specific module
pytest -v --cov=src                         # With coverage

# Debugging and diagnostics
python3 scripts/debug_regtech_advanced.py     # REGTECH auth analysis
```

## Core Architecture (Currently Simplified)

### Current Simplified Architecture
Due to Flask endpoint conflicts, the application is temporarily running as a single unified Flask app in `main.py`. All complex features are disabled until the decorator issues are resolved.

### Original Architecture (Disabled)

#### Service Container and Dependency Injection
The system was designed to use a central dependency injection container (`src/core/container.py`) that manages service lifecycles:

```python
from src.core.container import get_container

# Service registration happens automatically via BlacklistContainer
container = get_container()
blacklist_manager = container.get('blacklist_manager')
cache_manager = container.get('cache_manager')
```

**Key Services:**
- `blacklist_manager`: Core IP management (`src/core/blacklist_unified.py`)
- `cache_manager`: Redis/memory cache fallback (`src/utils/advanced_cache.py`)
- `collection_manager`: Multi-source data collection (`src/core/collection_manager.py`)
- `regtech_collector`: REGTECH-specific collection with session management
- `secudium_collector`: SECUDIUM-specific collection

#### Application Entry Points and Fallback Chain

The system was designed with multiple entry points with automatic fallback:

1. **Primary**: `main.py` → `src/core/app_compact.py` (full feature set)
2. **Fallback**: `src/core/minimal_app.py` (essential features only)
3. **Legacy**: `src/app.py` or `app.py` (backward compatibility)

**app_compact.py** features:
- Full dependency injection
- Performance optimization (orjson, connection pooling)
- Rate limiting and security headers
- Comprehensive error handling

#### IP Source Plugin System

Extensible architecture in `src/core/ip_sources/`:

```python
# Base class for all IP sources
class BaseIPSource(ABC):
    @abstractmethod
    def collect_ips(self) -> List[BlacklistEntry]: pass

# Built-in sources
- RegtechSource: Financial security data
- SecudiumSource: Threat intelligence
- FileSource: Static file imports
- URLSource: HTTP endpoint collection
```

### Data Collection Architecture

**Collection Manager Pattern** (`src/core/collection_manager.py`):
- Centralized ON/OFF control
- Source-specific triggering
- Data clearing and lifecycle management
- Integration with container services

**REGTECH Collection** (`src/core/regtech_collector.py`):
- Session-based authentication with enhanced retry logic
- Date range parameters (startDate, endDate) for filtered collection
- Sequential collection to maintain session integrity
- Comprehensive error detection and logging

**SECUDIUM Collection** (`src/core/secudium_collector.py`):
- Token-based authentication
- Automatic fallback strategies
- Integration with collection manager

### Caching and Performance

**Advanced Cache System** (`src/utils/advanced_cache.py`):
- Redis primary with memory fallback
- Tag-based invalidation
- TTL-based expiration
- Performance metrics

**Performance Features**:
- orjson for faster JSON processing
- Flask-Compress for response compression
- Connection pooling for database operations
- Rate limiting per endpoint

### CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/build-deploy.yml`):
1. **Parallel Quality Checks**: Lint, security scan, tests
2. **Docker Build**: Multi-stage build with caching to `registry.jclee.me`
3. **Watchtower Deployment**: Auto-detects and deploys new images
4. **Verification**: Health checks, smoke tests, performance monitoring
5. **Automatic Rollback**: On failure, reverts to previous version

**Deployment Flow**:
```
Push to main → GitHub Actions → Build & Push to Registry → Watchtower Auto-Deploy → Verify → Rollback on Failure
```

## API Endpoints Reference

### Core Blacklist Endpoints
- `GET /` - Web dashboard interface
- `GET /health` - System health check with detailed diagnostics
- `GET /api/blacklist/active` - Active IPs in plain text format
- `GET /api/fortigate` - FortiGate External Connector JSON format
- `GET /api/stats` - System statistics and metrics

### Collection Management
- `GET /api/collection/status` - Collection service status and configuration
- `POST /api/collection/enable` - Enable collection (clears existing data)
- `POST /api/collection/disable` - Disable all collection sources
- `POST /api/collection/regtech/trigger` - Manual REGTECH collection trigger
- `POST /api/collection/secudium/trigger` - Manual SECUDIUM collection trigger

### Enhanced V2 Endpoints (Currently Disabled)
- `GET /api/v2/blacklist/enhanced` - Enhanced blacklist with metadata
- `GET /api/v2/analytics/trends` - Advanced analytics and trends
- `GET /api/v2/sources/status` - Multi-source collection detailed status

### Search and Analysis (Currently Disabled)
- `GET /api/search/{ip}` - Single IP lookup with history
- `POST /api/search` - Batch IP search (JSON payload)
- `GET /api/stats/detection-trends` - Detection trends over time

### Docker Monitoring (Currently Disabled)
- `GET /api/docker/containers` - List all Docker containers
- `GET /api/docker/container/{name}/logs` - Get container logs (streaming support)
- `GET /docker-logs` - Web interface for Docker logs monitoring

## Critical Implementation Notes

### Cache Configuration
Cache operations must use specific parameter naming:
```python
# Correct cache usage
cache.set(key, value, ttl=300)  # Use 'ttl=', not 'timeout='

# Decorator usage
@cached(cache, ttl=300, key_prefix="stats")  # Use 'ttl=' and 'key_prefix='
```

### Environment Variables
Required for production deployment:
```bash
# Authentication credentials
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=Sprtmxm1@3
SECUDIUM_USERNAME=nextrade  
SECUDIUM_PASSWORD=Sprtmxm1@3

# Application configuration
PORT=8541               # Application port
SECRET_KEY=your-secret  # Flask secret key
REDIS_URL=redis://localhost:6379/0  # Optional, falls back to memory cache

# Security
JWT_SECRET_KEY=jwt-secret    # JWT token signing
API_SECRET_KEY=api-secret    # API key generation

# Docker Registry (for CI/CD)
DOCKER_USERNAME=your-username
DOCKER_PASSWORD=your-password
REGISTRY_USERNAME=registry-username  # For private registry
REGISTRY_PASSWORD=registry-password
```

### Date Parameters for REGTECH
REGTECH collector requires startDate and endDate parameters:
```python
# In collection calls, dates are automatically set to last 90 days if not provided
collector.collect_from_web(start_date='20250601', end_date='20250620')
```

### Database Management
- SQLite for development/small deployments
- Auto-migration support via `setup_database.py`
- 3-month data retention with automatic cleanup
- Located at `/app/instance/blacklist.db` in containers

## Troubleshooting

### Common Issues and Solutions

**Container Build Issues**:
```bash
# Force clean rebuild
docker-compose -f deployment/docker-compose.yml down
docker-compose -f deployment/docker-compose.yml build --no-cache
docker-compose -f deployment/docker-compose.yml up -d
```

**502 Bad Gateway Error**:
- Usually indicates Flask app not starting properly
- Check decorator conflicts in route files
- Verify all imports are working correctly
- Check Docker logs: `docker logs blacklist -f`

**REGTECH Authentication Failures**:
- Server returns `error=true` in login redirect URL
- Indicates external server authentication policy changes
- Check credentials in docker-compose.yml environment variables
- Run `python3 scripts/debug_regtech_advanced.py` for detailed auth analysis

**SECUDIUM Collection Issues**:
- Standard authentication (no SMS OTP required)
- Check server response for 500 errors indicating server-side issues
- Verify credentials are properly set in container environment

**Cache and API Errors**:
```bash
# Check Redis connectivity
docker logs blacklist-redis -f

# If Redis unavailable, system falls back to in-memory cache
# API errors like "Cache is None" indicate container configuration issues
```

**Database Initialization**:
```bash
# Manual database setup in container
docker exec blacklist python3 setup_database.py

# Check database status
docker exec blacklist python3 -c "
import sqlite3
conn = sqlite3.connect('/app/instance/blacklist.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM blacklist_ip')
print(f'Total IPs: {cursor.fetchone()[0]}')
conn.close()
"
```

**Watchtower Auto-Deployment Issues**:
```bash
# Check Watchtower logs
docker logs watchtower -f

# Manually trigger update check
docker exec watchtower sh -c 'kill -HUP 1'

# Verify Watchtower labels on container
docker inspect blacklist | grep -A 5 "Labels"
```

### Integration Testing
Run comprehensive system tests:
```bash
python3 scripts/integration_test_comprehensive.py
```

Expected results:
- System health: ✅ Should be healthy
- Collection enable: ✅ Should clear existing data
- REGTECH/SECUDIUM: ❌ Expected authentication failures with external servers
- API endpoints: ✅ Should respond correctly
- Performance: ✅ Should be under 500ms average response time

### Log Analysis
```bash
# Application logs
docker logs blacklist -f

# Key log patterns to watch for:
# - "로그인 후 다시 로그인 페이지로 리다이렉트됨" (REGTECH auth issue)
# - "numpy.dtype size changed" (non-blocking compatibility warning)  
# - "Cache is None" (cache initialization issue)
# - "View function mapping is overwriting" (decorator conflict)
```

### Manual Deployment (Fallback)
If CI/CD fails, use manual deployment:
```bash
# Build and push manually
docker build -f deployment/Dockerfile -t registry.jclee.me/blacklist:latest .
docker push registry.jclee.me/blacklist:latest

# On production server
docker pull registry.jclee.me/blacklist:latest
docker-compose -f deployment/docker-compose.yml up -d

# Or use the manual deploy script
./manual-deploy.sh
```

## Quick Fix Guide

### Flask Endpoint Conflict Fix
If you encounter Flask endpoint conflicts:
1. Remove all `@api_endpoint` and `@public_endpoint` decorators from route files
2. Check `src/utils/unified_decorators.py` - decorators should return functions unchanged
3. Restart the application

### CI/CD Failure Fix
If CI/CD is failing:
1. Check GitHub Actions runner compatibility - use v3/v2 versions, not v4/v3
2. Increase timeout values in workflow files
3. Ensure production URL monitoring is correct
4. Check self-hosted runner is properly configured

### 502 Bad Gateway Fix
If production returns 502:
1. Check if container is running: `docker ps | grep blacklist`
2. Check container logs: `docker logs blacklist -f`
3. Verify Flask app is starting without errors
4. Check NGINX/OpenResty reverse proxy configuration
5. Try manual restart: `docker restart blacklist`

## Development Tips

### Working with Simplified Architecture
Until the decorator issues are fully resolved:
1. All changes should be made directly in `main.py`
2. Avoid importing from complex modules that use decorators
3. Test locally before pushing to avoid CI/CD issues
4. Use manual deployment script if CI/CD is problematic

### Restoring Full Architecture
To restore the full architecture:
1. Fix decorator conflicts in `src/utils/unified_decorators.py`
2. Ensure no duplicate endpoint registrations
3. Gradually re-enable imports in `main.py`
4. Test each module independently
5. Use feature flags to enable/disable complex features

### Performance Considerations
- Current simplified app has no caching - performance may be limited
- No rate limiting or advanced features
- Database operations are direct without pooling
- Consider impact on production load

## Future Improvements

### Immediate Priorities
1. **Fix Decorator System**: Resolve Flask endpoint conflicts properly
2. **Restore Full Architecture**: Re-enable dependency injection and plugins
3. **Improve CI/CD**: Make deployment more robust with better error handling
4. **Add Monitoring**: Implement proper APM and logging

### Long-term Goals
1. **Kubernetes Support**: Move from Docker Compose to K8s
2. **Multi-tenancy**: Support multiple organizations
3. **GraphQL API**: Modern API interface
4. **Real-time Updates**: WebSocket support for live data
5. **Machine Learning**: Threat prediction and anomaly detection

## Contact and Support

- **Repository**: https://github.com/JCLEE94/blacklist
- **Production**: https://blacklist.jclee.me
- **Maintainer**: JC Lee
- **Last Updated**: 2025.06.27

---

**Note**: This document reflects the current simplified state of the application. The full architecture documentation is preserved for when the decorator issues are resolved.
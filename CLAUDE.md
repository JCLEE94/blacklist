# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with multi-source data collection, automated processing, and FortiGate External Connector integration. Features dependency injection architecture, containerized deployment with GitHub Actions CI/CD and Watchtower auto-deployment.

**Key Architecture Principles:**
- **Dependency Injection**: Central service container (`src/core/container.py`) manages all service lifecycles
- **Multi-layered Entry Points**: `main.py` → `src/core/app_compact.py` → fallback chain for maximum compatibility
- **Plugin-based IP Sources**: Extensible source system in `src/core/ip_sources/`
- **Container-First**: Docker/Podman deployment with automated CI/CD

**Production Infrastructure:**
- Docker Registry: `registry.jclee.me`
- Production Server: `192.168.50.215` (port 1111 for SSH, port 2541 for app)
- Default Ports: DEV=8541, PROD=2541
- Auto-deployment: Watchtower monitors registry for updates
- Production URL: https://blacklist.jclee.me
- Timezone: Asia/Seoul (KST)

**Data Sources:**
- REGTECH (Financial Security Institute) - Requires authentication, ~1,200 IPs
- SECUDIUM - Standard authentication with POST-based login and Excel download
- Public Threat Intelligence - Automated collection

## Development Commands

### Application Startup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database (SQLite with auto-migration)
python3 init_database.py

# Development server (entry point with fallback chain)
python3 main.py                    # Preferred: app_compact → minimal_app → fallback
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
python3 scripts/debug_regtech_har.py          # HAR-based debugging
```

### Linting and Code Quality
```bash
# Python syntax check
python3 -m py_compile src/**/*.py

# Security scan for hardcoded credentials
grep -r -E "(password|secret|key|token)\s*=\s*['\"][^'\"]*['\"]" --include="*.py" src/

# Format code
black src/

# Run flake8 (if configured)
flake8 src/
```

## Core Architecture

### Service Container and Dependency Injection

The system uses a central dependency injection container (`src/core/container.py`) that manages service lifecycles:

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
- `secudium_collector`: SECUDIUM-specific collection with Excel download
- `unified_service`: Central service orchestrator (`src/core/unified_service.py`)

### Application Entry Points

The system provides streamlined entry point with error handling:

1. **Primary**: `main.py` → `src/core/app_compact.py` (full feature set)
2. **Fallback**: `src/core/minimal_app.py` (if compact fails)
3. **Error Handling**: Comprehensive logging and graceful shutdown on failure

**app_compact.py** features:
- Full dependency injection
- Performance optimization (orjson, connection pooling)
- Rate limiting and security headers
- Comprehensive error handling

### IP Source Plugin System

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
- Proper date parsing from Excel source data (not current time)
- Comprehensive error detection and logging
- HAR-based collector available (`src/core/har_based_regtech_collector.py`)

**SECUDIUM Collection** (`src/core/secudium_collector.py`):
- POST-based login to `/isap-api/loginProcess`
- Force login with `is_expire='Y'` to handle concurrent sessions
- Excel file download from bulletin board
- Token-based authentication with Bearer token
- Automatic IP extraction from Excel files
- Original detection date preservation from source data
- HAR-based collector available (`src/core/har_based_secudium_collector.py`)

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

**Self-hosted Runner Compatibility**:
```yaml
runs-on: self-hosted
# Must use these specific versions:
- uses: actions/checkout@v3         # NOT v4
- uses: docker/setup-buildx-action@v2  # NOT v3
- uses: docker/build-push-action@v4    # NOT v5
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

### Enhanced V2 Endpoints
- `GET /api/v2/blacklist/enhanced` - Enhanced blacklist with metadata
- `GET /api/v2/analytics/trends` - Advanced analytics and trends
- `GET /api/v2/sources/status` - Multi-source collection detailed status

### Search and Analysis
- `GET /api/search/{ip}` - Single IP lookup with history
- `POST /api/search` - Batch IP search (JSON payload)
- `GET /api/stats/detection-trends` - Detection trends over time

### Docker Monitoring
- `GET /api/docker/containers` - List all Docker containers
- `GET /api/docker/container/{name}/logs` - Get container logs (streaming support)
- `GET /docker-logs` - Web interface for Docker logs monitoring

### Test Endpoint
- `GET /test` - Simple test endpoint that returns "Test response from blacklist app"

## Critical Implementation Notes

### Cache Configuration
Cache operations must use specific parameter naming:
```python
# Correct cache usage
cache.set(key, value, ttl=300)  # Use 'ttl=', not 'timeout='

# Decorator usage
@cached(cache, ttl=300, key_prefix="stats")  # Use 'ttl=' and 'key_prefix='
```

### Content-Type Handling
Support both JSON and form data in POST endpoints:
```python
# Handle both JSON and form data
if request.is_json:
    data = request.get_json() or {}
else:
    data = request.form.to_dict() or {}
```

### Date Parsing in Collectors
Preserve original detection dates from source data:
```python
# Correct - use source data dates
if isinstance(detection_date_raw, pd.Timestamp):
    detection_date = detection_date_raw.strftime('%Y-%m-%d')
# NOT: detection_date = datetime.now().strftime('%Y-%m-%d')
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
- Auto-migration support via `init_database.py`
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

**REGTECH Authentication Failures**:
- Server returns `error=true` in login redirect URL
- Indicates external server authentication policy changes
- Check credentials in docker-compose.yml environment variables
- Run `python3 scripts/debug_regtech_advanced.py` for detailed auth analysis
- Try HAR-based collector: `python3 scripts/debug_regtech_har.py`

**SECUDIUM Collection Issues**:
- Uses POST login to `/isap-api/loginProcess` (not GET)
- Requires `is_expire='Y'` to handle concurrent sessions
- Downloads Excel files from bulletin board, not direct API
- Check server response for authentication errors
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
docker exec blacklist python3 init_database.py

# Check database status
docker exec blacklist python3 -c "
import sqlite3
conn = sqlite3.connect('/app/instance/blacklist.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM blacklist_ip')
print(f'Total IPs: {cursor.fetchone()[0]}')
conn.close()
"

# Force recreate database
python3 init_database.py --force
```

**Watchtower Auto-Deployment Issues**:
```bash
# Check Watchtower logs
docker logs watchtower -f

# Manually trigger update check
docker exec watchtower sh -c 'kill -HUP 1'

# Verify Watchtower labels on container
docker inspect blacklist | grep -A 5 "Labels"

# Watchtower webhook URL
https://watchtower.jclee.me/v1/update
# Authorization: Bearer MySuperSecretToken12345
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
# - "동일 ID로 로그인 한 사용자가 있습니다" (SECUDIUM concurrent session)
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

### 502 Bad Gateway Fix
If production returns 502:
1. Check if `main.py` exists in repository root
2. Verify container is running: `docker ps | grep blacklist`
3. Check container logs: `docker logs blacklist -f`
4. Check if app can find main.py: `docker exec blacklist ls -la /app/main.py`
5. If main.py is missing, restore from git and push to trigger deployment

### Memory Issues
If experiencing high memory usage:
1. Check system memory: `free -h`
2. Check Docker stats: `docker stats --no-stream`
3. Restart container: `docker restart blacklist`
4. Consider killing unused processes consuming memory

## Collection Logging

Enhanced collection logging system (`src/core/unified_service.py`):
- Detailed daily collection statistics in logs
- Collection start/complete events with IP counts
- Memory-based log storage with rotation
- Source-specific action tracking

```python
def add_collection_log(self, source: str, action: str, details: Dict[str, Any] = None):
    """수집 로그 추가 - 일일 상세 통계 포함"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'source': source,
        'action': action,
        'details': details or {}
    }
```

## Recent Implementations (2025.06.28)

### HAR-Based Collectors
- Added HAR-based REGTECH collector for enhanced compatibility
- Added HAR-based SECUDIUM collector for robust authentication
- Comprehensive logging for debugging authentication issues

### V2 API Endpoints
- Enhanced blacklist API with metadata
- Advanced analytics and trends
- Multi-source status monitoring
- Docker container management

### Collection Date Fix
- Fixed collectors to use source dates instead of current time
- Proper Excel timestamp parsing in REGTECH and SECUDIUM
- Original detection date preservation throughout pipeline

### Collection Logging Enhancement
- Daily collection statistics displayed in logs
- Detailed collector action tracking
- Memory-based log storage with automatic rotation

### Technology Stack

- **Backend**: Flask 2.3.3 + Gunicorn
- **Database**: SQLite with auto-migration support
- **Cache**: Redis (memory fallback for development)
- **Container**: Docker/Podman with Watchtower auto-deployment
- **CI/CD**: GitHub Actions + Self-hosted Runner
- **Monitoring**: Built-in performance metrics and health checks
- **JSON**: orjson for high-performance serialization
- **Data Processing**: pandas + openpyxl for Excel parsing

## Quick Reference

```bash
# Development
python3 main.py --debug

# Testing
pytest -v

# Deployment
./manual-deploy.sh

# Health Check
curl http://localhost:8541/health

# Collection Status
curl http://localhost:8541/api/collection/status

# Manual Collection
curl -X POST http://localhost:8541/api/collection/regtech/trigger
curl -X POST http://localhost:8541/api/collection/secudium/trigger

# Force collection with date range (REGTECH)
curl -X POST http://localhost:8541/api/collection/regtech/trigger \
  -H "Content-Type: application/json" \
  -d '{"start_date": "20250601", "end_date": "20250620"}'
```
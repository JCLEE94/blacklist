# Blacklist Management System - AI Agent Development Rules

## Project Overview

**ENTERPRISE THREAT INTELLIGENCE PLATFORM** - Flask-based blacklist management system with GitOps deployment, FortiGate integration, and dual-source data collection (REGTECH/SECUDIUM).

### Core Technology Stack
- **Backend**: Flask 2.3.3 + Python 3.9+ + Gunicorn
- **Database**: PostgreSQL 15 (primary) + Redis 7 (cache)
- **Security**: JWT + API Key dual authentication
- **Deployment**: Docker Compose + ArgoCD GitOps
- **Testing**: pytest (95% coverage requirement)
- **Registry**: registry.jclee.me/blacklist:latest

## Architecture Rules

### File Size Limitation
- **ENFORCE 500-LINE MAXIMUM** per Python file
- **SPLIT IMMEDIATELY** when approaching 500 lines
- **USE MIXINS** for service composition instead of large classes
- **USE BLUEPRINTS** for route organization

### Modular Structure Pattern
- **ALWAYS USE MIXINS** for Flask app composition: `AppConfigurationMixin`, `MiddlewareMixin`, `BlueprintRegistrationMixin`, `ErrorHandlerMixin`
- **FOLLOW MIXIN HIERARCHY** in `src/core/app_compact.py`
- **NEVER CREATE MONOLITHIC FILES** - break into logical modules

### Entry Point Chain
- **PRIMARY**: `main.py` → `src/core/app_compact.py`  
- **FALLBACK**: `src/core/minimal_app.py` → legacy routes
- **NEVER BYPASS** the established entry point chain

## Service Access Patterns

### Dependency Injection (REQUIRED)
```python
# CORRECT - Container pattern
from src.core.container import get_container
container = get_container()
service = container.get('unified_service')

# ALTERNATIVE - Factory pattern  
from src.core.services.unified_service_factory import get_unified_service
service = get_unified_service()

# NEVER - Direct instantiation
# service = UnifiedService()  # PROHIBITED
```

### Available Container Services
- `unified_service` - Main orchestrator
- `blacklist_manager` - IP management
- `cache_manager` - Redis + memory fallback
- `collection_manager` - Data collection
- `auth_manager` - Authentication

## Database Interaction Rules

### Cache Usage (CRITICAL)
```python
# CORRECT - Use 'ttl=' parameter
cache.set(key, value, ttl=300)
@cached(cache, ttl=300, key_prefix="stats")

# PROHIBITED - Using 'timeout='
# cache.set(key, value, timeout=300)  # WRONG PARAMETER NAME
```

### Connection Patterns
- **PostgreSQL**: Use connection pooling via container
- **Redis**: Auto-fallback to memory cache if Redis unavailable
- **NEVER ASSUME** database availability - always implement fallbacks

### Date Handling
```python
# CORRECT - Use source dates
if isinstance(detection_date_raw, pd.Timestamp):
    detection_date = detection_date_raw.strftime('%Y-%m-%d')

# PROHIBITED - Using current time for historical data
# detection_date = datetime.now().strftime('%Y-%m-%d')  # WRONG
```

## API Development Rules

### Request Data Handling
```python
# REQUIRED - Support both JSON and form data
if request.is_json:
    data = request.get_json() or {}
else:
    data = request.form.to_dict() or {}
```

### Performance Requirements
- **API Response Time**: <50ms target, <200ms acceptable
- **Use orjson**: Instead of standard json for 3x performance
- **Enable Compression**: Flask-Compress for bandwidth optimization
- **Cache Aggressively**: TTL-based caching for analytics endpoints

### Error Handling Pattern
```python
# REQUIRED - Never crash, always fallback
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return fallback_value
```

## Security Requirements

### Authentication System
- **DUAL AUTHENTICATION**: JWT + API Key both required
- **NO HARDCODED CREDENTIALS**: Always use environment variables
- **CREDENTIAL ROTATION**: Support automatic key rotation
- **AUDIT TRAILS**: Log all authentication attempts

### Environment Variables (CRITICAL)
```bash
# REQUIRED for collection functionality
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password  
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Security system
JWT_SECRET_KEY=change-in-production
API_KEY_ENABLED=true
DEFAULT_API_KEY=blk_generated-key-here
```

## Data Collection Rules

### External Source Integration
- **REGTECH**: Session-based auth, Excel parsing, HAR fallback
- **SECUDIUM**: POST login `/isap-api/loginProcess`, Bearer tokens
- **RETRY LOGIC**: Implement exponential backoff for failed requests
- **DATE VALIDATION**: Always validate date ranges from external sources

### Collection Safety
```python
# PRODUCTION SAFETY - Check environment flags
FORCE_DISABLE_COLLECTION = os.getenv('FORCE_DISABLE_COLLECTION', 'false').lower() == 'true'
COLLECTION_ENABLED = os.getenv('COLLECTION_ENABLED', 'false').lower() == 'true'
```

## Testing Requirements

### Coverage Standards
- **MINIMUM 95% COVERAGE** - Non-negotiable
- **REAL DATA TESTING** - Never use fake/mock data for core functionality
- **NO MAGICMOCK** - Prohibited for core business logic testing

### Test Markers (pytest.ini)
```python
# Use specific markers
pytest -m unit -v          # Unit tests only
pytest -m integration -v   # Integration tests  
pytest -m api -v           # API endpoint tests
pytest -m collection -v    # Collection system tests
pytest -m regtech -v       # REGTECH-specific tests
pytest -m secudium -v      # SECUDIUM-specific tests
```

### Test Structure Requirements
```python
# REQUIRED - Track ALL validation failures
all_validation_failures = []
total_tests = 0

# PROHIBITED - Unconditional success messages
# print("✅ All tests passed")  # NEVER use without actual validation

# REQUIRED - Conditional success based on results
if all_validation_failures:
    print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed")
    sys.exit(1)
else:
    print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
    sys.exit(0)
```

## Docker & Deployment Rules

### Port Configuration
- **Docker Environment**: Port 32542 (docker-compose.yml)
- **Local Development**: Port 2542 (direct Python execution)
- **NEVER HARDCODE PORTS** - Use environment variables

### Docker Compose Integration
```yaml
# PRODUCTION DEFAULTS (docker-compose.yml)
FORCE_DISABLE_COLLECTION=false    # Collection enabled
COLLECTION_ENABLED=true           # Active collection
RESTART_PROTECTION=false          # Docker: protection disabled
```

### Environment-Specific Settings
- **Local .env.example**: Collection DISABLED (safety)
- **Docker compose**: Collection ENABLED (production)
- **ALWAYS VERIFY** environment-specific configurations

## GitOps & CI/CD Rules

### Registry Integration
- **PRIMARY REGISTRY**: `registry.jclee.me/blacklist:latest`
- **GITHUB CONTAINER REGISTRY**: Integrated with GitHub Actions
- **SELF-HOSTED RUNNERS**: Performance-optimized CI/CD

### Deployment Commands
```bash
# REQUIRED deployment verification
make deploy                    # Full GitOps workflow
make docker-build             # Build verification
make k8s-deploy               # Kubernetes deployment
make argocd-sync              # ArgoCD synchronization
```

### ArgoCD Integration
- **AUTO-SYNC ENABLED**: Monitors Git repository
- **HEALTH CHECKS**: K8s-compatible endpoints required
- **ROLLBACK CAPABILITY**: Blue-green deployment support

## Monitoring & Observability

### Prometheus Metrics
- **55 METRICS TOTAL**: System and business metrics
- **23 ALERT RULES**: Critical system monitoring
- **CUSTOM METRICS**: Collection performance, API response times

### Health Check Endpoints
```python
# REQUIRED endpoints
GET /health, /healthz, /ready    # K8s-compatible
GET /api/health                  # Detailed service status
GET /metrics                     # Prometheus metrics
```

### Logging Requirements
- **USE LOGURU**: `from loguru import logger`
- **STRUCTURED LOGGING**: JSON format for production
- **LOG ROTATION**: 10MB file rotation

## Performance Optimization

### Response Time Targets
- **Excellent**: <50ms
- **Good**: <200ms  
- **Acceptable**: <1000ms
- **Poor**: >5000ms (requires immediate optimization)

### Optimization Techniques
- **orjson**: 3x faster JSON processing
- **Connection Pooling**: Database optimization
- **Redis Caching**: TTL-based with memory fallback
- **Compression**: Flask-Compress for bandwidth

## Prohibited Actions

### NEVER DO
- **Create files >500 lines**
- **Use hardcoded credentials**
- **Mock core business logic in tests**
- **Bypass container/factory patterns**
- **Use asyncio.run() inside functions**
- **Ignore cache parameter names (use ttl= not timeout=)**
- **Create monolithic route files**
- **Skip fallback implementations**
- **Use unconditional test success messages**

### ALWAYS DO
- **Use dependency injection**
- **Implement error fallbacks**
- **Test with real data**  
- **Follow 500-line file limit**
- **Use environment variables**
- **Maintain 95% test coverage**
- **Structure validation outputs**
- **Verify actual vs expected results**

## Multi-File Coordination

### Simultaneous Updates Required
1. **Database Schema Changes**: 
   - `src/core/database_schema.py` + `src/core/database/table_definitions.py`
   - Migration scripts in `scripts/database/migration/`

2. **Route Additions**:
   - Blueprint file + `src/core/app/blueprints.py` registration
   - Corresponding test file in `tests/`

3. **Service Changes**:
   - Service implementation + container registration
   - Factory pattern update if applicable

4. **Docker Configuration**:
   - `docker-compose.yml` + `.env` updates
   - `Dockerfile` modifications require build verification

### Configuration Synchronization
- **Environment Files**: `.env.example` (safe defaults) + docker-compose.yml (production)
- **Test Configuration**: `pytest.ini` + `conftest.py` + test-specific fixtures
- **Security Settings**: `config/security.json` + environment variables

## Decision Making Priorities

### Priority Order
1. **Security** - Authentication, authorization, credential protection
2. **Stability** - Error handling, fallbacks, graceful degradation
3. **Performance** - Response times, resource optimization
4. **Maintainability** - Modular design, test coverage
5. **Features** - New functionality implementation

### Conflict Resolution
- **Security vs Performance**: Choose security
- **Stability vs Features**: Choose stability  
- **Test Coverage vs Speed**: Maintain 95% coverage
- **Modularity vs Simplicity**: Enforce 500-line limit
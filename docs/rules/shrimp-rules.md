# Blacklist Management System - AI Agent Development Guidelines

## Project Overview

**Technology Stack**: Python 3.9+ Flask 2.3.3, Redis 7, SQLite/PostgreSQL, Docker/Kubernetes, ArgoCD GitOps
**Architecture**: Monolithic Flask with MSA components using mixin pattern and dependency injection
**Port Configuration**: Docker 32542 (external) → 2542 (internal), Local Development 2542
**Current Version**: v1.0.37 with 95% test coverage, GitOps maturity 9.0/10

## Critical File Size Rule

**ABSOLUTE REQUIREMENT**: Maximum 500 lines per Python file
- **When file exceeds 500 lines**: Split into logical modules using mixins or separate route files
- **Check before committing**: Use `find src/ -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print}'`
- **Enforcement**: This is strictly enforced in CI/CD pipeline

## Architecture Patterns

### Flask App Composition (MANDATORY PATTERN)
- **Main App Factory**: `src/core/main.py` uses mixin composition
- **Required Mixins**: AppConfigurationMixin, MiddlewareMixin, BlueprintRegistrationMixin, ErrorHandlerMixin
- **Entry Point Chain**: `main.py` → `main.py` → `minimal_app.py` (fallback)
- **Container Pattern**: Always use `get_container()` for dependency injection

### Route Organization (CRITICAL COORDINATION)
```
src/core/routes/
├── api_routes.py           # Core API endpoints
├── collection_*_routes.py  # Collection system routes  
├── unified_control_*.py    # Control panel routes
├── web_routes.py          # Dashboard/UI routes
└── health_routes.py       # Health checks
```

**MULTI-FILE RULE**: When adding ANY new route:
1. Create route file in `src/core/routes/`
2. **MUST** register blueprint in `src/core/app/blueprints.py`
3. **MUST** add tests in `tests/unit/test_*_routes.py`
4. **MUST** update API documentation if public endpoint

## Dependency Injection Rules

### Service Access Pattern (REQUIRED)
```python
# Via factory (preferred)
from src.core.services.unified_service_factory import get_unified_service
service = get_unified_service()

# Via container (dependency injection)
from src.core.container import get_container
container = get_container()
service = container.get('unified_service')
```

**PROHIBITED**: Direct service instantiation outside container

## Logging Requirements

### Structured Logging (MANDATORY)
```python
# REQUIRED import
from src.utils.structured_logging import get_logger
logger = get_logger(__name__)

# PROHIBITED
import logging  # Never use basic logging
```

**ENFORCEMENT**: All modules must use structured logging with proper context

## Environment Configuration Rules

### Port Management (CRITICAL)
- **Docker Environment**: Port 32542 (external) → 2542 (internal)
- **Local Development**: Port 2542 direct
- **Health Checks**: Always use internal port 2542 in container health checks

### Multi-File Environment Coordination (REQUIRED)
**When modifying environment variables**:
1. Update `.env` file
2. **MUST** update `docker-compose.yml` environment section
3. **MUST** update `config/` files if referenced
4. **MUST** test both Docker and local development modes

### Security Configuration (CRITICAL)
```bash
# Docker (Production) - Collection ENABLED
COLLECTION_ENABLED=true
FORCE_DISABLE_COLLECTION=false

# Local (.env.example) - Collection DISABLED (safety)
COLLECTION_ENABLED=false
FORCE_DISABLE_COLLECTION=true
```

## Database Coordination Rules

### Schema Changes (MULTI-FILE REQUIREMENT)
**When modifying database schema**:
1. Update `src/core/database/table_definitions.py`
2. **MUST** create migration in `src/core/database/migration_service.py`
3. **MUST** update models in `src/core/models.py` or relevant model files
4. **MUST** update test fixtures in `tests/fixtures/`
5. **MUST** run `python3 commands/utils/init_database.py --force` to test

### Database Access Pattern (REQUIRED)
```python
# Via unified service (preferred)
service = get_unified_service()
data = service.get_blacklist_data()

# Via container
container = get_container()
db_manager = container.get('blacklist_manager')
```

## Collection System Rules

### Collector Development (MULTI-FILE COORDINATION)
**When adding/modifying collectors**:
1. Update collector in `src/core/collectors/`
2. **MUST** register in `src/core/collectors/unified_collector.py`
3. **MUST** add routes in `src/core/routes/collection_*_routes.py`
4. **MUST** update configuration in `config/collection_config.json`
5. **MUST** add tests with marker: `@pytest.mark.collection`

### Authentication Pattern (REQUIRED)
```python
# Session-based with retry (REGTECH pattern)
# POST login with force expire (SECUDIUM pattern)
# Bearer token for API calls
```

## Testing Requirements

### Test Markers (MANDATORY)
```python
@pytest.mark.unit           # Unit tests
@pytest.mark.integration    # Integration tests  
@pytest.mark.api            # API tests
@pytest.mark.collection     # Collection system
@pytest.mark.regtech        # REGTECH-specific
@pytest.mark.secudium       # SECUDIUM-specific
@pytest.mark.slow           # Slow tests (skip in CI)
```

### Test Coverage (ENFORCED)
- **Minimum**: 95% coverage required
- **Command**: `pytest --cov=src --cov-report=html`
- **Failure**: CI fails if coverage drops below 95%

### Test File Coordination (REQUIRED)
```
tests/
├── unit/test_*_routes.py      # Route tests
├── integration/test_*_integration.py  # Integration tests
├── fixtures/                  # Shared test data
└── conftest.py               # Test configuration
```

## Cache Usage Rules

### Redis Cache Pattern (CRITICAL)
```python
# CORRECT - use 'ttl=' parameter
cache.set(key, value, ttl=300)
@cached(cache, ttl=300, key_prefix="stats")

# WRONG - 'timeout=' parameter not supported
cache.set(key, value, timeout=300)  # PROHIBITED
```

### Fallback Strategy (REQUIRED)
- **Primary**: Redis cache
- **Automatic Fallback**: Memory cache when Redis unavailable
- **Memory Limit**: 256MB maximum

## Request Handling Patterns

### Data Processing (MANDATORY)
```python
# Support both JSON and form data
if request.is_json:
    data = request.get_json() or {}
else:
    data = request.form.to_dict() or {}
```

### Date Handling (CRITICAL)
```python
# Use source dates, not current time
if isinstance(detection_date_raw, pd.Timestamp):
    detection_date = detection_date_raw.strftime('%Y-%m-%d')

# PROHIBITED - never use current time for source data
# datetime.now().strftime('%Y-%m-%d')  # WRONG
```

## Docker and Deployment Rules

### Registry Configuration (REQUIRED)
- **Primary Registry**: `registry.jclee.me/jclee94/blacklist:latest`
- **Build Command**: `make docker-build && make docker-push`
- **Update Command**: `docker-compose pull && docker-compose up -d`

### Resource Limits (ENFORCED)
```yaml
# docker-compose.yml limits
limits:
  cpus: '0.5'
  memory: 512M
reservations:
  cpus: '0.05'  
  memory: 128M
```

## GitOps Coordination Rules

### CI/CD File Coordination (MULTI-FILE REQUIREMENT)
**When modifying deployment**:
1. Update `docker-compose.yml`
2. **MUST** update `k8s/manifests/` if using Kubernetes
3. **MUST** update `.github/workflows/` if changing CI
4. **MUST** test with `scripts/auto-deploy-test.sh`

### Version Management (REQUIRED)
- **Version File**: `VERSION` in root directory
- **Tag Format**: `v1.0.x` semantic versioning
- **Release Notes**: Update `docs/CHANGELOG.md`

## Security Implementation Rules

### Authentication System (DUAL REQUIREMENT)
```python
# JWT + API Key dual authentication
# JWT for web sessions
# API keys for service-to-service
```

### Credential Management (CRITICAL)
- **Storage**: Fernet encrypted in `instance/credentials.enc`
- **Rotation**: Automatic key rotation enabled
- **Access**: Via `src/core/security/credential_manager.py` only

## Error Handling Patterns

### Never-Crash Rule (MANDATORY)
```python
# Always provide fallback
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return fallback_value  # Never crash
```

### Structured Error Responses (REQUIRED)
```python
# API error format
{
    "error": "error_code",
    "message": "Human readable message", 
    "details": {...}
}
```

## Performance Requirements

### Response Time Targets (ENFORCED)
- **Excellent**: < 5ms
- **Good**: < 50ms  
- **Acceptable**: < 200ms
- **Poor**: > 1000ms (requires optimization)

### Optimization Patterns (REQUIRED)
- **JSON Processing**: Use `orjson` (3x faster than standard json)
- **Compression**: Flask-Compress for all responses
- **Connection Pooling**: Database connection pooling enabled

## Code Quality Rules

### Formatting (AUTOMATED)
- **Black**: Line length 88, Python 3.9+ target
- **isort**: Profile "black", trailing commas
- **Command**: `make lint` runs all checks

### Security Scanning (ENFORCED)
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checks
- **Trivy**: Container image scanning in CI

## Prohibited Actions

### NEVER Do These
- **Mock core functionality** in tests (use real implementations)
- **Use `asyncio.run()`** inside functions (only in main blocks)
- **Import conditionally** for required packages in pyproject.toml
- **Exceed 500 lines** per Python file
- **Use basic `logging`** module (use structured_logging)
- **Hardcode credentials** in source code
- **Skip blueprint registration** when adding routes
- **Deploy without testing** both Docker and local modes

### AI Decision Priority (WHEN UNCERTAIN)
1. **Check existing patterns** in similar files
2. **Follow mixin composition** for complex features  
3. **Use dependency injection** via container
4. **Prefer modular routes** over monolithic files
5. **Test both environments** (Docker + local)
6. **Maintain 95% coverage** minimum

## Emergency Procedures

### Rollback Strategy (CRITICAL)
```bash
# Immediate rollback
docker-compose down
git checkout HEAD~1
docker-compose pull && docker-compose up -d
```

### Database Recovery (REQUIRED)
```bash
# Force database reset
python3 commands/utils/init_database.py --force
# Restore from backup if available
```

This document guides AI agents to maintain project consistency, avoid breaking changes, and follow established patterns. All rules are based on actual project architecture and requirements.
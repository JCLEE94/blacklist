# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with Docker Compose deployment, multi-source data collection, and FortiGate External Connector integration. Uses Watchtower for automated deployments. Default security mode blocks all external authentication to prevent server lockouts.

## Development Commands

### Quick Start
```bash
# Environment setup
make init                          # Initialize environment (dependencies, DB, .env)
cp .env.example .env && nano .env  # Configure credentials

# Run services (Docker Compose)
make start                         # Start all services
make status                        # Check status
make logs                          # View logs
make stop                          # Stop services

# Local development (without Docker)
python3 main.py                    # Dev server (port 8541)
python3 main.py --debug           # Debug mode with verbose logging
make dev                           # Auto-reload development mode
```

### Testing
```bash
# Unit tests
pytest -v                          # All tests
pytest -k "test_name" -v          # Specific test by name
pytest tests/test_apis.py::test_regtech_apis -v  # Single test function
pytest -m "not slow" -v           # Skip slow tests
pytest --cov=src --cov-report=html  # Coverage report

# Test markers (from pytest.ini)
pytest -m unit -v                  # Unit tests only
pytest -m integration -v          # Integration tests
pytest -m api -v                   # API tests
pytest -m collection -v           # Collection system tests
pytest -m regtech -v              # REGTECH-specific
pytest -m secudium -v             # SECUDIUM-specific

# Debug failing tests
pytest --pdb tests/failing_test.py
pytest -vvs tests/                # Verbose with stdout
```

### Deployment
```bash
# Docker Compose (single file at root)
docker-compose up -d               # Start services
docker-compose down                # Stop services
docker-compose logs -f blacklist   # Follow logs
docker-compose pull && docker-compose up -d  # Update and restart

# Using helper script
./start.sh start                   # Start services
./start.sh stop                    # Stop services
./start.sh restart                 # Restart services
./start.sh logs                    # View logs
./start.sh status                  # Check status
./start.sh update                  # Pull latest images
./start.sh clean                   # Clean up resources
```

### Code Quality
```bash
# Formatting
black src/ tests/                  # Auto-format code
isort src/ tests/                  # Sort imports

# Linting
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
bandit -r src/ -ll                 # Security analysis
safety check                       # Dependency vulnerabilities

# File size check (STRICT: max 500 lines)
find src/ -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print}'

# Makefile shortcuts
make lint                          # All linters
make security                      # Security checks
```

## Architecture

### Entry Points & Fallback Chain
```
main.py 
  └─> src/core/app_compact.py (primary)
      └─> src/core/minimal_app.py (fallback)
          └─> legacy routes (ultimate fallback)
```

### Modular Structure (500-line rule enforced)

**Routes** (`src/core/routes/`):
- `api_routes.py` - Core API endpoints (/health, /api/blacklist/*, /api/fortigate)
- `web_routes.py` - Web dashboard and UI
- `collection_status_routes.py` - Collection monitoring
- `collection_trigger_routes.py` - Manual collection triggers
- `collection_logs_routes.py` - Collection history
- `admin_routes.py` - Administrative functions

**Services** (`src/core/services/`):
- `unified_service_core.py` - Core service lifecycle
- `collection_service.py` - Collection mixin
- `statistics_service.py` - Analytics mixin
- `unified_service_factory.py` - Singleton factory

### Dependency Injection
```python
from src.core.container import get_container
container = get_container()

# Available services:
service = container.get('unified_service')      # Main orchestrator
blacklist_mgr = container.get('blacklist_manager')
cache_mgr = container.get('cache_manager')      # Redis + memory fallback
collection_mgr = container.get('collection_manager')
auth_mgr = container.get('auth_manager')
```

### Docker Services
```yaml
# docker-compose.yml structure:
blacklist:        # Main app (port 2541)
  - Flask application
  - Gunicorn in production
  - Health checks enabled
  
redis:            # Cache (port 6379)
  - Session storage
  - Response caching
  - 256MB memory limit
```

## API Endpoints

### Health & Status
- `GET /health`, `/healthz`, `/ready` - K8s-compatible health check
- `GET /api/health` - Detailed service status

### Blacklist Operations
- `GET /api/blacklist/active` - Active IPs (text format)
- `GET /api/fortigate` - FortiGate External Connector format
- `GET /api/v2/blacklist/enhanced` - IPs with full metadata

### Collection Control
- `GET /api/collection/status` - Current collection status
- `POST /api/collection/enable` - Enable collection (clears data)
- `POST /api/collection/disable` - Disable collection
- `POST /api/collection/regtech/trigger` - Manual REGTECH collection
- `POST /api/collection/secudium/trigger` - Manual SECUDIUM collection

### Analytics
- `GET /api/v2/analytics/trends` - Trend analysis
- `GET /api/v2/sources/status` - Source-specific status

## Critical Implementation Patterns

### Cache Usage
```python
# MUST use 'ttl=' not 'timeout='
cache.set(key, value, ttl=300)
@cached(cache, ttl=300, key_prefix="stats")
```

### Request Data Handling
```python
# Support both JSON and form data
if request.is_json:
    data = request.get_json() or {}
else:
    data = request.form.to_dict() or {}
```

### Date Processing
```python
# Use source dates, not current time
if isinstance(detection_date_raw, pd.Timestamp):
    detection_date = detection_date_raw.strftime('%Y-%m-%d')
# WRONG: datetime.now().strftime('%Y-%m-%d')
```

### Service Access Pattern
```python
# Via factory (singleton)
from src.core.services.unified_service_factory import get_unified_service
service = get_unified_service()

# Via container (dependency injection)
from src.core.container import get_container
container = get_container()
service = container.get('unified_service')
```

## Data Collectors

### REGTECH
- Session-based authentication with retry
- Excel file parsing for IP extraction
- Date range support (`start_date`, `end_date`)
- HAR-based fallback mechanism

### SECUDIUM  
- POST login to `/isap-api/loginProcess`
- Force login with `is_expire='Y'`
- Excel download from bulletin board
- Bearer token authentication

## CI/CD Pipeline (Watchtower-based)

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yaml
- Trigger: Push to main
- Build: Docker image with version tag
- Push: registry.jclee.me/jclee94/blacklist:latest
- Watchtower: Auto-detects and deploys (60s interval)
```

### Deployment Flow
```
Code Push → GitHub Actions → Docker Build → Registry Push → Watchtower Pull → Auto Deploy
```

### Manual Deployment (if Watchtower fails)
```bash
docker-compose pull
docker-compose up -d
```

## Environment Configuration

### Essential Variables (.env)
```bash
# Application
PORT=2541
FLASK_ENV=production
DATABASE_URL=sqlite:////app/instance/blacklist.db
REDIS_URL=redis://redis:6379/0

# Security (defaults prevent lockouts)
FORCE_DISABLE_COLLECTION=true     # Block external auth
COLLECTION_ENABLED=false          # Collection disabled
RESTART_PROTECTION=true           # Prevent restart loops
MAX_AUTH_ATTEMPTS=10

# External APIs
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Secrets
SECRET_KEY=change-in-production
JWT_SECRET_KEY=change-in-production
```

## Troubleshooting

### Common Issues
1. **Container not updating**: Manual pull needed `docker-compose pull && docker-compose up -d`
2. **Auth failures**: Check `.env` credentials and `FORCE_DISABLE_COLLECTION` setting
3. **Redis connection**: Falls back to memory cache automatically
4. **Database locked**: `python3 init_database.py --force`

### Debug Commands
```bash
# Container logs
docker logs blacklist -f
docker-compose logs redis

# Health check
curl http://localhost:2541/health | jq

# Collection status
curl http://localhost:2541/api/collection/status | jq

# Test specific collector
python3 -m src.core.collectors.regtech_collector
```

## Security Defaults

### Protection Mechanisms
- **External auth blocked by default** (`FORCE_DISABLE_COLLECTION=true`)
- **Collection disabled** (`COLLECTION_ENABLED=false`) 
- **Restart protection** (`RESTART_PROTECTION=true`)
- **Rate limiting** on API endpoints
- **JWT dual-token system** (access + refresh)

### Enabling Collection (CAUTION)
```bash
# Only enable after verifying credentials
FORCE_DISABLE_COLLECTION=false
COLLECTION_ENABLED=true
```

## Development Patterns

### Mixin Pattern (Services)
```python
class UnifiedService(CollectionServiceMixin, StatisticsServiceMixin):
    """Composed service with specialized functionality"""
```

### Blueprint Registration (Routes)
```python
from flask import Blueprint
bp = Blueprint('api', __name__, url_prefix='/api')

# In app_compact.py:
app.register_blueprint(api_routes_bp)
```

### Error Handling
```python
# Never crash - always fallback
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return fallback_value
```

### File Size Enforcement
- **Maximum 500 lines per Python file**
- Split large files into logical modules
- Use mixins for service composition
- Use blueprints for route organization

## Testing Shortcuts

### Run Specific Tests
```bash
# By file
pytest tests/test_apis.py

# By function
pytest tests/test_apis.py::test_regtech_apis

# By pattern
pytest -k "collection"

# By marker
pytest -m api
```

### Test Utilities
```python
# Inline tests (Rust-style)
python3 -c "from src.core.unified_routes import _test_collection_status_inline; _test_collection_status_inline()"
```

## Deployment Scripts

### Main Scripts
- `start.sh` - Docker Compose management
- `scripts/auto-deploy-test.sh` - Full pipeline test
- `scripts/test-watchtower-deployment.sh` - Watchtower verification
- `scripts/load-env.sh` - Environment variable loader

### Makefile Targets
```bash
make init      # Setup environment
make start     # Start services
make stop      # Stop services
make restart   # Restart services
make logs      # View logs
make status    # Check status
make test      # Run tests
make lint      # Code quality
make clean     # Cleanup
```
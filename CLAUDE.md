# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with Docker Compose deployment, multi-source data collection, and FortiGate External Connector integration. Uses Watchtower for automated deployments. Default security mode blocks all external authentication to prevent server lockouts.

### Key Dependencies
- **Python 3.9+** with Flask 2.3.3 web framework
- **Redis 7** for caching (with automatic memory fallback)
- **SQLite** database (file-based at `/app/instance/blacklist.db`)
- **Docker & Docker Compose** for containerization
- **Gunicorn 23.0** WSGI server for production
- **pytest** for testing with extensive marker support

## Development Commands

### Quick Start
```bash
# Environment setup
make init                          # Initialize environment (dependencies, DB, .env)
cp .env.example .env && nano .env  # Configure credentials

# Run services (Docker Compose) - PORT 32542
make start                         # Start all services (uses ./start.sh)
make status                        # Check status
make logs                          # View logs
make stop                          # Stop services

# Local development (without Docker) - PORT 8541
python3 main.py                    # Dev server (port 8541)
python3 main.py --debug           # Debug mode with verbose logging
make dev                           # Auto-reload development mode (FLASK_ENV=development)
make run                           # Same as python3 main.py --debug
```

### Testing
```bash
# Unit tests (make test = full test suite with coverage)
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
pytest --tb=short                 # Short traceback (default in pytest.ini)
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
# Formatting (NOT auto-run on commit)
black src/ tests/                  # Auto-format code
isort src/ tests/                  # Sort imports

# Linting (make lint for basic checks)
flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
bandit -r src/ -ll                 # Security analysis
safety check                       # Dependency vulnerabilities

# File size check (STRICT: max 500 lines)
find src/ -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print}'

# Makefile shortcuts
make lint                          # Basic error checking (flake8 + black + isort)
make security                      # Security checks (bandit + safety)
make clean                         # Remove __pycache__, *.pyc, coverage files
```

## Architecture

### Entry Points & Fallback Chain
```
main.py                             # Main entry point (port 8541)
  └─> src/core/app_compact.py       # Primary app factory with mixins
      └─> src/core/minimal_app.py   # Fallback minimal implementation
          └─> legacy routes          # Ultimate fallback

# App factory composition (src/core/app_compact.py):
CompactFlaskApp(
    AppConfigurationMixin,          # Configuration and optimization
    MiddlewareMixin,                # Request/response processing
    BlueprintRegistrationMixin,     # Route registration
    ErrorHandlerMixin               # Error handling
)
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
  - Auto-restart policy
  
redis:            # Cache (port 6379)
  - Session storage
  - Response caching
  - 256MB memory limit
  - Persistent volume

# Alternative compose files:
docker-compose.yml              # Production deployment
docker-compose.local.yml        # Local development
docker-compose.watchtower.yml   # Watchtower auto-update service
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

## CI/CD Pipeline

### Automated Deployment (Watchtower)
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

### Manual Deployment Options
```bash
# If Watchtower fails
docker-compose pull
docker-compose up -d

# Full deployment workflow (Makefile)
make deploy                        # Build, push, and verify deployment

# Individual deployment steps
make docker-build                  # Build Docker image
make docker-push                   # Push to registry
make docker-run                    # Run container locally for testing

# Kubernetes operations (if using K8s)
make k8s-deploy                    # Deploy to Kubernetes
make k8s-status                    # Check deployment status
make k8s-logs                      # View pod logs

# ArgoCD operations
make argocd-sync                   # Trigger ArgoCD sync
make argocd-status                 # Check ArgoCD app status
```

## Environment Configuration

### Essential Variables (.env)
```bash
# Application (NOTE: Docker uses port 32542, local dev uses 8541)
PORT=32542                        # Docker port (docker-compose.yml)
FLASK_ENV=production
DATABASE_URL=sqlite:////app/instance/blacklist.db
REDIS_URL=redis://redis:6379/0

# Security (docker-compose.yml overrides: collection enabled)
FORCE_DISABLE_COLLECTION=false    # Docker: enabled for collection
COLLECTION_ENABLED=true           # Docker: collection active
RESTART_PROTECTION=false          # Docker: protection disabled
MAX_AUTH_ATTEMPTS=5               # Docker: reduced from 10
BLOCK_DURATION_HOURS=1            # Docker: reduced from 24

# External APIs (REQUIRED for collection)
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
5. **Port conflicts**: Docker uses 32542, local dev uses 8541
   - Docker: `lsof -i :32542` or `netstat -tunlp | grep 32542`
   - Local: `lsof -i :8541` or `netstat -tunlp | grep 8541`

### Debug Commands
```bash
# Container logs
docker logs blacklist -f
docker-compose logs redis
docker-compose logs -f --tail=100 blacklist  # Last 100 lines with follow

# Health check (adjust port based on environment)
curl http://localhost:32542/health | jq      # Docker
curl http://localhost:8541/health | jq       # Local dev
curl http://localhost:32542/api/health | jq  # Detailed health (Docker)

# Collection status
curl http://localhost:32542/api/collection/status | jq  # Docker
curl http://localhost:8541/api/collection/status | jq   # Local

# Test specific collector (standalone)
python3 -m src.core.collectors.unified_collector  # Unified collector test

# Check running containers
docker-compose ps
docker ps | grep blacklist

# Database operations
python3 init_database.py           # Initialize database
python3 init_database.py --force   # Force reinitialize (clears data)

# Environment verification
python3 -c "from src.core.container import get_container; c = get_container(); print(c.get('unified_service'))"
```

## Security Defaults

### Protection Mechanisms
- **Docker Compose**: Collection ENABLED by default (see docker-compose.yml)
- **Local .env.example**: Collection DISABLED by default for safety
- **Rate limiting** on API endpoints
- **JWT dual-token system** (access + refresh)
- **Restart protection** configurable via env vars

### Collection Settings
```bash
# Docker-compose.yml (current production settings)
FORCE_DISABLE_COLLECTION=false    # Collection enabled
COLLECTION_ENABLED=true           # Active collection

# .env.example (safe defaults for new setups)
FORCE_DISABLE_COLLECTION=true     # Collection blocked
COLLECTION_ENABLED=false          # Inactive collection
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

### Performance Testing
```bash
# Run performance benchmarks
python3 tests/integration/performance_benchmark.py

# Load testing endpoints
curl -X GET "http://localhost:2541/api/blacklist/active" -w "\nTime: %{time_total}s\n"
```

## Deployment Scripts

### Main Scripts
- `start.sh` - Docker Compose management (wrapper for docker-compose commands)
- `scripts/auto-deploy-test.sh` - Full pipeline test
- `scripts/test-watchtower-deployment.sh` - Watchtower verification
- `scripts/load-env.sh` - Environment variable loader
- `init_database.py` - Database initialization (run with --force to reset)

### Makefile Targets (Complete List)
```bash
# Basic operations
make help      # Show all available commands
make init      # Setup environment (deps, DB, .env)
make start     # Start services
make stop      # Stop services
make restart   # Restart services
make logs      # View logs
make status    # Check status
make clean     # Remove cache and temp files

# Development
make run       # Run dev server locally
make dev       # Run with auto-reload
make install   # Install dependencies
make test      # Run all tests with coverage
make lint      # Run code quality checks

# Docker operations
make docker-build  # Build Docker image
make docker-push   # Push to registry
make docker-run    # Test container locally

# Kubernetes operations
make k8s-deploy    # Deploy to K8s
make k8s-status    # Check K8s status
make k8s-logs      # View K8s logs
make k8s-describe  # Describe K8s resources

# ArgoCD operations
make argocd-sync   # Trigger sync
make argocd-status # Check app status

# Complete deployment
make deploy    # Full GitOps workflow
```
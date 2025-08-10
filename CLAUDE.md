# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with simplified Docker Compose deployment, multi-source data collection, and FortiGate External Connector integration. Default security mode blocks all external authentication to prevent server lockouts.

## Development Commands

### Quick Start
```bash
# 1. 환경 초기화
make init                          # 자동 환경 설정

# 2. 서비스 시작 (Docker Compose)
make start                         # 또는 ./start.sh
# 또는
docker-compose up -d              # 직접 실행

# 3. 상태 확인
make status                        # 또는 ./start.sh status

# 4. 로그 확인
make logs                          # 또는 ./start.sh logs

# 로컬 개발 (Docker 없이)
make dev                           # 개발 서버 (port 8541)
```

### Testing
```bash
# Unit tests
pytest -v                          # All tests
pytest -k "test_name" -v          # Specific test
pytest -m "not slow" -v           # Fast tests only
pytest --cov=src --cov-report=html  # With coverage

# Integration tests
python3 tests/integration/run_integration_tests.py
python3 tests/integration/performance_benchmark.py

# Inline tests (Rust-style)
python3 -c "from src.core.unified_routes import _test_collection_status_inline; _test_collection_status_inline()"

# Using Makefile
make test                          # Run all tests with coverage
```

### Deployment (단일 Docker Compose)
```bash
# 기본 배포 (권장)
make start                         # 서비스 시작
make stop                          # 서비스 종료
make restart                       # 서비스 재시작

# 또는 직접 스크립트 사용
./start.sh start                   # 서비스 시작
./start.sh stop                    # 서비스 종료
./start.sh logs                    # 로그 확인
./start.sh status                  # 상태 확인
./start.sh update                  # 이미지 업데이트

# 직접 Docker Compose 사용
docker-compose up -d               # 백그라운드 시작
docker-compose down                # 종료
docker-compose logs -f             # 로그 확인
```

### Code Quality
```bash
# Format and lint
black src/ tests/                  # Format code
isort src/ tests/                  # Sort imports
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503

# Security scan
bandit -r src/ -ll                 # Security issues
safety check                       # Dependency vulnerabilities

# Using Makefile shortcuts
make lint                          # Run all linters
make security                      # Run security checks
make test                          # Run tests with coverage
```

## Architecture

### Entry Points
- **Main**: `main.py` → `src/core/app_compact.py` (with fallback chain)
- **Container**: `src/core/container.py` - Dependency injection for all services
- **Routes**: Modular route system in `src/core/routes/` (split from monolithic unified_routes.py)

### Modular Route Architecture (Post-Refactoring)
The routes have been split into logical modules under `src/core/routes/`:
- `web_routes.py` - Web interface and dashboard routes
- `api_routes.py` - Core API endpoints for blacklist management
- `collection_status_routes.py` - Collection status monitoring endpoints
- `collection_trigger_routes.py` - Manual collection trigger endpoints
- `collection_logs_routes.py` - Collection logging and history
- `admin_routes.py` - Administrative and management endpoints
- `test_utils.py` - Testing utilities and mock endpoints

### Modular Service Architecture  
Services split into specialized components under `src/core/services/`:
- `unified_service_core.py` - Core service class with lifecycle management
- `collection_service.py` - Collection-related functionality (mixin pattern)
- `statistics_service.py` - Analytics and statistics methods (mixin pattern)
- `unified_service_factory.py` - Service factory with singleton management

### Key Services (via container)
- `blacklist_manager` - IP management and validation
- `cache_manager` - Redis with memory fallback  
- `collection_manager` - Multi-source data collection
- `unified_service` - Service orchestrator (now modular with mixins)
- `auth_manager` - Authentication and authorization

### MSA Services (Docker Compose)
- Collection Service (8000) - REGTECH/SECUDIUM collection
- Blacklist Service (8001) - IP management  
- Analytics Service (8002) - Statistics and trends
- API Gateway (8080) - Request routing and caching
- Redis (6379) - Distributed caching
- PostgreSQL (5432) - Persistent data storage
- RabbitMQ (5672/15672) - Message queuing

### Security System (Default: All external auth blocked)
```bash
# Environment variables control security
FORCE_DISABLE_COLLECTION=true      # Block all external auth (default)
COLLECTION_ENABLED=false           # Collection off (default)
RESTART_PROTECTION=true            # Prevent infinite restarts
MAX_AUTH_ATTEMPTS=10               # Auth attempt limit
```

## API Endpoints

### Core Endpoints
- `GET /` - Web dashboard
- `GET /health` - Health check
- `GET /api/blacklist/active` - Active IPs (text)
- `GET /api/fortigate` - FortiGate JSON format

### Collection Management
- `GET /api/collection/status` - Collection status
- `POST /api/collection/enable` - Enable (clears data)
- `POST /api/collection/disable` - Disable collection
- `POST /api/collection/regtech/trigger` - Manual REGTECH
- `POST /api/collection/secudium/trigger` - Manual SECUDIUM

### V2 Enhanced APIs
- `GET /api/v2/blacklist/enhanced` - IPs with metadata
- `GET /api/v2/analytics/trends` - Trend analysis
- `GET /api/v2/sources/status` - Detailed source status

### MSA-specific (via Gateway :8080)
- `GET /api/v1/collection/health` - Service health checks
- `GET /api/v1/analytics/report` - Full analytics report
- `GET /api/gateway/services` - Service discovery

## Critical Implementation Notes

### Cache Usage
```python
# MUST use 'ttl=' parameter, not 'timeout='
cache.set(key, value, ttl=300)
@cached(cache, ttl=300, key_prefix="stats")
```

### Content-Type Support
```python
# Support both JSON and form data
if request.is_json:
    data = request.get_json() or {}
else:
    data = request.form.to_dict() or {}
```

### Date Handling
```python
# Use source dates, not current time
if isinstance(detection_date_raw, pd.Timestamp):
    detection_date = detection_date_raw.strftime('%Y-%m-%d')
# NOT: datetime.now().strftime('%Y-%m-%d')
```

### GitHub Actions Compatibility
```yaml
# Self-hosted runner requires specific versions
runs-on: self-hosted
- uses: actions/checkout@v3         # NOT v4
- uses: docker/setup-buildx-action@v2  # NOT v3
- uses: docker/build-push-action@v4    # NOT v5
```

## Data Collection

### REGTECH Collector
- Session-based auth with retry logic
- Date range support: `start_date`, `end_date`
- Excel parsing for IP extraction
- HAR-based fallback available

### SECUDIUM Collector
- POST login to `/isap-api/loginProcess`
- Force login: `is_expire='Y'`
- Excel download from bulletin board
- Bearer token authentication

## Troubleshooting

### Common Issues
1. **502 Bad Gateway**: Check pods with `kubectl get pods -n blacklist`
2. **Auth failures**: Verify credentials in `.env` and container environment
3. **Cache errors**: Redis connectivity - falls back to memory
4. **Database issues**: Run `python3 init_database.py --force`

### Debug Commands
```bash
# Check logs
docker logs blacklist -f
kubectl logs -f deployment/blacklist -n blacklist

# ArgoCD status
argocd app get blacklist --grpc-web
kubectl logs -n argocd deployment/argocd-image-updater

# Test endpoints
curl http://localhost:8541/health
curl http://localhost:8541/api/collection/status
```

## CI/CD Pipeline

### GitHub Actions
- **Workflow**: `.github/workflows/deploy.yaml`
- **Triggers**: Push to main branch
- **Registry**: registry.jclee.me (private registry)
- **Tags**: `latest`, `sha-<hash>`, `date-<timestamp>`
- **Runner**: Self-hosted for security

### ArgoCD GitOps
- **Auto-sync**: Enabled with self-heal
- **Image Updater**: Checks every 2 minutes
- **Rollback**: `argocd app rollback blacklist --grpc-web`
- **Namespace**: blacklist

### Required Secrets
- `DOCKER_REGISTRY_USER` - Registry authentication
- `DOCKER_REGISTRY_PASS` - Registry password
- `REGTECH_USERNAME/PASSWORD` - Data source credentials
- `SECUDIUM_USERNAME/PASSWORD` - Data source credentials

## Environment Configuration

### Key Variables
```bash
# Security (defaults block external auth)
FORCE_DISABLE_COLLECTION=true
COLLECTION_ENABLED=false

# Application
PORT=8541
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key

# Data Sources
REGTECH_USERNAME=username
REGTECH_PASSWORD=password
SECUDIUM_USERNAME=username
SECUDIUM_PASSWORD=password
```

### Deployment Environments
- **Development**: SQLite, port 8541, debug enabled
- **Production**: Gunicorn, port 2541, Redis cache
- **MSA**: PostgreSQL, Redis, RabbitMQ, port 8080

## Project Structure (Post-Modularization)

```
blacklist/
├── main.py                 # Entry point
├── src/
│   ├── core/              # Core business logic
│   │   ├── app_compact.py # Flask app factory
│   │   ├── container.py   # Dependency injection
│   │   ├── routes/        # Modular route system (< 500 lines each)
│   │   │   ├── web_routes.py         # Web interface routes
│   │   │   ├── api_routes.py         # Core API endpoints
│   │   │   ├── collection_*.py       # Collection-related routes
│   │   │   └── admin_routes.py       # Administrative endpoints
│   │   ├── services/      # Modular service system (< 500 lines each)
│   │   │   ├── unified_service_core.py    # Core service class
│   │   │   ├── collection_service.py      # Collection mixin
│   │   │   ├── statistics_service.py      # Statistics mixin  
│   │   │   └── unified_service_factory.py # Service factory
│   │   ├── ip_sources/    # IP source management
│   │   ├── collectors/    # Data collectors
│   │   └── common/        # Shared utilities
│   ├── web/               # Web interface (modularized)
│   │   ├── routes/        # Web-specific route modules
│   │   └── static/        # Static assets
│   └── utils/             # Application utilities
│       ├── cicd_troubleshooter.py      # Main CI/CD troubleshooter interface
│       ├── cicd_troubleshooter_core.py # Core orchestration logic (160 lines)
│       ├── cicd_error_patterns.py      # Error pattern definitions (149 lines)
│       ├── cicd_fix_strategies.py      # Fix implementations (278 lines)
│       └── cicd_utils.py               # File and API utilities (211 lines)
├── services/              # MSA microservices
├── scripts/               # Deployment & management scripts
├── k8s/                   # Kubernetes manifests
├── tests/                 # Comprehensive test suite
│   ├── integration/       # Integration tests
│   └── unit/              # Unit tests
└── deployment/            # Docker configurations
```

## Modular Architecture Patterns

### Service Pattern (Mixin-based)
```python
# Services use multiple inheritance with specialized mixins
class UnifiedService(CollectionServiceMixin, StatisticsServiceMixin):
    """Core service with modular functionality via mixins"""
    
# Access via factory pattern
from src.core.services.unified_service_factory import get_unified_service
service = get_unified_service()
```

### Route Pattern (Flask Blueprint)
```python
# Each route module registers its own Blueprint
from flask import Blueprint
blueprint = Blueprint('api', __name__, url_prefix='/api')

# Import and register in app_compact.py
from src.core.routes.api_routes import blueprint as api_blueprint
app.register_blueprint(api_blueprint)
```

### Backwards Compatibility
All major refactored modules maintain wrapper modules for compatibility:
- `unified_routes.py` → imports from modular `routes/` modules  
- `unified_service.py` → imports from modular `services/` modules
- Original import paths continue to work without changes

## Infrastructure URLs
- **ArgoCD**: https://argo.jclee.me (GitOps dashboard)
- **Registry**: registry.jclee.me (private Docker registry)
- **Charts**: charts.jclee.me (Helm repository)
- **K8s API**: k8s.jclee.me (Kubernetes API server)

## Essential Patterns

### Dependency Injection
```python
# Always use container for service access
from src.core.container import get_container
container = get_container()
service = container.get('unified_service')
```

### Entry Point Fallback Chain
The system has multiple fallback levels:
1. `main.py` → `app_compact.py` (full features)
2. Falls back to `minimal_app.py` (essential features)
3. Ultimate fallback to legacy routes

### Cache Pattern
```python
# Correct cache usage with TTL
cache.set(key, value, ttl=300)  # NOT timeout=300
@cached(cache, ttl=300, key_prefix="stats")
```

### CI/CD Troubleshooter Pattern (Modular)
The CI/CD troubleshooter has been refactored into modular components:
```python
# Main interface (backward compatible)
from src.utils.cicd_troubleshooter import CICDTroubleshooter, create_troubleshooter

# Individual modules for specialized tasks
from src.utils.cicd_troubleshooter_core import CICDTroubleshooter  # Core logic
from src.utils.cicd_error_patterns import ErrorPatternManager     # Error matching
from src.utils.cicd_fix_strategies import FixStrategyManager       # Fix implementations
from src.utils.cicd_utils import CICDUtils                        # Utilities

# Factory pattern usage
troubleshooter = create_troubleshooter()
```

### Error Handling Philosophy
- Never crash the application
- Always provide meaningful fallbacks
- Log before handling errors
- Return appropriate HTTP status codes

## Development Workflow

### Development Server Options
```bash
# Development options
python3 main.py                    # Standard dev server (port 8541)
python3 main.py --debug           # Debug mode with verbose logging
make dev                           # Development with auto-reload
make run                           # Quick run command

# Production deployment
gunicorn -w 4 -b 0.0.0.0:2541 --timeout 120 main:application
```

### Single Test Execution
```bash
# Run specific test
pytest tests/test_apis.py::test_regtech_apis -v

# Run with markers (see pytest.ini for all available markers)
pytest -m "not slow" -v     # Skip slow tests
pytest -m integration -v    # Only integration tests
pytest -m unit -v           # Only unit tests
pytest -m api -v            # API tests only
pytest -m collection -v     # Collection system tests
pytest -m regtech -v        # REGTECH-specific tests
pytest -m secudium -v       # SECUDIUM-specific tests

# Debug failing test
pytest --pdb tests/failing_test.py

# Run tests with specific patterns
pytest -k "test_collection" -v  # All tests with 'collection' in name
```

### Code Quality Enforcement
```bash
# Pre-commit checks
black src/ tests/ --check
flake8 src/ --max-line-length=88
bandit -r src/ -ll

# File size enforcement (500-line rule) - STRICTLY ENFORCED
find src/ -name "*.py" -exec wc -l {} + | awk '$1 > 500 {print}'

# All Python files MUST be under 500 lines
# Files exceeding this limit should be split into logical modules
# Recent example: cicd_troubleshooter.py was split into 5 modules
```

## Security & Authentication

### Default Security Stance
- `FORCE_DISABLE_COLLECTION=true` (blocks all external auth)
- `COLLECTION_ENABLED=false` (collection disabled by default)
- `RESTART_PROTECTION=true` (prevents infinite restarts)

### Credential Management
```bash
# Required secrets in K8s
kubectl create secret generic blacklist-secrets \
  --from-literal=regtech-username=$REGTECH_USERNAME \
  --from-literal=regtech-password=$REGTECH_PASSWORD \
  --from-literal=secudium-username=$SECUDIUM_USERNAME \
  --from-literal=secudium-password=$SECUDIUM_PASSWORD
```

## Development Tools & Utilities

### Makefile Commands
```bash
# Quick development workflow
make init                          # Initialize environment
make test                          # Run tests with coverage
make lint                          # Code quality checks
make security                      # Security scans
make build                         # Build Docker image
make deploy                        # Deploy application
make clean                         # Clean up artifacts

# Individual components
make install                       # Install dependencies only
make run                           # Run development server
make dev                           # Development mode with reload
```

### Script Utilities
```bash
# Environment and configuration
source scripts/load-env.sh         # Load environment variables
./scripts/k8s-management.sh         # Kubernetes operations
./scripts/build-and-push.sh        # Build and push to registry
./scripts/performance-optimizer.sh  # Performance optimization

# CI/CD and monitoring
./scripts/pipeline-health-monitor.sh # Monitor CI/CD health
./scripts/auto-rollback.sh          # Automated rollback
./scripts/cleanup-artifacts.sh     # Clean build artifacts
```
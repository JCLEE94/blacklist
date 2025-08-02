# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with dual architecture support (Monolithic & MSA), GitOps deployment via ArgoCD, multi-source data collection, and FortiGate External Connector integration. Default security mode blocks all external authentication to prevent server lockouts.

## Development Commands

### Quick Start
```bash
# Setup
cp .env.example .env && nano .env  # Configure credentials
source scripts/load-env.sh
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing
python3 init_database.py

# Run (Monolithic)
python3 main.py                    # Dev server (port 8541)
python3 main.py --debug           # Debug mode
gunicorn -w 4 -b 0.0.0.0:2541 --timeout 120 main:application  # Production

# Run (MSA)
./scripts/msa-deployment.sh deploy-docker    # Full MSA stack
cd services/collection-service && python app.py    # Individual services
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

# MSA tests
./scripts/msa-deployment.sh test
curl http://localhost:8080/health  # API Gateway health
```

### Deployment
```bash
# ArgoCD GitOps (Production)
./scripts/k8s-management.sh init    # Initial setup
./scripts/k8s-management.sh deploy  # Deploy
./scripts/k8s-management.sh status  # Check status
./scripts/k8s-management.sh sync    # Manual sync
./scripts/k8s-management.sh rollback  # Rollback

# Docker
docker-compose -f deployment/docker-compose.yml up -d --build

# Multi-server
./scripts/multi-deploy.sh          # Deploy to all clusters

# CI/CD Status
./scripts/check-cicd-status.sh     # Pipeline health check
gh run list --workflow=deploy.yaml --limit=5  # GitHub Actions status
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
```

## Architecture

### Entry Points
- **Main**: `main.py` → `src/core/app_compact.py` (with fallback chain)
- **Container**: `src/core/container.py` - Dependency injection for all services
- **Routes**: `src/core/unified_routes.py` - All API endpoints

### Key Services (via container)
- `blacklist_manager` - IP management and validation
- `cache_manager` - Redis with memory fallback
- `collection_manager` - Multi-source data collection
- `unified_service` - Service orchestrator
- `auth_manager` - Authentication and authorization

### MSA Services (Port 8080 API Gateway)
- Collection Service (8000) - REGTECH/SECUDIUM collection
- Blacklist Service (8001) - IP management
- Analytics Service (8002) - Statistics and trends
- API Gateway (8080) - Request routing and caching

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

## Project Structure

```
blacklist/
├── main.py                 # Entry point
├── src/
│   ├── core/              # Core business logic
│   │   ├── app_compact.py # Flask app factory
│   │   ├── container.py   # Dependency injection
│   │   ├── unified_routes.py # API routes
│   │   └── collection_manager.py # Data collection
│   └── utils/             # Utilities
├── services/              # MSA microservices
├── scripts/               # Deployment & management
├── k8s/                   # Kubernetes manifests
├── tests/                 # Test suites
└── deployment/            # Docker configurations
```

## Best Practices

1. **Security First**: Default blocks all external authentication
2. **Use Container**: Access services via `get_container()`
3. **Test Coverage**: Run tests before committing
4. **GitOps Only**: Never modify K8s resources directly
5. **Cache Parameters**: Always use `ttl=` not `timeout=`
6. **Error Handling**: Centralized in `error_handlers.py`
7. **Date Parsing**: Preserve source dates, don't use current time
8. **MSA Gateway**: All external requests through port 8080
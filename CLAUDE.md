# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with GitOps-based deployment, multi-source data collection, automated processing, and FortiGate External Connector integration. Features dependency injection architecture, containerized deployment with GitHub Actions CI/CD and ArgoCD GitOps automation.

**Key Architecture Principles:**
- **GitOps Deployment**: ArgoCD-based continuous deployment with automatic image updates
- **Multi-Server Support**: Parallel deployment to multiple Kubernetes clusters (local + remote)
- **Dependency Injection**: Central service container (`src/core/container.py`) manages all service lifecycles
- **Multi-layered Entry Points**: `main.py` → `src/core/app_compact.py` → fallback chain for maximum compatibility
- **Plugin-based IP Sources**: Extensible source system in `src/core/ip_sources/`
- **Container-First**: Docker/Podman deployment with automated CI/CD

**Production Infrastructure:**
- Docker Registry: Private registry (configure based on your setup)
- Kubernetes Clusters: 
  - Primary: Self-hosted k3s/k8s (local)
  - Secondary: Remote server (configure as needed)
- ArgoCD Server: Configure based on your environment
- Default Ports: DEV=8541, PROD=2541, NodePort=32542
- Auto-deployment: ArgoCD Image Updater monitors registry
- Production URL: Configure based on your domain
- Timezone: Configure based on your location
- Namespace: `blacklist`

**Data Sources:**
- REGTECH (Financial Security Institute) - Requires authentication, ~9,500 IPs ✅ Active
- SECUDIUM - Standard authentication with POST-based login and Excel download ❌ Disabled (account issues)
- Public Threat Intelligence - Automated collection

## Development Commands

### Initial Setup
```bash
# Clone repository
git clone https://github.com/JCLEE94/blacklist.git
cd blacklist

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
# IMPORTANT: Update credentials and URLs for your environment
nano .env

# Load environment variables
source scripts/load-env.sh

# Install dependencies
pip install -r requirements.txt

# Initialize database (SQLite with auto-migration)
python3 init_database.py

# For development/testing (optional)
pip install pytest pytest-cov pytest-xdist pytest-html
```

### Application Startup
```bash
# Development server (entry point with fallback chain)
python3 main.py                    # Preferred: app_compact → minimal_app → fallback
python3 main.py --port 8080        # Custom port
python3 main.py --debug            # Debug mode

# Production deployment
gunicorn -w 4 -b 0.0.0.0:2541 --timeout 120 main:application
```

### Container Operations
```bash
# Build and push to registry
docker build -f deployment/Dockerfile -t your-registry/blacklist:latest .
docker push your-registry/blacklist:latest

# Local container development
docker-compose -f deployment/docker-compose.yml up -d --build

# Container logs and debugging
docker logs blacklist -f
docker exec -it blacklist /bin/bash

# Force rebuild (no cache)
docker-compose -f deployment/docker-compose.yml build --no-cache
docker-compose -f deployment/docker-compose.yml down
docker-compose -f deployment/docker-compose.yml up -d
```

### ArgoCD Setup
```bash
# ArgoCD + GitHub + Private Registry setup
./scripts/setup/argocd-complete-setup.sh

# This script automatically configures:
# 1. GitHub Repository integration (Private repos supported)
# 2. Private Registry Secret creation
# 3. ArgoCD Image Updater configuration
# 4. ArgoCD Application creation
# 5. CI/CD pipeline workflow generation
# 6. GitHub Actions Secrets setup guidance
```

### Kubernetes Operations (ArgoCD GitOps)
```bash
# Quick deployment using management script
./scripts/k8s-management.sh init      # Initial ArgoCD setup
./scripts/k8s-management.sh deploy    # Deploy with ArgoCD
./scripts/k8s-management.sh status    # Check ArgoCD & pod status
./scripts/k8s-management.sh logs      # View application logs
./scripts/k8s-management.sh rollback  # Rollback via ArgoCD
./scripts/k8s-management.sh sync      # Force ArgoCD sync
./scripts/k8s-management.sh restart   # Rolling restart

# Multi-server deployment
./scripts/multi-deploy.sh             # Deploy to local + remote clusters
./scripts/all-clusters-deploy.sh     # Deploy to all registered K8s clusters

# Cluster management
./scripts/kubectl-register-cluster.sh # Register/manage K8s clusters

# ArgoCD operations
argocd app sync blacklist --grpc-web
argocd app get blacklist --grpc-web
argocd app rollback blacklist --grpc-web

# Manual Kubernetes operations
kubectl apply -k k8s/                 # Deploy using Kustomize

# Check deployment status
kubectl get pods -n blacklist
kubectl get deployment blacklist -n blacklist

# Scale deployment
kubectl scale deployment blacklist --replicas=4 -n blacklist

# View logs
kubectl logs -f deployment/blacklist -n blacklist

# Debug pod issues
kubectl describe pod <pod-name> -n blacklist
kubectl exec -it deployment/blacklist -n blacklist -- /bin/bash

# Rolling restart
kubectl rollout restart deployment/blacklist -n blacklist

# Registry secret management
kubectl create secret docker-registry regcred \
  --docker-server=your-registry \
  --docker-username=your-username \
  --docker-password=your-password \
  --namespace=blacklist
```

### Remote Server Management
```bash
# Initial remote server setup
./scripts/setup/remote-server-setup.sh

# Check remote server status
./scripts/check-remote-status.sh

# Deploy to specific server
ssh user@remote-server "cd ~/app/blacklist && ./scripts/k8s-management.sh deploy"
```

### Cloudflare Tunnel Integration
```bash
# Install cloudflared on host system
./scripts/setup/install-cloudflared.sh install

# Deploy Cloudflare Tunnel to Kubernetes
export CLOUDFLARE_TUNNEL_TOKEN="your-tunnel-token"
./scripts/setup/cloudflared-k8s-setup.sh deploy

# Integration with deployment pipeline
ENABLE_CLOUDFLARED=true ./scripts/k8s-management.sh init
ENABLE_CLOUDFLARED=true ./scripts/deploy.sh

# Check tunnel status
./scripts/setup/cloudflared-k8s-setup.sh status

# View tunnel logs
kubectl logs -l app=cloudflared -n blacklist -f

# Remove tunnel
./scripts/setup/cloudflared-k8s-setup.sh delete
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

# Run a single test
pytest tests/test_core_endpoints.py::test_health_endpoint -v
pytest -k "test_collection_status" -v              # Run tests matching pattern

# Specific test categories
pytest -m "not slow and not integration"            # Unit tests only
pytest tests/test_core_endpoints.py                 # Specific module
pytest -v --cov=src                                 # With coverage
pytest -v --cov=src --cov-report=html              # Coverage with HTML report

# Integration tests
pytest tests/integration/                           # Complete integration test suite
python3 tests/integration/run_integration_tests.py  # Automated test runner

# Performance benchmarking
python3 tests/integration/performance_benchmark.py  # Response time validation

# Quick integration test
python3 tests/quick_integration_test.py

# Inline tests (Rust-style)
python3 -c "from src.core.unified_routes import _test_collection_status_inline; _test_collection_status_inline()"

# Debugging and diagnostics
python3 scripts/debug_regtech_advanced.py          # REGTECH auth analysis
python3 scripts/debug_regtech_har.py               # HAR-based debugging
```

### Linting and Code Quality
```bash
# Install quality tools (optional, not required for basic functionality)
pip install flake8 black isort mypy bandit safety

# Python syntax check
python3 -m py_compile src/**/*.py

# Enhanced linting suite (matches CI/CD pipeline)
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
black --check src/ --diff --color
isort src/ --check-only --diff --color
mypy src/ --ignore-missing-imports --no-error-summary

# Security scanning
bandit -r src/ -f json -o bandit-report.json -ll  # Medium/High severity only
safety check --json --output safety-report.json
# semgrep --config=auto src/ --json --output=semgrep-report.json  # Requires semgrep

# Auto-format code
black src/
isort src/

# Security scan for hardcoded credentials
grep -r -E "(password|secret|key|token)\s*=\s*['\"][^'\"]*['\"]" --include="*.py" src/
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

### CI/CD Pipeline (ArgoCD GitOps)

**GitHub Actions Workflow** (`.github/workflows/gitops-cicd.yml`):
1. **Build & Push**: Docker image to registry
2. **Multi-tag Strategy**: `latest`, `sha-<hash>`, `date-<timestamp>`, branch names
3. **ArgoCD Image Updater**: Automatically detects and deploys new images
4. **Health Checks**: Post-deployment verification
5. **No Artifact Uploads**: Avoids GitHub storage quota issues

**Deployment Flow**:
```
Push to main → GitHub Actions → Build & Push → ArgoCD Auto Deploy
```

**Self-hosted Runner Compatibility**:
```yaml
runs-on: self-hosted
# Must use these specific versions:
- uses: actions/checkout@v3         # NOT v4
- uses: docker/setup-buildx-action@v2  # NOT v3
- uses: docker/build-push-action@v4    # NOT v5
```

**GitOps Features**:
1. **ArgoCD Application**: Auto-sync with self-heal enabled
2. **Image Updater**: Monitors registry for new images every 2 minutes
3. **Progressive Delivery**: Gradual rollout with health checks
4. **Automated Rollback**: Immediate revert on deployment failure
5. **Multi-cluster Support**: Deploy to multiple K8s clusters simultaneously

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

## Deployment Scripts

### ArgoCD GitOps Scripts

**k8s-management.sh** - Complete ArgoCD management tool:
```bash
./scripts/k8s-management.sh init      # Initialize ArgoCD application
./scripts/k8s-management.sh deploy    # Deploy with GitOps
./scripts/k8s-management.sh status    # Check ArgoCD and pod status
./scripts/k8s-management.sh sync      # Force ArgoCD sync
./scripts/k8s-management.sh rollback  # Rollback deployment
./scripts/k8s-management.sh restart   # Rolling restart
./scripts/k8s-management.sh logs      # View application logs
```

**deploy.sh** - Streamlined ArgoCD deployment:
- Creates namespace and secrets
- Applies Kubernetes manifests
- Configures ArgoCD application
- Triggers GitOps sync

**multi-deploy.sh** - Multi-server parallel deployment:
- Deploys to local and remote simultaneously
- Real-time progress monitoring
- Automatic project file sync via rsync
- ArgoCD sync on both clusters

**all-clusters-deploy.sh** - Deploy to all registered Kubernetes clusters:
- Automatically deploys to all kubectl contexts
- Parallel deployment for efficiency
- Cluster-specific status monitoring
- Works with or without ArgoCD

**kubectl-register-cluster.sh** - Kubernetes cluster management:
- Add new clusters via kubeconfig files
- Remote cluster registration via SSH
- Manual cluster configuration
- Connection testing for all clusters

**unified-deploy.sh** - Platform-agnostic deployment:
- Supports: kubernetes, docker, production, local
- ArgoCD GitOps for Kubernetes deployments

**argocd-complete-setup.sh** - ArgoCD automation setup:
- GitHub Repository integration (Private repos supported)
- Private Registry Secret auto-creation
- ArgoCD Image Updater configuration
- ArgoCD Application creation and auto-sync
- CI/CD pipeline workflow generation
- Duplicate run prevention for safe re-execution

### Remote Server Setup

**remote-server-setup.sh** - Automated remote server configuration:
- SSH key setup for passwordless access
- Docker, kubectl, and ArgoCD CLI installation
- Kubernetes configuration sync
- Registry authentication setup

**check-remote-status.sh** - Remote server monitoring:
- Connectivity check
- Tool availability verification
- Kubernetes cluster status
- Deployment health check

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
# Authentication credentials (store in Kubernetes secrets)
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Application configuration
PORT=8541               # Application port
SECRET_KEY=your-secret  # Flask secret key
REDIS_URL=redis://localhost:6379/0  # Optional, falls back to memory cache

# Security
JWT_SECRET_KEY=jwt-secret    # JWT token signing
API_SECRET_KEY=api-secret    # API key generation

# Docker Registry (for CI/CD)
REGISTRY_URL=your-registry     # Private registry URL
DOCKER_REGISTRY_USER=username  # Registry username
DOCKER_REGISTRY_PASS=password  # Registry password

# ArgoCD Configuration
ARGOCD_SERVER=argo.your-domain   # ArgoCD server
ARGOCD_USERNAME=admin             # ArgoCD username
ARGOCD_PASSWORD=password          # ArgoCD password

# ChartMuseum Configuration  
CHARTS_URL=https://charts.your-domain # Helm chart repository
HELM_REPO_USERNAME=admin              # ChartMuseum username
HELM_REPO_PASSWORD=password           # ChartMuseum password

# Cloudflare Tunnel (optional)
ENABLE_CLOUDFLARED=false            # Enable Cloudflare Tunnel deployment
CLOUDFLARE_TUNNEL_TOKEN=your-token  # Cloudflare Zero Trust tunnel token
CLOUDFLARE_HOSTNAME=blacklist.yourdomain.com  # External hostname
```

### GitHub Repository Secrets
Required for CI/CD pipeline:
```bash
# Set these in GitHub Settings → Secrets and variables → Actions
REGISTRY_URL           # Private registry URL
DOCKER_REGISTRY_USER   # Registry username  
DOCKER_REGISTRY_PASS   # Registry password
ARGOCD_SERVER         # ArgoCD server URL
ARGOCD_USERNAME       # ArgoCD username
ARGOCD_PASSWORD       # ArgoCD password
CHARTS_URL            # ChartMuseum URL
HELM_REPO_USERNAME    # ChartMuseum username
HELM_REPO_PASSWORD    # ChartMuseum password
DEPLOYMENT_WEBHOOK_URL # Optional webhook for deployment notifications
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

**ArgoCD Auto-Deployment Issues**:
```bash
# Check ArgoCD application status
argocd app get blacklist --grpc-web
argocd app sync blacklist --grpc-web

# Check ArgoCD Image Updater logs
kubectl logs -n argocd deployment/argocd-image-updater

# Manually trigger sync
argocd app sync blacklist --force --grpc-web

# Check sync status
argocd app wait blacklist --health

# Rollback if needed
argocd app rollback blacklist --grpc-web

# Check application manifests
kubectl get application blacklist -n argocd -o yaml
```

**Multi-Server Deployment Issues**:
```bash
# Check remote server connectivity
ssh user@remote-server "echo Connected"

# Verify remote tools
./scripts/check-remote-status.sh

# Check remote deployment
ssh user@remote-server "kubectl get pods -n blacklist"

# Re-run remote setup if needed
./scripts/setup/remote-server-setup.sh
```

### Integration Testing
Run comprehensive system tests:
```bash
# Complete integration test suite
python3 tests/integration/run_integration_tests.py

# Legacy comprehensive test (still available)
python3 scripts/integration_test_comprehensive.py

# Performance benchmarking
python3 tests/integration/performance_benchmark.py

# Individual test categories
pytest tests/integration/test_collection_endpoints_integration.py
pytest tests/integration/test_service_integration.py
pytest tests/integration/test_error_handling_edge_cases.py
```

Expected results:
- **Integration Tests**: ✅ All endpoints working correctly
- **Performance**: ✅ Average response time <15ms (excellent, target <50ms)
- **Concurrent Load**: ✅ Handles 100+ simultaneous requests
- **Error Handling**: ✅ Comprehensive edge case coverage
- **Security**: ✅ Proper error responses without sensitive data
- **API Contract**: ✅ All documented endpoints implemented and functional

Legacy test expected results:
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

# ArgoCD logs
argocd app logs blacklist --grpc-web

# Remote server logs
ssh user@remote-server "kubectl logs -f deployment/blacklist -n blacklist"
```

### Offline Package Deployment
Download and deploy offline packages for air-gapped environments:
```bash
# Download offline package from GitHub Actions artifacts
# Extract package
tar -xzf blacklist-offline-YYYYMMDD-HHMMSS.tar.gz
cd blacklist-offline-YYYYMMDD-HHMMSS/

# Load Docker image
docker load < blacklist-image.tar.gz

# Deploy with Kubernetes
kubectl create namespace blacklist
kubectl apply -k k8s/

# Or deploy with Helm
helm install blacklist blacklist-*.tgz -n blacklist

# Or run locally
pip install -r requirements.txt
python3 init_database.py
python3 main.py
```

### Manual Deployment (Fallback)
If CI/CD fails, use manual deployment:
```bash
# Build and push manually to private registry
docker build -f deployment/Dockerfile -t your-registry/blacklist:latest .
docker push your-registry/blacklist:latest

# Deploy with ArgoCD
argocd app sync blacklist --grpc-web

# Or use kubectl directly (not recommended with GitOps)
kubectl set image deployment/blacklist blacklist=your-registry/blacklist:latest -n blacklist
kubectl rollout status deployment/blacklist -n blacklist
```

## Quick Fix Guide

### 502 Bad Gateway Fix
If production returns 502:
1. Check if pods are running: `kubectl get pods -n blacklist`
2. Check pod logs: `kubectl logs -f deployment/blacklist -n blacklist`
3. Check service endpoints: `kubectl get endpoints -n blacklist`
4. Check ingress status: `kubectl get ingress -n blacklist`
5. Debug pod: `kubectl describe pod <pod-name> -n blacklist`
6. Force ArgoCD sync: `argocd app sync blacklist --force --grpc-web`

### Memory Issues
If experiencing high memory usage:
1. Check pod memory usage: `kubectl top pods -n blacklist`
2. Check node resources: `kubectl top nodes`
3. Restart deployment: `kubectl rollout restart deployment/blacklist -n blacklist`
4. Scale horizontally: `kubectl scale deployment/blacklist --replicas=6 -n blacklist`
5. Check HPA status: `kubectl get hpa -n blacklist`

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

## Recent Implementations (2025.07.24)

### CI/CD Pipeline Optimization
**GitHub Actions Artifact Storage Fix**:
- Removed artifact uploads from CI/CD pipeline to avoid storage quota issues
- Created streamlined workflow (`gitops-cicd.yml`) focused on build and deploy only
- Created artifact cleanup script to manage existing artifacts
- Result: Pipeline now runs successfully without hitting quota limits

### Code Cleanup Completion
**Code Quality Improvements**:
- Black formatting applied to all Python files (4 files reformatted)
- isort import sorting fixed (60+ files)
- Flake8 issues reduced from 425 to 315 (26% reduction)
- Fixed critical issues: undefined names, bare except clauses, duplicate functions
- Organized file structure: moved test/debug files from root to appropriate directories
- Removed duplicate and temporary files

## Recent Implementations (2025.01.12)

### Integration Testing Suite Implementation
**Comprehensive Testing Infrastructure**:
- Added missing collection management endpoints to maintain API contract compliance
- Implemented Rust-style inline testing within route modules for immediate validation
- Created comprehensive integration test suite covering all scenarios, edge cases, and error handling
- Added performance benchmarking with automated response time validation (achieved 7.58ms average)
- Implemented mock-based testing to prevent external dependencies and ensure test isolation

**Key Testing Files**:
- `tests/integration/test_collection_endpoints_integration.py` - Core endpoint testing
- `tests/integration/test_service_integration.py` - Service layer integration
- `tests/integration/test_error_handling_edge_cases.py` - Error scenarios and edge cases
- `tests/integration/performance_benchmark.py` - Response time and concurrency validation
- `src/core/unified_routes.py` - Added inline tests at end of file (Rust-style pattern)

### Enhanced CI/CD Pipeline and Security
**Registry Configuration Alignment**:
- Fixed critical registry mismatch between CI/CD and ArgoCD
- Updated all Kubernetes manifests and ArgoCD Image Updater configuration
- Resolved automatic deployment issues - GitOps now works seamlessly

**Security and Quality Enhancements**:
- Added Semgrep for advanced code analysis alongside existing tools
- Enhanced Bandit security scanning with severity filtering (-ll for medium/high only)
- Improved Safety dependency vulnerability scanning with JSON reporting
- Added isort for import sorting to maintain code consistency
- Enhanced flake8 configuration (max-line-length=88, ignore E203,W503 for Black compatibility)

**Monitoring and Alerting**:
- Created automated deployment status monitoring workflow (runs every 5 minutes)
- Added health checks for application, connectivity, ArgoCD status, and API endpoints
- Implemented performance monitoring with response time tracking and alerting
- Added critical issue detection with automated alerts and recommended actions

### Documentation and Troubleshooting
**Comprehensive Guides Created**:
- `docs/CI_CD_TROUBLESHOOTING.md` - Complete troubleshooting guide with debugging commands
- `docs/CI_CD_IMPROVEMENTS_SUMMARY.md` - Summary of all improvements with metrics
- `tests/integration/README.md` - Complete testing setup and execution guide
- Enhanced CHANGELOG.md with detailed implementation notes and performance metrics

**Best Practices Documented**:
- Mock-based testing patterns to prevent external dependencies
- Inline testing methodology (Rust-style) for immediate validation
- Registry configuration alignment for GitOps automation
- Security scanning integration with CI/CD pipeline
- Performance benchmarking and monitoring strategies

## Recent Implementations (2025.07.15)

### GitOps Template Pipeline Implementation
**Complete CI/CD Pipeline** (`.github/workflows/gitops-template.yml`):
- Comprehensive CI/CD workflow with GitOps best practices
- Multi-stage deployment with environment-specific configurations
- Parallel quality checks and testing with matrix strategy
- Automatic offline package generation for air-gapped environments
- ArgoCD Image Updater integration for automatic deployments
- Helm chart management with ChartMuseum integration

**Key Features**:
- **Pre-flight checks**: Smart deployment decisions based on branch/tag
- **Parallel execution**: Code quality and tests run concurrently
- **Multi-tag strategy**: `latest`, `sha-<hash>`, `date-<timestamp>`, branch names
- **Offline packages**: Complete deployment bundles for disconnected environments
- **Health monitoring**: Post-deployment health checks with retries
- **GitOps integration**: Automatic ArgoCD sync after successful builds

### Private Registry Configuration
**registry.jclee.me**:
- Primary registry for all Docker images
- No authentication required (public read access)
- Configured with insecure registry support in buildx
- Used by both CI/CD and ArgoCD Image Updater

**Buildx Configuration**:
```yaml
config-inline: |
  [registry."registry.jclee.me"]
    http = true
    insecure = true
```

## Recent Implementations (2025.07.04)

### ArgoCD GitOps Integration
**Complete GitOps Pipeline**:
- Replaced auto-updater CronJob with ArgoCD Image Updater
- Multi-tag strategy for reliable deployments
- Self-healing enabled for automatic recovery
- Progressive delivery with health checks

**Key Files**:
- `k8s/argocd-app-clean.yaml` - ArgoCD application definition
- `scripts/k8s-management.sh` - Complete ArgoCD management tool
- `scripts/deploy.sh` - GitOps-aware deployment script
- `.github/workflows/argocd-deploy.yml` - CI/CD with multi-tag push

### Multi-Server Deployment
**Remote Server Support**:
- Automated SSH key setup and tool installation
- Parallel deployment to multiple clusters
- Real-time deployment monitoring
- Project file synchronization via rsync

**Key Scripts**:
- `scripts/multi-deploy.sh` - Parallel multi-server deployment
- `scripts/setup/remote-server-setup.sh` - Remote server configuration
- `scripts/check-remote-status.sh` - Remote server monitoring

### Namespace Consolidation
- Migrated from `blacklist-new` to `blacklist` namespace
- Updated all Kubernetes manifests
- Cleaned up legacy configurations

### Script Modernization
**Legacy Scripts Moved**:
- Old auto-updater based scripts moved to `legacy/` directory
- All primary scripts updated to use ArgoCD GitOps
- Unified deployment interface via `unified-deploy.sh`

### Dependencies Update Alert
**Dependabot Configuration** (`.github/dependabot.yml`):
- Automated dependency updates enabled for Python packages
- Note: `reviewers` field deprecated - use CODEOWNERS file instead
- Required labels to create: `dependencies`, `python`

### GitHub Actions Compatibility
**Self-hosted Runner Requirements**:
```yaml
# MUST use these specific versions for self-hosted runners:
- uses: actions/checkout@v3         # NOT v4 (fails on self-hosted)
- uses: docker/setup-buildx-action@v2  # NOT v3
- uses: docker/build-push-action@v4    # NOT v5
```

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
- **Container**: Docker/Kubernetes with ArgoCD GitOps
- **CI/CD**: GitHub Actions + Self-hosted Runner
- **Orchestration**: Kubernetes (k3s/k8s) with Kustomize
- **GitOps**: ArgoCD with Image Updater
- **Monitoring**: Built-in performance metrics and health checks
- **JSON**: orjson for high-performance serialization
- **Data Processing**: pandas + openpyxl for Excel parsing

## Quick Reference

```bash
# Development
python3 main.py --debug

# Testing
pytest -v

# CI/CD Deployment (Recommended)
git add . && git commit -m "feat: your changes"
git push origin main  # Triggers automatic GitOps deployment

# Manual ArgoCD Deployment
./scripts/k8s-management.sh deploy

# Multi-Server Deployment
./scripts/multi-deploy.sh  # Deploy to local + remote

# Health Check (Local)
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

# Check deployment status
kubectl get pods -n blacklist
kubectl logs -f deployment/blacklist -n blacklist

# Check ArgoCD status
argocd app get blacklist --grpc-web
argocd app sync blacklist --grpc-web

# Troubleshoot current issues
kubectl describe pod <failing-pod> -n blacklist  # For ImagePullBackOff
kubectl get ingress -n blacklist                 # For 502 errors
kubectl get endpoints -n blacklist               # Check service routing

# Offline Package Download
# Available in GitHub Actions artifacts after pipeline completion
# Package includes: source code + Docker image + Helm charts + install guide

# Remote server status
ssh user@remote-server "kubectl get pods -n blacklist"
```

## GitOps Best Practices

1. **Never modify resources directly** - Always use Git commits
2. **Use ArgoCD for all deployments** - Ensures consistency
3. **Monitor Image Updater logs** - For deployment issues
4. **Tag images properly** - Use semantic versioning when possible
5. **Enable notifications** - Configure ArgoCD alerts
6. **Regular sync checks** - Ensure clusters match Git state
7. **Backup before major changes** - ArgoCD supports easy rollback
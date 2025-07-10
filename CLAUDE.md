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
- Docker Registry: `ghcr.io` (GitHub Container Registry)
- Kubernetes Clusters: 
  - Primary: Self-hosted k3s/k8s (local)
  - Secondary: 192.168.50.110 (remote server)
- ArgoCD Server: `argo.jclee.me`
- Default Ports: DEV=8541, PROD=2541, NodePort=32452
- Auto-deployment: ArgoCD Image Updater monitors registry
- Production URL: https://blacklist.jclee.me
- Timezone: Asia/Seoul (KST)
- Namespace: `blacklist` (consolidated from `blacklist-new`)

**Data Sources:**
- REGTECH (Financial Security Institute) - Requires authentication, ~1,200 IPs ✅ Active
- SECUDIUM - Standard authentication with POST-based login and Excel download ❌ Disabled (account issues)
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
./manual-deploy.sh                 # Build, push to registry

# Local container development
docker-compose -f deployment/docker-compose.yml up -d --build

# Container logs and debugging
docker logs blacklist -f
docker exec -it blacklist /bin/bash

# Force rebuild (no cache)
docker-compose -f deployment/docker-compose.yml build --no-cache
```

### ArgoCD 완전 자동화 설정
```bash
# ArgoCD + GitHub + Private Registry 완전 자동화 설정
./scripts/setup/argocd-complete-setup.sh

# 필요한 환경 변수들이 스크립트에 미리 설정되어 있음:
# - ARGOCD_API_TOKEN: ArgoCD API 토큰
# - GITHUB_TOKEN: GitHub 개인 액세스 토큰
# - REGISTRY 인증 정보: Private registry 접근

# 실행 후 자동으로 설정되는 항목들:
# 1. GitHub Repository 연동 (Private 저장소 지원)
# 2. Private Registry Secret 생성
# 3. ArgoCD Image Updater 설정
# 4. ArgoCD Application 생성
# 5. CI/CD 파이프라인 워크플로우 생성
# 6. GitHub Actions Secrets 설정 안내
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
./scripts/multi-deploy.sh             # Deploy to local + remote (192.168.50.110)
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
  --docker-server=ghcr.io/jclee94 \
  --docker-username=<username> \
  --docker-password=<password> \
  -n blacklist
```

### Remote Server Management
```bash
# Initial remote server setup (192.168.50.110)
./scripts/setup/remote-server-setup.sh

# Check remote server status
./scripts/check-remote-status.sh

# Deploy to specific server
ssh jclee@192.168.50.110 "cd ~/app/blacklist && ./scripts/k8s-management.sh deploy"
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

### CI/CD Pipeline (ArgoCD GitOps)

**GitHub Actions Workflow** (`.github/workflows/streamlined-cicd.yml`):
1. **Parallel Quality Checks**: Lint, security scan, tests
2. **Docker Build**: Multi-stage build with caching to `ghcr.io/jclee94`
3. **Multi-tag Push**: `latest`, `sha-<hash>`, `date-<timestamp>`
4. **ArgoCD Deployment**: Image Updater auto-detects and deploys
5. **Remote Server Deploy**: Parallel deployment to 192.168.50.110
6. **Verification**: Health checks, smoke tests, performance monitoring
7. **Automatic Rollback**: On failure, ArgoCD reverts to previous version

**Deployment Flow**:
```
Push to main → GitHub Actions → Build & Push (3 tags) → ArgoCD Auto-Deploy → Verify → Remote Deploy
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
- Deploys to local and remote (192.168.50.110) simultaneously
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

**argocd-complete-setup.sh** - ArgoCD 완전 자동화 설정:
- GitHub Repository 연동 (Private 저장소 지원)
- Private Registry Secret 자동 생성
- ArgoCD Image Updater 설정
- ArgoCD Application 생성 및 자동 동기화
- CI/CD 파이프라인 워크플로우 생성
- 중복 실행 방지로 안전한 반복 실행

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

# Cloudflare Tunnel (optional)
ENABLE_CLOUDFLARED=false            # Enable Cloudflare Tunnel deployment
CLOUDFLARE_TUNNEL_TOKEN=your-token  # Cloudflare Zero Trust tunnel token
CLOUDFLARE_HOSTNAME=blacklist.yourdomain.com  # External hostname
```

### GitHub Repository Secrets
Required for CI/CD pipeline:
```bash
# Set these in GitHub Settings → Secrets and variables → Actions
DOCKER_USERNAME         # Docker Hub username
DOCKER_PASSWORD         # Docker Hub password  
REGISTRY_USERNAME       # Private registry username (priority)
REGISTRY_PASSWORD       # Private registry password (priority)
DEPLOYMENT_WEBHOOK_URL  # Optional webhook for deployment notifications
CLOUDFLARE_TUNNEL_TOKEN # Cloudflare Zero Trust tunnel token (required for Cloudflare)
CF_API_TOKEN           # Cloudflare API token for DNS management (required for Cloudflare)
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
ssh jclee@192.168.50.110 "echo Connected"

# Verify remote tools
./scripts/check-remote-status.sh

# Check remote deployment
ssh jclee@192.168.50.110 "kubectl get pods -n blacklist"

# Re-run remote setup if needed
./scripts/setup/remote-server-setup.sh
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

# ArgoCD logs
argocd app logs blacklist --grpc-web

# Remote server logs
ssh jclee@192.168.50.110 "kubectl logs -f deployment/blacklist -n blacklist"
```

### Manual Deployment (Fallback)
If CI/CD fails, use manual deployment:
```bash
# Build and push manually
docker build -f deployment/Dockerfile -t ghcr.io/jclee94/blacklist:latest .
docker push ghcr.io/jclee94/blacklist:latest

# Deploy with ArgoCD
argocd app sync blacklist --grpc-web

# Or use kubectl directly (not recommended with GitOps)
kubectl set image deployment/blacklist blacklist=ghcr.io/jclee94/blacklist:latest -n blacklist
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
**Remote Server Support** (192.168.50.110):
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
./scripts/multi-deploy.sh  # Deploy to local + 192.168.50.110

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

# Check deployment status
kubectl get pods -n blacklist
kubectl logs -f deployment/blacklist -n blacklist

# Check ArgoCD status
argocd app get blacklist --grpc-web
argocd app sync blacklist --grpc-web

# Remote server status
ssh jclee@192.168.50.110 "kubectl get pods -n blacklist"
```

## GitOps Best Practices

1. **Never modify resources directly** - Always use Git commits
2. **Use ArgoCD for all deployments** - Ensures consistency
3. **Monitor Image Updater logs** - For deployment issues
4. **Tag images properly** - Use semantic versioning when possible
5. **Enable notifications** - Configure ArgoCD alerts
6. **Regular sync checks** - Ensure clusters match Git state
7. **Backup before major changes** - ArgoCD supports easy rollback
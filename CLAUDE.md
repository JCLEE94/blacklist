# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Blacklist Management System** - Enterprise threat intelligence platform with Docker Compose deployment, multi-source data collection, and FortiGate External Connector integration. Uses Watchtower for automated deployments and ArgoCD GitOps pipeline. 

### Project Status (v1.0.35 - 2025-08-14 현재)
- **GitOps 성숙도**: 9.5/10 (완성도 높음) - GitHub Container Registry 통합, V2 API 완료, 포트폴리오 사이트 런칭
- **아키텍처**: Monolithic (Flask) + 완전 오프라인 배포 시스템
- **성능 기준선**: API 평균 응답시간 7.58ms, 100+ 동시 요청 처리
- **보안 시스템**: Fernet 암호화, 자동 로테이션, 감사 추적
- **모니터링**: Prometheus 55개 메트릭, 23개 알림 규칙, 실시간 대시보드
- **테스트 커버리지**: 95%+ 달성, 모든 통합 테스트 안정화
- **배포 전략**: 완전 오프라인 패키지 (에어갭 환경), 원클릭 설치

### Key Dependencies & Performance Stack (v1.0.35 Enhanced)
- **Python 3.9+** with Flask 2.3.3 web framework + orjson (3x faster JSON)
- **Redis 7** for caching (automatic memory fallback, 256MB limit)
- **SQLite** (dev) / **PostgreSQL** (prod) with connection pooling + 스키마 v2.0
- **Docker & Kubernetes** - ArgoCD GitOps, **ghcr.io** GitHub Container Registry
- **Gunicorn 23.0** WSGI server with Flask-Compress
- **pytest** comprehensive testing (95% coverage, unit/integration/api markers)
- **Prometheus** 55개 메트릭 + 23개 알림 규칙
- **JWT + API Key 이중 보안** 완전 구현 인증 시스템
- **GitHub Pages 포트폴리오** 현대적 설계 (https://jclee94.github.io/blacklist/)
- **완전한 V2 API** Sources + Analytics 엔드포인트
- **오프라인 배포** 완전 자체 포함 패키지

### MSA Architecture Components
- **API Gateway Service** - 라우팅 및 인증
- **Collection Service** - 데이터 수집 (REGTECH/SECUDIUM)
- **Blacklist Service** - IP 관리 및 FortiGate 연동
- **Analytics Service** - 통계 및 트렌드 분석

## Development Commands

### Quick Start (v1.0.34 Enhanced)
```bash
# Environment setup
make init                          # Initialize environment (dependencies, DB, .env)
cp config/.env.example .env && nano .env  # Configure credentials (note: .env.example is in config/)
python3 scripts/setup-credentials.py  # 자격증명 설정

# Database initialization (스키마 v2.0)
python3 app/init_database.py          # 새로운 스키마 v2.0 초기화
python3 app/init_database.py --force  # 강제 재초기화

# Run services (Docker Compose) - PORT 32542
make start                         # Start all services (uses ./start.sh)
make status                        # Check status
make logs                          # View logs
make stop                          # Stop services

# Local development (without Docker) - PORT 8541
python3 app/main.py                    # Dev server (port 8541)
python3 app/main.py --debug           # Debug mode with verbose logging
make dev                           # Auto-reload development mode (FLASK_ENV=development)
make run                           # Same as python3 app/main.py --debug

# 새로운 모니터링 및 헬스체크
curl http://localhost:32542/health | jq        # 기본 헬스체크
curl http://localhost:32542/api/health | jq    # 상세 헬스체크
curl http://localhost:32542/metrics           # Prometheus 메트릭
curl http://localhost:32542/monitoring/dashboard  # 실시간 대시보드
```

### Testing (v1.0.34 - 95% Coverage)
```bash
# Unit tests (make test = full test suite with coverage)
pytest -v                          # All tests (95% coverage)
pytest -k "test_name" -v          # Specific test by name
pytest tests/test_apis.py::test_regtech_apis -v  # Single test function
pytest -m "not slow" -v           # Skip slow tests
pytest --cov=src --cov-report=html  # Coverage report (95%+)

# Test markers (from pytest.ini)
pytest -m unit -v                  # Unit tests only
pytest -m integration -v          # Integration tests (모두 수정됨)
pytest -m api -v                   # API tests
pytest -m collection -v           # Collection system tests
pytest -m regtech -v              # REGTECH-specific
pytest -m secudium -v             # SECUDIUM-specific

# 새로운 테스트 시스템 (v1.0.34)
pytest tests/conftest_enhanced.py  # 향상된 테스트 픽스처
pytest tests/integration/test_cicd_pipeline_fixed.py  # 수정된 CI/CD 테스트
pytest tests/integration/test_error_handling_edge_cases_fixed.py  # 에러 처리 테스트

# Debug failing tests
pytest --pdb tests/failing_test.py
pytest -vvs tests/                # Verbose with stdout
pytest --tb=short                 # Short traceback (default in pytest.ini)

# 성능 테스트
python3 tests/integration/performance_benchmark.py  # 성능 벤치마크
```

### 오프라인 배포 (v1.0.34 새 기능)
```bash
# 오프라인 패키지 생성 (온라인 환경에서)
python3 scripts/create-offline-package.py      # 완전 오프라인 패키지 생성
# 생성물: blacklist-offline-package.tar.gz (~1-2GB)

# 오프라인 환경에서 설치
tar -xzf blacklist-offline-package.tar.gz
cd blacklist-offline-package
sudo ./install-offline.sh                      # 자동 설치 (15-30분)
./verify-installation.sh                       # 설치 검증
./health-check.sh                              # 헬스체크

# 자격증명 관리
python3 scripts/setup-credentials.py          # 대화식 자격증명 설정
python3 scripts/setup-credentials.py --batch  # 배치 모드
python3 scripts/setup-credentials.py --check  # 자격증명 검증
python3 scripts/setup-credentials.py --rotate # 자격증명 로테이션
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

### Analytics (V2 API Complete)
- `GET /api/v2/analytics/trends` - Trend analysis with time series data
- `GET /api/v2/analytics/summary` - Analysis summary with period filtering
- `GET /api/v2/analytics/threat-levels` - Threat level analysis
- `GET /api/v2/analytics/sources` - Source-specific analysis
- `GET /api/v2/analytics/geo` - Geographic analysis
- `GET /api/v2/sources/status` - All sources current status

### Authentication & Security (JWT + API Key)
- `POST /api/auth/login` - JWT dual-token authentication (access + refresh)
- `POST /api/auth/refresh` - JWT token renewal
- `POST /api/auth/logout` - Token invalidation
- `GET /api/auth/profile` - Current user profile
- `GET /api/keys/verify` - API key verification
- `GET /api/keys/list` - List user's API keys (admin)
- `POST /api/keys/create` - Generate new API key (admin)

## Performance Optimization & Monitoring

### Performance Baseline (2025년 기준)
- **API 평균 응답시간**: 7.58ms (목표: <5ms 고성능, <50ms 양호)
- **동시 처리 용량**: 100+ 요청 처리 가능
- **성능 임계값**: 우수 50ms | 양호 200ms | 허용 1000ms | 불량 5000ms+

### 주요 최적화 적용 사항
```python
# JSON 처리 성능 (3배 향상)
import orjson  # 기본 json 대신 사용

# 압축 응답 (대역폭 절약)
from flask_compress import Compress

# 연결 풀링 (DB 성능)
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0
```

### 병목 지점 및 해결책
1. **N+1 쿼리 문제**: SQLAlchemy eager loading, 배치 쿼리
2. **MSA 통신 지연**: HTTP/2, 연결 재사용, 비동기 처리
3. **캐시 미활용**: Redis TTL 전략, 계층적 캐싱
4. **메모리 비효율**: 대량 데이터 스트리밍, 페이징

### 모니터링 & 알림
```bash
# 헬스체크 (K8s 호환)
curl http://localhost:32542/health | jq
curl http://localhost:32542/api/health | jq  # 상세 상태

# 성능 벤치마크
python3 tests/integration/performance_benchmark.py
curl -w "
Time: %{time_total}s
" http://localhost:32542/api/blacklist/active
```

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

## CI/CD Pipeline & GitOps

### Current GitOps Status (성숙도: 8.5/10)
```yaml
# GitHub Container Registry 기반 GitOps 파이프라인
✅ 소스 제어: 9/10 (Git 기반, 자동 브랜칭)
✅ 컨테이너 레지스트리: 9/10 (ghcr.io 완전 통합)
✅ 보안 스캔: 9/10 (Trivy + Bandit)
✅ 테스트: 9/10 (95% 커버리지, 자동화)
✅ CI/CD 파이프라인: 9/10 (ubuntu-latest 안정성)
✅ GitHub Pages: 10/10 (포트폴리오 자동 배포)
⚠️ K8s 매니페스트: 7/10 (Helm 차트 완료)
⚠️ ArgoCD 통합: 7/10 (일부 설정 개선 필요)
✅ 보안 시스템: 10/10 (JWT + API 키 완전 구현)
```

### Automated Deployment (GitHub Container Registry + GitHub Pages)
```yaml
# .github/workflows/main-deploy.yml
- Trigger: Push to main branch
- Runner: ubuntu-latest (stable, scalable)
- Build: Multi-stage Docker (Python 3.9 Alpine)
- Security: Trivy + Bandit scanning
- Push: ghcr.io/jclee94/blacklist:latest
- GitHub Pages: Automatic portfolio deployment
- Monitoring: Real-time health checks
```

### Enhanced Deployment Flow
```
Code Push → GitHub Actions (ubuntu-latest) → Security Scan (Trivy + Bandit) → 
Docker Build → ghcr.io Registry → GitHub Pages Deploy → Health Monitoring → 
Portfolio Update → Auto Documentation → Performance Tracking
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

# Security System (v1.0.35 New)
SECRET_KEY=change-in-production
JWT_SECRET_KEY=change-in-production
API_KEY_ENABLED=true
JWT_ENABLED=true
DEFAULT_API_KEY=blk_generated-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=auto-generated-password

# GitHub Container Registry
REGISTRY_URL=ghcr.io
REGISTRY_USERNAME=jclee94
```

## Troubleshooting

### GitOps & Deployment Issues
1. **ArgoCD OutOfSync**: 
   ```bash
   kubectl get applications -n argocd
   argocd app sync blacklist --force  # 강제 동기화
   ```
2. **프로덕션 502 Bad Gateway**: 
   ```bash
   kubectl logs -f deployment/blacklist -n blacklist
   kubectl describe pod <pod-name> -n blacklist
   ```
3. **이미지 업데이트 실패**: 
   ```bash
   docker-compose pull && docker-compose up -d
   kubectl rollout restart deployment/blacklist -n blacklist
   ```
4. **파드 Pending 상태**: 리소스 부족 또는 노드 스케줄링 이슈
   ```bash
   kubectl describe pod <pending-pod> -n blacklist
   kubectl get nodes -o wide
   ```

### Common Application Issues  
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
python3 app/init_database.py           # Initialize database
python3 app/init_database.py --force   # Force reinitialize (clears data)

# Environment verification
python3 -c "from src.core.container import get_container; c = get_container(); print(c.get('unified_service'))"
```

## New Features (v1.0.35)

### 🚀 GitHub Pages Portfolio
- **Live Site**: https://jclee94.github.io/blacklist/
- **Modern Design**: Dark theme with gradient animations
- **Interactive Elements**: Counter animations, responsive charts
- **Complete Documentation**: API reference, architecture diagrams
- **Performance Metrics**: Real-time system statistics
- **Mobile Responsive**: Optimized for all device sizes

### 🔐 Security System Complete
```bash
# Initialize security system
python3 scripts/init_security.py

# Generated components:
- API keys with expiration management
- JWT dual-token system (access + refresh)
- Security tables (api_keys, token_blacklist, user_sessions)
- Admin account with auto-generated password
- Security configuration (config/security.json)
```

### ✅ V2 API Implementation
- **Analytics API**: 6 comprehensive endpoints with caching
- **Sources API**: Real-time status monitoring
- **Error Handling**: Robust exception management
- **Performance**: Optimized with unified decorators

### 🐳 GitHub Container Registry
```bash
# New registry location
ghcr.io/jclee94/blacklist:latest

# Migration benefits:
- Better integration with GitHub Actions
- Improved reliability and performance
- Automatic cleanup and versioning
- Enhanced security scanning
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
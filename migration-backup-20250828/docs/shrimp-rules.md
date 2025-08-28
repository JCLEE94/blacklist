# AI Agent Development Guidelines - Blacklist Management System

## Project Identity

- **NEVER modify the core purpose**: Enterprise blacklist management with FortiGate integration
- **ALWAYS maintain compatibility**: Flask 2.3.3, Python 3.9+, dependency injection architecture
- **ALWAYS preserve**: GitOps deployment workflow and container registry integration

## Architecture Enforcement Rules

### Dependency Injection Rules

- **MUST use container.py**: Register all new services via `get_container().register()`
- **MUST follow service pattern**: `service = container.get('service_name')`
- **NEVER instantiate services directly**: Use container for all service access
- **ALWAYS register dependencies**: Add new services to container before use
- **REQUIRED imports**: `from src.core.container import get_container`

### Route Organization Rules

- **API routes**: Place in `src/core/routes/api_routes.py`
- **Web routes**: Place in `src/core/routes/web_routes.py`
- **Collection routes**: Place in `src/core/routes/collection_*_routes.py`
- **V2 API routes**: Place in `src/core/v2_routes/` directory
- **MUST register blueprints**: Add to `src/core/app/blueprints.py`
- **ALWAYS use prefixes**: `/api/` for API, `/collection/` for collection management

### Service Layer Rules

- **MUST extend unified patterns**: Follow `src/core/services/unified_service_core.py`
- **ALWAYS use mixins**: Implement functionality as mixins, compose in main service
- **REQUIRED service methods**: `health_check()`, proper error handling
- **MUST use dependency injection**: Access other services via container
- **ALWAYS implement interfaces**: Define clear service contracts

## File Modification Coordination

### Multi-file Update Requirements

- **When adding new route**: Update `src/core/app/blueprints.py` + route file + tests
- **When adding new service**: Update `src/core/container.py` + service file + tests
- **When modifying API**: Update route + documentation + version in constants
- **When changing database**: Update `src/core/database/` + migrations + models
- **When adding collector**: Update `src/core/collectors/` + factory + tests

### Documentation Synchronization

- **When modifying commands**: Update `CLAUDE.md` development commands section
- **When changing API**: Update API documentation in `CLAUDE.md`
- **When adding features**: Update README.md + CLAUDE.md project overview
- **When changing deployment**: Update `k8s/manifests/` + CLAUDE.md deployment section

## Code Quality Standards

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `BlacklistManager`, `CollectionService`)
- **Functions/Variables**: `snake_case` (e.g., `get_blacklist_data`, `cache_manager`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CACHE_TTL`, `API_VERSION`)
- **Files**: `snake_case.py` (e.g., `unified_service.py`, `collection_manager.py`)
- **Directories**: `snake_case` (e.g., `collection_manager/`, `ip_sources/`)

### Import Organization

- **REQUIRED order**: Standard library → Third-party → Local imports
- **ALWAYS use absolute imports**: `from src.core.container import get_container`
- **NEVER use wildcard imports**: Explicit imports only
- **Group related imports**: Separate groups with blank lines
- **Sort within groups**: Alphabetical order

### Error Handling Requirements

- **MUST use custom exceptions**: Import from `src.core.exceptions`
- **ALWAYS log before raising**: `logger.error(f"Description: {error}")`
- **REQUIRED graceful fallbacks**: Redis → memory cache pattern
- **NEVER silent failures**: Always log and handle errors explicitly
- **MUST preserve stack traces**: Use `raise` not `raise e`

## Testing Requirements

### Test File Organization

- **Unit tests**: `tests/unit/test_*.py`
- **Integration tests**: `tests/integration/test_*.py`
- **API tests**: `tests/test_apis.py`
- **MUST mirror structure**: Test file structure matches src structure
- **REQUIRED naming**: `test_[module_name].py`

### Test Implementation Rules

- **ALWAYS mock external services**: REGTECH, SECUDIUM, Redis
- **MUST test error paths**: Network failures, authentication errors
- **REQUIRED coverage**: Minimum 80% for new code
- **ALWAYS test integrations**: Service-to-service interactions
- **MUST validate fixtures**: Use realistic test data

### Test Execution Commands

- **Full test suite**: `python3 -m pytest -v`
- **Unit tests only**: `pytest -m unit -v`
- **Integration tests**: `pytest -m integration -v`
- **Coverage report**: `pytest --cov=src --cov-report=html`
- **ALWAYS run before commit**: Ensure tests pass

## GitOps Deployment Rules

### Kubernetes Manifest Updates

- **When changing image**: Update `k8s/manifests/06-deployment.yaml`
- **When adding secrets**: Update `k8s/manifests/03-secret.yaml`
- **When changing config**: Update `k8s/manifests/02-configmap.yaml`
- **When scaling**: Update `k8s/manifests/13-hpa.yaml`
- **ALWAYS increment version**: Update `k8s/manifests/06-deployment.yaml` app version

### GitHub Actions Integration

- **NEVER modify**: `.github/workflows/main-deploy.yml` without verification
- **ALWAYS test locally**: Run `make test` before pushing
- **REQUIRED commit format**: `type: description` (e.g., `feat: Add new collector`)
- **MUST pass CI**: All GitHub Actions must succeed before merge

### Container Registry Rules

- **ALWAYS build locally**: `make docker-build` before deployment
- **MUST tag properly**: Use commit SHA for production releases
- **REQUIRED registry**: `registry.jclee.me/blacklist:tag`
- **NEVER use latest**: In production manifests use specific tags

## Data Collection Rules

### Collector Implementation

- **MUST inherit from BaseCollector**: Use abstract base class pattern
- **REQUIRED methods**: `collect()`, `health_check()`, `cancel()`
- **ALWAYS handle authentication**: Implement proper session management
- **MUST respect rate limits**: Implement backoff strategies
- **REQUIRED error handling**: Network timeouts, authentication failures

### Data Processing Rules

- **ALWAYS validate IP addresses**: Use `ipaddress` module validation
- **MUST handle duplicates**: Implement deduplication logic
- **REQUIRED data retention**: 3-month automatic cleanup
- **ALWAYS sanitize input**: Validate all external data
- **MUST log collection events**: Track success/failure rates

## Performance Requirements

### Caching Rules

- **MUST use Redis first**: Fallback to memory cache automatically
- **REQUIRED TTL**: Set appropriate cache expiration times
- **ALWAYS cache expensive operations**: Database queries, API calls
- **MUST invalidate properly**: Clear cache on data updates
- **REQUIRED cache keys**: Use consistent naming patterns

### Database Optimization

- **ALWAYS use transactions**: For multi-table operations
- **MUST use connection pooling**: Configure proper pool sizes
- **REQUIRED indexing**: Add indexes for frequently queried columns
- **ALWAYS paginate results**: For large data sets
- **MUST handle deadlocks**: Implement retry logic

## Security Requirements

### Authentication Rules

- **MUST use JWT tokens**: For API authentication
- **REQUIRED token validation**: Validate all incoming tokens
- **ALWAYS encrypt secrets**: Use proper encryption for sensitive data
- **MUST implement rate limiting**: Prevent abuse and DoS
- **REQUIRED HTTPS**: All production traffic must be encrypted

### Input Validation

- **ALWAYS validate inputs**: Use `src/core/validators.py`
- **MUST sanitize outputs**: Prevent XSS and injection attacks
- **REQUIRED parameter checking**: Validate all request parameters
- **ALWAYS use prepared statements**: For database queries
- **MUST implement CSRF protection**: For web forms

## Prohibited Actions

### Code Modifications

- **NEVER modify main.py**: Entry point is stable, use main.py
- **NEVER change container interface**: Dependency injection pattern is fixed
- **NEVER bypass error handling**: All exceptions must be properly handled
- **NEVER hardcode credentials**: Use environment variables or secrets
- **NEVER break backward compatibility**: API changes require versioning

### Deployment Violations

- **NEVER commit secrets**: Use .env files and secret management
- **NEVER skip tests**: All changes must pass test suite
- **NEVER modify production directly**: Use GitOps workflow only
- **NEVER use development settings**: In production environments
- **NEVER ignore health checks**: All services must implement health endpoints

### Architecture Violations

- **NEVER create circular dependencies**: Between modules
- **NEVER bypass service layer**: Direct database access prohibited
- **NEVER create singleton without container**: Use dependency injection
- **NEVER ignore logging**: All significant events must be logged
- **NEVER create tight coupling**: Services must be loosely coupled

## Emergency Procedures

### Production Issues

- **IMMEDIATE rollback**: Use `kubectl rollout undo deployment/blacklist -n blacklist`
- **REQUIRED notification**: Alert team via monitoring channels
- **MUST preserve logs**: Capture logs before rollback
- **ALWAYS investigate**: Root cause analysis required
- **REQUIRED documentation**: Update incident reports

### Development Blockers

- **Database corruption**: Use `python3 commands/utils/init_database.py --force`
- **Redis connection failure**: System falls back to memory cache automatically
- **Container issues**: Use `docker-compose down && docker-compose up -d`
- **Test failures**: Run `make test` and fix before proceeding
- **Deployment pipeline failure**: Check GitHub Actions logs and ArgoCD status

---

*This document is specifically for AI agents working on the Blacklist Management System. Follow these rules strictly to maintain system integrity and deployment pipeline health.*
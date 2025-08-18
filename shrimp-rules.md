# Development Guidelines

## Project Architecture

### Directory Structure Requirements
- **ALWAYS** place source code in `src/` directory
- **ALWAYS** place tests in `tests/` directory mirroring src/ structure
- **ALWAYS** place configuration files in `config/` directory
- **NEVER** create files in root directory except Makefile, docker-compose.yml, README.md, CLAUDE.md, shrimp-rules.md
- **NEVER** create `app/` directory - use `src/core/` instead

### Module Organization Rules
- **ENFORCE** 500-line maximum per Python file - split larger files immediately
- **USE** mixins for service composition in `src/core/services/`
- **USE** blueprints for route organization in `src/core/routes/`
- **PLACE** all collectors in `src/core/collectors/`
- **PLACE** all database models in `src/core/models.py` or `src/core/database/`

## Code Standards

### Import Rules
- **NEVER** use conditional imports with try/except for required packages
- **ALWAYS** import required packages directly at file top
- **USE** absolute imports from src: `from src.core.services import unified_service_factory`
- **NEVER** use relative imports except within same package

### Naming Conventions
- **USE** snake_case for functions and variables
- **USE** PascalCase for classes
- **USE** UPPER_CASE for constants in `src/core/constants.py`
- **PREFIX** private methods with underscore: `_internal_method()`
- **SUFFIX** test files with `test_`: `test_apis.py`

### Type Hints Requirements
- **ALWAYS** add type hints to function parameters and returns
- **USE** `from typing import Dict, List, Optional, Union, Tuple`
- **NEVER** use `Any` when specific type is known
- **DOCUMENT** complex types with docstrings

## Functionality Implementation Standards

### Flask Application Rules
- **ENTRY POINT** is always `src/core/app_compact.py`
- **FALLBACK** chain: app_compact.py → minimal_app.py → legacy routes
- **REGISTER** all blueprints in `app_compact.py` BlueprintRegistrationMixin
- **NEVER** create new Flask() instances outside app factory

### Service Access Patterns
- **USE** factory for singleton: `from src.core.services.unified_service_factory import get_unified_service`
- **USE** container for DI: `from src.core.container import get_container`
- **NEVER** instantiate services directly - always use factory or container
- **CACHE** service instances to avoid recreation

### Route Implementation Rules
- **CREATE** new routes as blueprints in `src/core/routes/`
- **REGISTER** blueprints in `src/core/app_compact.py`
- **USE** `@bp.route()` not `@app.route()`
- **SUPPORT** both JSON and form data in POST endpoints
- **RETURN** consistent JSON responses with status codes

### Collection System Rules
- **COLLECTORS** must inherit from base collector class
- **IMPLEMENT** `collect()` method returning standardized format
- **USE** `src/core/collectors/unified_collector.py` for orchestration
- **HANDLE** authentication failures with retry logic
- **LOG** all collection activities to database

### Database Operations
- **USE** SQLAlchemy models from `src/core/models.py`
- **NEVER** use raw SQL except for migrations
- **IMPLEMENT** connection pooling with size 20
- **USE** transactions for multi-step operations
- **HANDLE** SQLite locked errors with retry

### Caching Rules
- **USE** `ttl=` parameter, NOT `timeout=`
- **USE** Redis with automatic memory fallback
- **IMPLEMENT** cache decorator: `@cached(cache, ttl=300)`
- **INVALIDATE** cache on data updates
- **SET** appropriate TTL based on data volatility

## Framework Usage Standards

### Docker Deployment
- **PORT** 32542 for Docker, 2542 for local development
- **NEVER** hardcode ports - use environment variables
- **UPDATE** both docker-compose.yml and .env when changing configuration
- **USE** multi-stage builds for production images
- **IMPLEMENT** health checks at /health endpoint

### Testing Requirements
- **USE** pytest with markers: unit, integration, api, collection
- **MAINTAIN** 95%+ test coverage
- **NEVER** use MagicMock for core functionality
- **TEST** with real data, not fake inputs
- **RUN** `pytest -m unit` for quick tests

### Environment Variables
- **REQUIRED**: REGTECH_USERNAME, REGTECH_PASSWORD, SECUDIUM_USERNAME, SECUDIUM_PASSWORD
- **CHECK** credentials with `python3 scripts/setup-credentials.py --check`
- **NEVER** commit credentials to repository
- **USE** .env.example as template

## Workflow Standards

### GitOps Pipeline
- **TRIGGER** CI/CD on push to main branch
- **USE** self-hosted runners for better performance
- **PUSH** images to registry.jclee.me
- **DEPLOY** via ArgoCD to Kubernetes
- **UPDATE** GitHub Pages portfolio automatically

### Error Handling
- **NEVER** let application crash - always provide fallback
- **LOG** errors with loguru: `from loguru import logger`
- **RETURN** meaningful error messages in API responses
- **IMPLEMENT** circuit breakers for external services
- **USE** exponential backoff for retries

## Key File Interactions

### Critical File Dependencies
- **WHEN** modifying routes → update `src/core/app_compact.py` blueprint registration
- **WHEN** adding models → update `src/core/database_schema.py` and run migrations
- **WHEN** changing API → update both v1 (`src/core/routes/api_routes.py`) and v2 (`src/core/v2_routes/`)
- **WHEN** modifying collectors → update `src/core/collectors/unified_collector.py`
- **WHEN** changing configuration → update both `.env.example` and `docker-compose.yml`
- **WHEN** updating documentation → update both README.md and CLAUDE.md

### Service Dependencies
- **UnifiedService** depends on CollectionServiceMixin and StatisticsServiceMixin
- **Collectors** depend on authentication services
- **Routes** depend on service factory and container
- **Cache** depends on Redis with memory fallback
- **Database** operations depend on connection manager

## AI Decision Standards

### Priority Hierarchy
1. **FIRST** check existing patterns in codebase
2. **SECOND** follow established conventions in similar files
3. **THIRD** consult CLAUDE.md for project-specific guidance
4. **FOURTH** apply general Python/Flask best practices
5. **NEVER** introduce new patterns without clear justification

### File Modification Strategy
- **CHECK** file size before editing - split if approaching 500 lines
- **PRESERVE** existing code style and formatting
- **MAINTAIN** backwards compatibility unless explicitly breaking
- **UPDATE** tests when modifying functionality
- **RUN** linters after modifications

### Troubleshooting Approach
1. **CHECK** logs in `docker logs blacklist -f`
2. **VERIFY** environment variables are set correctly
3. **TEST** health endpoint: `curl http://localhost:32542/health`
4. **EXAMINE** Redis connection and fallback
5. **REVIEW** database locks and connections

## Prohibited Actions

### Never Do These
- **NEVER** create files without clear purpose
- **NEVER** modify .git directory or git configuration
- **NEVER** commit sensitive data or credentials
- **NEVER** use asyncio.run() inside functions
- **NEVER** bypass the service factory/container pattern
- **NEVER** create circular imports
- **NEVER** ignore the 500-line file limit
- **NEVER** use print() for logging - use logger
- **NEVER** hardcode URLs or credentials
- **NEVER** modify production database without backup

### Security Restrictions
- **NEVER** disable FORCE_DISABLE_COLLECTION without authorization
- **NEVER** expose internal APIs without authentication
- **NEVER** log sensitive information (passwords, tokens)
- **NEVER** use eval() or exec() with user input
- **NEVER** bypass rate limiting on APIs

### Development Restrictions
- **NEVER** push untested code to main branch
- **NEVER** skip CI/CD pipeline checks
- **NEVER** ignore failing tests
- **NEVER** reduce test coverage below 95%
- **NEVER** merge without code review

## Command Execution Standards

### Development Commands
- **RUN** `make init` for initial setup
- **RUN** `make test` before committing
- **RUN** `make lint` to check code quality
- **USE** `python3` not `python` for all commands
- **USE** `uv` for package management, not pip

### Docker Commands
- **START** services: `make start` or `docker-compose up -d`
- **VIEW** logs: `make logs` or `docker-compose logs -f`
- **RESTART** after changes: `make restart`
- **CLEAN** resources: `make clean`
- **UPDATE** images: `docker-compose pull && docker-compose up -d`

### Database Commands
- **INITIALIZE**: `python3 app/init_database.py`
- **FORCE RESET**: `python3 app/init_database.py --force`
- **CHECK** schema version before migrations
- **BACKUP** before destructive operations
- **USE** transactions for data modifications
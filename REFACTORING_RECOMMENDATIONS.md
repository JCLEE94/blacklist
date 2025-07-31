# Code Refactoring Recommendations

## Large File Analysis

### Current State
- `src/core/unified_routes.py`: 4,395 lines
- `src/core/unified_service.py`: 2,897 lines
- Total: 7,292 lines in 2 files

### Refactoring Plan for unified_routes.py

The file is well-organized with clear section markers. Recommended modular breakdown:

#### 1. Web Interface Routes (Lines 40-495)
**Target Module**: `src/core/routes/web_routes.py`
- Dashboard routes
- Search interfaces
- Collection control pages
- Data management pages
- Docker logs interface

#### 2. Core API Endpoints (Lines 496-1423)
**Target Module**: `src/core/routes/api_routes.py`
- Health endpoints
- Blacklist API
- FortiGate endpoints
- Statistics API
- Search functionality

#### 3. Collection Management API (Lines 1424-2295)
**Target Module**: `src/core/routes/collection_routes.py`
- Collection triggers
- Status management
- Manual collection endpoints
- Daily collection control

#### 4. System Management API (Lines 2296-2505)
**Target Module**: `src/core/routes/system_routes.py`
- System statistics
- Maintenance endpoints
- Performance monitoring

#### 5. Enhanced v2 API (Lines 2506-2740)
**Target Module**: `src/core/routes/v2_routes.py`
- Enhanced blacklist API
- Advanced analytics
- Multi-source status

#### 6. Docker & Infrastructure (Lines 2741-2870)
**Target Module**: `src/core/routes/docker_routes.py`
- Container monitoring
- Log streaming
- Infrastructure status

#### 7. Authentication & Settings (Lines 2871-3662)
**Target Module**: `src/core/routes/auth_routes.py`
- Cookie management
- Authentication settings
- Configuration management

#### 8. Testing & Development (Lines 3663-4395)
**Target Module**: `src/core/routes/dev_routes.py`
- GitHub issue reporting
- Test endpoints
- Inline tests
- Development utilities

### Refactoring Benefits

1. **Improved Maintainability**: Each module focuses on specific functionality
2. **Better Testing**: Easier to test individual route groups
3. **Reduced Complexity**: Smaller files are easier to understand
4. **Team Collaboration**: Multiple developers can work on different route modules
5. **Performance**: Faster loading and compilation times

### Implementation Strategy

1. **Phase 1**: Extract web interface routes (lowest risk)
2. **Phase 2**: Extract API routes with proper testing
3. **Phase 3**: Extract collection and system routes
4. **Phase 4**: Extract specialized routes (v2, Docker, auth)
5. **Phase 5**: Move inline tests to proper test files

### Shared Dependencies

All route modules will need:
- `from .container import get_container`
- `from .unified_service import get_unified_service`
- `from .exceptions import ValidationError, create_error_response, handle_exception`
- Common Flask imports

### Blueprint Registration

Update `src/core/app_compact.py` to register all route blueprints:

```python
from src.core.routes import (
    web_routes,
    api_routes,
    collection_routes,
    system_routes,
    v2_routes,
    docker_routes,
    auth_routes,
    dev_routes
)

# Register blueprints
app.register_blueprint(web_routes.bp)
app.register_blueprint(api_routes.bp)
app.register_blueprint(collection_routes.bp)
app.register_blueprint(system_routes.bp)
app.register_blueprint(v2_routes.bp)
app.register_blueprint(docker_routes.bp)
app.register_blueprint(auth_routes.bp)
if app.config.get('TESTING') or app.config.get('DEBUG'):
    app.register_blueprint(dev_routes.bp)
```

## unified_service.py Refactoring

### Current Analysis
- Single large service class with multiple responsibilities
- Mix of data collection, caching, statistics, and system management

### Recommended Service Decomposition

1. **CollectionService**: Data collection and source management
2. **CacheService**: Caching and performance optimization
3. **StatisticsService**: Metrics and analytics
4. **SystemService**: Health checks and system information
5. **ReportingService**: Log management and reporting

### Benefits of Service Decomposition

1. **Single Responsibility**: Each service has a clear, focused purpose
2. **Dependency Injection**: Services can be independently tested and mocked
3. **Performance**: Lazy loading of services only when needed
4. **Maintenance**: Easier to update individual service functionality

## Implementation Notes

- Preserve all existing functionality during refactoring
- Maintain backward compatibility with existing API contracts
- Add comprehensive tests for each extracted module
- Use gradual migration approach to minimize risk
- Update documentation after each phase

## Priority Ranking

1. **High Priority**: Extract inline tests to proper test files
2. **Medium Priority**: Break down unified_routes.py into logical modules
3. **Low Priority**: Refactor unified_service.py (requires more careful planning)

This refactoring will significantly improve code maintainability while preserving all existing functionality.
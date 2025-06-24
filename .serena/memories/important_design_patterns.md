# Important Design Patterns and Guidelines

## Dependency Injection Architecture
The system uses a central service container pattern:
```python
from src.core.container import get_container
container = get_container()
service = container.get('service_name')
```
All services are registered in `BlacklistContainer` and managed centrally.

## Multi-layered Entry Points
The system has a robust fallback mechanism:
1. `main.py` → `app_compact.py` (full features)
2. Falls back to → `minimal_app.py` (essential features)
3. Falls back to → Legacy `app.py`

This ensures the application can start even with partial failures.

## Caching Strategy
- Primary: Redis with configurable TTL
- Fallback: In-memory cache
- Cache keys use specific prefixes (CACHE_PREFIX_*)
- Important: Use `ttl=` parameter, not `timeout=`

## Error Handling Philosophy
- Never let the application crash
- Always provide meaningful fallbacks
- Log errors before handling
- Custom exceptions for different error types
- Return appropriate HTTP status codes

## Data Collection Architecture
- Centralized ON/OFF control via CollectionManager
- Each source can be triggered independently
- Session management for authenticated sources
- Automatic retry with exponential backoff

## Performance Optimizations
- orjson for 3x faster JSON processing
- Connection pooling for database
- Response compression with Flask-Compress
- Batch processing for large datasets
- Rate limiting per endpoint

## Security Considerations
- No hardcoded credentials (use environment variables)
- Input validation on all endpoints
- SQL injection prevention via SQLAlchemy
- Rate limiting to prevent abuse
- IP whitelisting for admin endpoints

## Korean-English Mixed Documentation
The codebase uses both Korean and English:
- Korean: Business logic explanations, comments
- English: Technical terms, function/variable names
- This reflects the Korean enterprise environment

## Testing Strategy
- Unit tests: Fast, isolated component tests
- Integration tests: Full system workflow tests
- Markers: `slow`, `integration`, `unit`
- Skip slow tests during development
# Code Style and Conventions

## Python Version
- Python 3.9+ compatible

## Code Organization
- Module-based architecture with clear separation of concerns
- Dependency injection pattern using service container
- Abstract base classes for extensibility (e.g., BaseIPSource)

## Naming Conventions
- Snake_case for functions and variables
- PascalCase for classes
- UPPER_CASE for constants
- Descriptive names (e.g., `blacklist_manager`, `cache_manager`)

## Type Hints
- Extensive use of type hints throughout codebase
- Custom types defined in `src/core/models.py`
- Generic types with TypeVar where appropriate

## Docstrings
- Korean and English mixed documentation
- Class and method docstrings present
- Focus on explaining business logic

## Error Handling
- Custom exceptions in `src/core/exceptions.py`
- Comprehensive try-except blocks
- Logging before raising exceptions
- Graceful fallbacks (e.g., Redis → memory cache)

## Imports
- Absolute imports preferred
- Grouped by: standard library, third-party, local
- Conditional imports for optional dependencies

## Design Patterns
- Singleton pattern for service instances
- Factory pattern for configuration
- Decorator pattern for caching/auth/monitoring
- Repository pattern for data access
# Task Completion Checklist

## Before Committing Code

### 1. Code Quality Checks
While no automated linting/formatting tools are configured in the project:
- Ensure code follows PEP 8 style guidelines
- Verify proper indentation (4 spaces)
- Check for unused imports and variables
- Ensure all functions have type hints
- Add/update docstrings for new functions/classes

### 2. Testing
```bash
# Run tests to ensure nothing is broken
pytest -m "not slow and not integration"  # Quick unit tests
pytest                                     # Full test suite if time permits
```

### 3. Manual Verification
- Test the specific functionality you implemented
- Check API endpoints with curl or browser
- Verify error handling works as expected
- Ensure logging is appropriate (not too verbose)

### 4. Documentation
- Update CLAUDE.md if you changed core functionality
- Update relevant documentation in docs/ directory
- Add inline comments for complex logic
- Update API documentation if endpoints changed

### 5. Performance Considerations
- Check for potential bottlenecks (database queries, loops)
- Ensure proper caching is implemented where needed
- Verify no memory leaks or resource issues

### 6. Security Review
- No hardcoded credentials or secrets
- Input validation for all user inputs
- SQL injection prevention (using parameterized queries)
- Proper error messages (no sensitive info exposed)

### 7. Container Testing (if applicable)
```bash
# Build and test in container
docker-compose -f docker/docker-compose.yml build
docker-compose -f docker/docker-compose.yml up -d
docker logs blacklist-app-1  # Check for startup errors
```

### 8. Commit Message
Use conventional commit format:
- feat: New feature
- fix: Bug fix
- docs: Documentation only
- style: Code style changes
- refactor: Code refactoring
- test: Test additions/changes
- chore: Build process or auxiliary tool changes
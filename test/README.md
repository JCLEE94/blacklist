# Test Structure

This directory contains all tests following CNCF testing best practices.

## Directory Structure

```
test/
├── e2e/                    # End-to-end tests
├── integration/            # Integration tests  
├── fixtures/               # Test data and fixtures
└── README.md              # This file
```

## Test Categories

### End-to-End Tests (`e2e/`)
- Full application workflow tests
- Browser-based testing with real UI
- Production-like environment testing
- Performance and load testing

### Integration Tests (`integration/`)
- Service integration testing
- Database integration tests
- API integration tests
- External service integration tests

### Fixtures (`fixtures/`)
- Test data files
- Mock responses
- Configuration files for testing
- Sample datasets

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# End-to-end tests
make test-e2e
```

## Test Guidelines

1. **Isolation**: Each test should be independent
2. **Repeatability**: Tests should produce consistent results
3. **Fast Feedback**: Unit tests should be fast (<1s each)
4. **Real Data**: Use real data when possible, avoid mocking core functionality
5. **Coverage**: Aim for 95% code coverage

## Test Environment

Tests use the following environment:
- Python pytest framework
- Docker containers for integration tests
- Real database connections (test database)
- Mock external API calls where appropriate
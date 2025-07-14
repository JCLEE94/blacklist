# Integration Tests for Blacklist Management System

This directory contains comprehensive integration tests for the blacklist management system, focusing on the collection management endpoints and service layer integration.

## Test Structure

### 1. Inline Integration Tests (Rust-style)
- **Location**: `src/core/unified_routes.py` (at the end of file)
- **Functions**:
  - `_test_collection_endpoints()` - Tests all collection API endpoints
  - `_test_collection_state_consistency()` - Verifies state consistency
  - `_test_concurrent_requests()` - Tests concurrent request handling

### 2. PyTest Integration Tests
- **test_collection_endpoints_integration.py** - Collection endpoint tests
- **test_service_integration.py** - Service layer integration tests
- **test_error_handling_edge_cases.py** - Error handling and edge cases

### 3. Test Runner
- **run_integration_tests.py** - Automated test runner for all tests

## Prerequisites

```bash
# Install required dependencies
pip install pytest pytest-cov flask

# Ensure the application dependencies are installed
pip install -r requirements.txt
```

## Running the Tests

### Run All Integration Tests
```bash
python3 tests/integration/run_integration_tests.py
```

### Run Inline Tests Only
```bash
python3 -m src.core.unified_routes
```

### Run Specific Test File
```bash
pytest tests/integration/test_collection_endpoints_integration.py -v
```

### Run with Coverage Report
```bash
pytest tests/integration/ --cov=src --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Run Tests in Watch Mode
```bash
pytest-watch tests/integration/ -- -v
```

## Test Features

### 1. Mock-Based Testing
All tests use mocks to avoid external dependencies:
- No real database connections
- No actual HTTP requests to external services
- Fast execution and reliable results

### 2. Comprehensive Coverage
Tests cover:
- ✅ Happy path scenarios
- ✅ Error handling
- ✅ Edge cases
- ✅ Concurrent access
- ✅ Performance characteristics
- ✅ State consistency

### 3. Test Organization
Each test file focuses on specific aspects:
- **Collection Endpoints**: API contract testing
- **Service Integration**: Component interaction testing
- **Error Handling**: Resilience and recovery testing

## Key Test Scenarios

### Collection Management
- Collection always enabled state
- Enable/disable endpoint behavior
- REGTECH trigger with date parameters
- SECUDIUM disabled status
- Concurrent collection requests

### Error Scenarios
- Network timeouts
- Authentication failures
- Database errors
- Malformed data handling
- Resource exhaustion

### Edge Cases
- Unicode characters
- Null values
- Empty responses
- Future/past dates
- Large data sets

## Writing New Tests

### 1. Follow the Pattern
```python
def test_new_feature(self, client, mock_service):
    """Test description"""
    # Arrange
    mock_service.method.return_value = expected_data
    
    # Act
    with patch('src.core.unified_routes.service', mock_service):
        response = client.post('/api/endpoint')
    
    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
```

### 2. Use Fixtures
- `app` - Flask test application
- `client` - Test client for making requests
- `mock_service` - Pre-configured mock service
- `failing_service` - Service that simulates failures

### 3. Test Naming Convention
- `test_<feature>_<scenario>` - e.g., `test_collection_enable_is_idempotent`
- Be descriptive about what is being tested

## Continuous Integration

To integrate with CI/CD:

```yaml
# .github/workflows/test.yml
- name: Run Integration Tests
  run: |
    python3 tests/integration/run_integration_tests.py
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure project root is in PYTHONPATH
   - Check all dependencies are installed

2. **Test Failures**
   - Check mock configurations match actual service behavior
   - Verify endpoint URLs are correct
   - Ensure response formats match implementation

3. **Slow Tests**
   - Use mocks instead of real services
   - Avoid time.sleep() in tests
   - Run tests in parallel: `pytest -n auto`

### Debug Mode
```bash
# Run with verbose output
pytest -vv tests/integration/

# Run with debug print statements
pytest -s tests/integration/

# Run specific test with debugging
pytest -k "test_collection_enable" -vvs
```

## Demo Without Dependencies

If dependencies are not installed, you can run the demo:

```python
# Create demo_integration_tests.py (included in initial implementation)
python3 demo_integration_tests.py
```

This demonstrates how the tests work without requiring all dependencies.

## Refactoring Suggestions

See `refactoring_suggestions.md` for recommendations on improving code testability:
- Extract configuration constants
- Implement dependency injection
- Use response builder pattern
- Add service result objects
- Create testable time provider

## Contributing

When adding new integration tests:
1. Follow existing patterns
2. Ensure tests are independent
3. Use meaningful assertions
4. Document complex test scenarios
5. Keep tests fast and reliable
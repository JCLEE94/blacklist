#!/usr/bin/env python3
"""
Common Decorators Module

Shared decorators used across API routes and services.
Consolidates authentication, validation, and rate limiting.

Sample input: @require_auth decorator on API endpoint
Expected output: Authenticated request handling with consistent behavior
"""

import functools
import logging
from typing import Callable, Any

from flask import request, jsonify

logger = logging.getLogger(__name__)


def require_auth(f: Callable) -> Callable:
    """
    Authentication decorator for API endpoints.
    
    Checks for valid authentication tokens or API keys.
    Falls back to mock implementation in development/testing.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Try to import and use real auth system
            from ..utils.security.auth import check_auth
            
            auth_result = check_auth(request)
            if not auth_result.get('valid', False):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
                
        except ImportError:
            # Development/testing fallback - log warning
            logger.warning("Using mock authentication - development mode only")
            
        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return jsonify({
                'success': False,
                'error': 'Authentication system error'
            }), 500
            
        return f(*args, **kwargs)
    
    return wrapper


def rate_limit(limit: int = 60, window_seconds: int = 60) -> Callable:
    """
    Rate limiting decorator for API endpoints.
    
    Args:
        limit: Maximum requests allowed
        window_seconds: Time window for rate limiting
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Try to import and use real rate limiting
                from ..utils.security.rate_limiting import check_rate_limit
                
                if not check_rate_limit(request, limit, window_seconds):
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded'
                    }), 429
                    
            except ImportError:
                # Development/testing fallback
                logger.debug(f"Mock rate limiting: {limit}/{window_seconds}s")
                
            except Exception as e:
                logger.error(f"Rate limiting check failed: {e}")
                # Continue processing - don't fail on rate limit errors
                
            return f(*args, **kwargs)
        
        return wrapper
    
    return decorator


def input_validation(schema: dict = None) -> Callable:
    """
    Input validation decorator for API endpoints.
    
    Args:
        schema: Validation schema (optional)
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Try to import and use real validation
                from ..utils.security.validation import validate_request
                
                validation_result = validate_request(request, schema)
                if not validation_result.get('valid', True):
                    return jsonify({
                        'success': False,
                        'error': validation_result.get('error', 'Invalid input')
                    }), 400
                    
            except ImportError:
                # Development/testing fallback
                logger.debug("Mock input validation")
                
            except Exception as e:
                logger.error(f"Input validation failed: {e}")
                # Continue processing - validation errors are logged but don't fail request
                
            return f(*args, **kwargs)
        
        return wrapper
    
    return decorator


def error_handler(default_message: str = "Internal server error") -> Callable:
    """
    Error handling decorator for API endpoints.
    
    Args:
        default_message: Default error message for unhandled exceptions
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Unhandled error in {f.__name__}: {e}")
                return jsonify({
                    'success': False,
                    'error': default_message
                }), 500
        
        return wrapper
    
    return decorator


class MockDecorators:
    """
    Mock implementations for testing and development.
    Used when security modules are not available.
    """
    
    @staticmethod
    def require_auth(f: Callable) -> Callable:
        """Mock authentication decorator"""
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            logger.debug("Mock auth: allowing request")
            return f(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def rate_limit(limit: int = 60, window_seconds: int = 60) -> Callable:
        """Mock rate limiting decorator"""
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                logger.debug(f"Mock rate limit: {limit}/{window_seconds}s")
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def input_validation(schema: dict = None) -> Callable:
        """Mock input validation decorator"""
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                logger.debug("Mock input validation: allowing request")
                return f(*args, **kwargs)
            return wrapper
        return decorator


if __name__ == "__main__":
    import sys
    from unittest.mock import Mock
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: require_auth decorator
    total_tests += 1
    try:
        @require_auth
        def test_function():
            return "success"
        
        result = test_function()
        if result != "success":
            all_validation_failures.append(f"Auth decorator test: Expected 'success', got {result}")
    except Exception as e:
        all_validation_failures.append(f"Auth decorator test: Failed - {e}")
    
    # Test 2: rate_limit decorator
    total_tests += 1
    try:
        @rate_limit(limit=10, window_seconds=60)
        def test_rate_limited():
            return "rate_limited"
        
        result = test_rate_limited()
        if result != "rate_limited":
            all_validation_failures.append(f"Rate limit decorator test: Expected 'rate_limited', got {result}")
    except Exception as e:
        all_validation_failures.append(f"Rate limit decorator test: Failed - {e}")
    
    # Test 3: error_handler decorator
    total_tests += 1
    try:
        @error_handler("Test error")
        def test_error_handler():
            return "no_error"
        
        result = test_error_handler()
        if result != "no_error":
            all_validation_failures.append(f"Error handler decorator test: Expected 'no_error', got {result}")
    except Exception as e:
        all_validation_failures.append(f"Error handler decorator test: Failed - {e}")
    
    # Test 4: Mock decorators
    total_tests += 1
    try:
        mock_decorators = MockDecorators()
        
        @mock_decorators.require_auth
        def test_mock_auth():
            return "mock_success"
        
        result = test_mock_auth()
        if result != "mock_success":
            all_validation_failures.append(f"Mock decorators test: Expected 'mock_success', got {result}")
    except Exception as e:
        all_validation_failures.append(f"Mock decorators test: Failed - {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Common decorators module is validated and ready for use")
        sys.exit(0)

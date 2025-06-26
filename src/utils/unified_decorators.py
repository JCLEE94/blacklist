"""
Unified Decorators - Consolidates all decorator functionality
Eliminates duplicate caching, authentication, and monitoring decorators
Updated with improved type hints and structured error handling
"""
import time
import json
import hashlib
from functools import wraps
from typing import Optional, Callable, Any, Dict, Union, Tuple
from flask import request, jsonify, g
from datetime import datetime
import logging

# Import structured exceptions and models
from src.core.exceptions import ValidationError, AuthenticationError, RateLimitError, CacheError
from src.core.models import ValidationResult, APIResponse
from src.core.constants import ERROR_MESSAGES, HTTP_STATUS_CODES

logger = logging.getLogger(__name__)


class DecoratorRegistry:
    """Central registry for all application decorators"""
    
    def __init__(self):
        self._cache = None
        self._auth_manager = None
        self._rate_limiter = None
        self._metrics = None
    
    def set_dependencies(self, cache=None, auth_manager=None, rate_limiter=None, metrics=None):
        """Set shared dependencies for decorators"""
        self._cache = cache
        self._auth_manager = auth_manager
        self._rate_limiter = rate_limiter
        self._metrics = metrics


# Global registry instance
_registry = DecoratorRegistry()


def unified_cache(
    ttl: int = 300,
    timeout: Optional[int] = None,  # Deprecated, use ttl instead
    key_func: Optional[Callable] = None,
    key_prefix: str = "",
    cache_unless: Optional[Callable] = None,
    per_user: bool = False
):
    """
    Unified caching decorator that works with multiple cache backends
    Consolidates all caching logic into a single, configurable decorator
    
    Args:
        ttl: Time to live in seconds (preferred parameter)
        timeout: Deprecated, use ttl instead
        key_func: Custom function to generate cache key
        key_prefix: Prefix for cache key
        cache_unless: Function that returns True to skip caching
        per_user: Whether to include user context in cache key
    """
    # Handle backward compatibility
    if timeout is not None:
        import warnings
        warnings.warn(
            "timeout parameter is deprecated, use ttl instead",
            DeprecationWarning,
            stacklevel=2
        )
        ttl = timeout
    def cache_decorator(func):
        @wraps(func)
        def cache_wrapper(*args, **kwargs):
            # Skip caching if condition is met
            if cache_unless and cache_unless():
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func()
            else:
                # Default key generation
                key_parts = [
                    func.__name__,
                    str(hash(str(args))),
                    str(hash(str(sorted(kwargs.items()))))
                ]
                
                # Add user context if requested
                if per_user and hasattr(g, 'user_id'):
                    key_parts.append(f"user_{g.user_id}")
                
                # Add request context for routes
                try:
                    if hasattr(request, 'endpoint') and request.endpoint:
                        key_parts.extend([
                            request.endpoint,
                            str(sorted(request.args.items()))
                        ])
                except RuntimeError:
                    # Outside of request context, which is fine for tests
                    pass
                
                prefix = f"unified:{key_prefix}:" if key_prefix else "unified:"
                cache_key = prefix + hashlib.md5(
                    ":".join(key_parts).encode()
                ).hexdigest()
            
            # Try to get from cache
            if _registry._cache is not None:
                try:
                    cached_result = _registry._cache.get(cache_key)
                    if cached_result is not None:
                        logger.debug(f"Cache hit for key: {cache_key}")
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache get error: {e}")
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            if _registry._cache is not None and hasattr(_registry._cache, 'set'):
                try:
                    _registry._cache.set(cache_key, result, ttl=ttl)
                    logger.debug(f"Cached result for key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set error: {e}")
            else:
                logger.debug(f"Cache not available, skipping cache set for key: {cache_key}")
            
            return result
        return cache_wrapper
    return cache_decorator


def unified_rate_limit(
    limit: int,
    per: int = 3600,  # per hour by default
    key_func: Optional[Callable] = None,
    exempt_when: Optional[Callable] = None,
    use_user_id: bool = True
):
    """
    Unified rate limiting decorator
    Consolidates rate limiting logic with flexible key generation
    
    Args:
        limit: Maximum number of requests allowed
        per: Time window in seconds (default: 3600 = 1 hour)
        key_func: Custom function to generate rate limit key
        exempt_when: Function to determine if rate limiting should be skipped
        use_user_id: Use authenticated user ID if available
    """
    def rate_limit_decorator(func):
        @wraps(func)
        def rate_limit_wrapper(*args, **kwargs):
            # Skip rate limiting if exemption condition is met
            if exempt_when and exempt_when():
                return func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                identifier = key_func()
            else:
                # Use authenticated user ID if available and requested
                if use_user_id and hasattr(g, 'auth_user') and g.auth_user:
                    identifier = g.auth_user.get('user_id', g.auth_user.get('client_name'))
                else:
                    # Default to IP address
                    client_ip = request.remote_addr
                    if request.headers.get('X-Forwarded-For'):
                        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
                    identifier = client_ip
                
                rate_key = f"rate_limit:{func.__name__}:{identifier}"
            
            # Check rate limit
            if _registry._rate_limiter:
                try:
                    # Use the check_rate_limit method that returns tuple
                    allowed, limit_val, remaining = _registry._rate_limiter.check_rate_limit(
                        identifier if not key_func else rate_key, 
                        limit
                    )
                    
                    if not allowed:
                        logger.warning(f"Rate limit exceeded for key: {rate_key}")
                        response = jsonify({
                            'error': 'Rate limit exceeded',
                            'limit': limit_val,
                            'retry_after': per
                        }), 429
                        
                        # Add rate limit headers
                        response[0].headers['X-RateLimit-Limit'] = str(limit_val)
                        response[0].headers['X-RateLimit-Remaining'] = '0'
                        response[0].headers['Retry-After'] = str(per)
                        
                        return response
                    
                    # For successful requests, we'll add headers after the function executes
                    g._rate_limit_info = {
                        'limit': limit_val,
                        'remaining': remaining
                    }
                    
                except Exception as e:
                    logger.error(f"Rate limit check error: {e}")
                    # Continue without rate limiting on error
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Add rate limit headers to successful responses
            if hasattr(g, '_rate_limit_info') and hasattr(result, 'headers'):
                result.headers['X-RateLimit-Limit'] = str(g._rate_limit_info['limit'])
                result.headers['X-RateLimit-Remaining'] = str(g._rate_limit_info['remaining'])
            
            return result
        return rate_limit_wrapper
    return rate_limit_decorator


def unified_auth(
    required: bool = True,
    roles: Optional[list] = None,
    permissions: Optional[list] = None,
    allow_api_key: bool = True,
    require_admin: bool = False,
    ip_whitelist: Optional[list] = None
):
    """
    Unified authentication decorator
    Consolidates all authentication logic with flexible options
    
    Args:
        required: Whether authentication is required
        roles: List of required roles
        permissions: List of required permissions
        allow_api_key: Whether to allow API key authentication
        require_admin: Whether to require admin privileges
        ip_whitelist: List of allowed IP addresses
    """
    def auth_decorator(func):
        @wraps(func)
        def auth_wrapper(*args, **kwargs):
            # Check IP whitelist if specified
            if ip_whitelist:
                client_ip = request.remote_addr
                # X-Forwarded-For 헤더 확인 (프록시 환경)
                if request.headers.get('X-Forwarded-For'):
                    client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
                
                if client_ip not in ip_whitelist:
                    return jsonify({'error': 'Access denied from this IP'}), 403
            
            if not _registry._auth_manager:
                if required:
                    return jsonify({'error': 'Authentication not configured'}), 503
                return func(*args, **kwargs)
            
            # Extract authentication credentials
            auth_header = request.headers.get('Authorization', '')
            api_key = request.headers.get('X-API-Key', '')
            
            user_context = None
            
            # Try Bearer token authentication (JWT)
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    user_context = _registry._auth_manager.verify_token(token)
                except Exception as e:
                    logger.warning(f"Token verification failed: {e}")
                    if required:
                        return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Try ApiKey authentication (custom format)
            elif auth_header.lower().startswith('apikey '):
                api_key = auth_header.split(' ')[1]
                try:
                    client_name = _registry._auth_manager.verify_api_key(api_key)
                    if client_name:
                        user_context = {'client_name': client_name, 'api_key': True}
                except Exception as e:
                    logger.warning(f"API key verification failed: {e}")
                    if required:
                        return jsonify({'error': 'Invalid API key'}), 401
            
            # Try X-API-Key header authentication
            elif api_key and allow_api_key:
                try:
                    client_name = _registry._auth_manager.verify_api_key(api_key)
                    if client_name:
                        user_context = {'user_id': client_name, 'client_name': client_name, 'api_key': True}
                except Exception as e:
                    logger.warning(f"API key verification failed: {e}")
                    if required:
                        return jsonify({'error': 'Invalid API key'}), 401
            
            # Check if authentication is required
            if required and not user_context:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Please provide valid credentials'
                }), 401
            
            # Check admin requirement
            if require_admin and (not user_context or not user_context.get('is_admin')):
                return jsonify({'error': 'Admin access required'}), 403
            
            # Check roles if specified
            if user_context and roles:
                user_roles = user_context.get('roles', [])
                if not any(role in user_roles for role in roles):
                    return jsonify({'error': 'Insufficient privileges'}), 403
            
            # Check permissions if specified
            if user_context and permissions:
                user_permissions = user_context.get('permissions', [])
                if not any(perm in user_permissions for perm in permissions):
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Set user context in Flask g
            if user_context:
                g.auth_user = user_context  # For compatibility with existing code
                g.user_id = user_context.get('user_id')
                g.client_name = user_context.get('client_name')
                g.user_roles = user_context.get('roles', [])
                g.user_permissions = user_context.get('permissions', [])
                g.is_admin = user_context.get('is_admin', False)
            
            return func(*args, **kwargs)
        return auth_wrapper
    return auth_decorator


def unified_monitoring(
    track_performance: bool = True,
    track_response_size: bool = False,
    track_errors: bool = True,
    custom_metrics: Optional[Dict[str, Any]] = None
):
    """
    Unified monitoring decorator
    Consolidates all monitoring and metrics collection
    """
    def monitoring_decorator(func):
        @wraps(func)
        def monitoring_wrapper(*args, **kwargs):
            start_time = time.time()
            error_occurred = False
            response_size = 0
            
            try:
                result = func(*args, **kwargs)
                
                # Track response size if requested
                if track_response_size:
                    try:
                        if hasattr(result, 'get_data'):
                            response_size = len(result.get_data())
                        elif isinstance(result, str):
                            response_size = len(result.encode('utf-8'))
                        elif isinstance(result, (dict, list)):
                            response_size = len(json.dumps(result).encode('utf-8'))
                    except Exception:
                        response_size = 0
                
                return result
                
            except Exception as e:
                error_occurred = True
                if track_errors and _registry._metrics:
                    try:
                        _registry._metrics.increment_counter(
                            f"error.{func.__name__}",
                            tags={'error_type': type(e).__name__}
                        )
                    except Exception:
                        pass
                raise
            
            finally:
                # Track performance metrics
                if track_performance and _registry._metrics:
                    try:
                        execution_time = (time.time() - start_time) * 1000  # ms
                        
                        # Record timing
                        _registry._metrics.record_timing(
                            f"execution_time.{func.__name__}",
                            execution_time
                        )
                        
                        # Record response size
                        if track_response_size and response_size > 0:
                            _registry._metrics.record_histogram(
                                f"response_size.{func.__name__}",
                                response_size
                            )
                        
                        # Record success/failure
                        status = 'error' if error_occurred else 'success'
                        _registry._metrics.increment_counter(
                            f"requests.{func.__name__}.{status}"
                        )
                        
                        # Record custom metrics
                        if custom_metrics:
                            for metric_name, metric_value in custom_metrics.items():
                                _registry._metrics.record_gauge(
                                    f"custom.{metric_name}",
                                    metric_value
                                )
                    
                    except Exception as e:
                        logger.warning(f"Metrics recording error: {e}")
        
        return monitoring_wrapper
    return monitoring_decorator


def unified_validation(
    schema: Optional[Dict] = None,
    validate_json: bool = False,
    validate_params: Optional[Dict] = None,
    validate_headers: Optional[Dict] = None
):
    """
    Unified validation decorator
    Consolidates input validation logic
    """
    def validation_decorator(func):
        @wraps(func)
        def validation_wrapper(*args, **kwargs):
            errors = []
            
            # Validate JSON body
            if validate_json:
                try:
                    data = request.get_json()
                    if data is None:
                        errors.append("Valid JSON body required")
                except Exception:
                    errors.append("Invalid JSON format")
            
            # Validate URL parameters
            if validate_params:
                for param, requirements in validate_params.items():
                    value = request.args.get(param)
                    
                    if requirements.get('required', False) and not value:
                        errors.append(f"Required parameter '{param}' missing")
                    
                    if value and 'type' in requirements:
                        try:
                            if requirements['type'] == 'int':
                                int(value)
                            elif requirements['type'] == 'float':
                                float(value)
                        except ValueError:
                            errors.append(f"Parameter '{param}' must be {requirements['type']}")
            
            # Validate headers
            if validate_headers:
                for header, requirements in validate_headers.items():
                    value = request.headers.get(header)
                    
                    if requirements.get('required', False) and not value:
                        errors.append(f"Required header '{header}' missing")
            
            # Return validation errors
            if errors:
                return jsonify({
                    'error': 'Validation failed',
                    'validation_errors': errors,
                    'timestamp': datetime.now().isoformat()
                }), 400
            
            return func(*args, **kwargs)
        return validation_wrapper
    return validation_decorator


# Convenience decorators for common combinations
def api_endpoint(
    cache_ttl: int = 300,
    rate_limit_val: int = 1000,
    auth_required: bool = False,
    monitor: bool = True
):
    """
    Convenience decorator for standard API endpoints
    Combines caching, rate limiting, auth, and monitoring
    """
    def api_endpoint_decorator(func):
        # Apply decorators in reverse order (they wrap from inside out)
        decorated = func
        
        if monitor:
            decorated = unified_monitoring()(decorated)
        
        if auth_required:
            decorated = unified_auth(required=True)(decorated)
        
        decorated = unified_rate_limit(limit=rate_limit_val)(decorated)
        decorated = unified_cache(ttl=cache_ttl)(decorated)
        
        # Preserve the original function's metadata
        import functools
        decorated = functools.wraps(func)(decorated)
        
        return decorated
    return api_endpoint_decorator


def admin_endpoint(
    cache_ttl: int = 600,
    rate_limit_val: int = 100,
    required_roles: Optional[list] = None
):
    """
    Convenience decorator for admin endpoints
    Includes authentication with role checking
    """
    def admin_endpoint_decorator(func):
        decorated = func
        decorated = unified_monitoring()(decorated)
        decorated = unified_auth(required=True, roles=required_roles or ['admin'])(decorated)
        decorated = unified_rate_limit(limit=rate_limit_val)(decorated)
        decorated = unified_cache(ttl=cache_ttl, per_user=True)(decorated)
        
        # Preserve the original function's metadata
        import functools
        decorated = functools.wraps(func)(decorated)
        
        return decorated
    return admin_endpoint_decorator


def public_endpoint(
    cache_ttl: int = 300,
    rate_limit_val: int = 1000,
    track_size: bool = True
):
    """
    Convenience decorator for public endpoints
    Optimized for high-traffic public APIs
    """
    def public_endpoint_decorator(func):
        decorated = func
        decorated = unified_monitoring(track_response_size=track_size)(decorated)
        decorated = unified_rate_limit(limit=rate_limit_val)(decorated)
        decorated = unified_cache(ttl=cache_ttl)(decorated)
        
        # Preserve the original function's metadata
        import functools
        decorated = functools.wraps(func)(decorated)
        
        return decorated
    return public_endpoint_decorator


# Initialize function for the registry
def initialize_decorators(cache=None, auth_manager=None, rate_limiter=None, metrics=None):
    """Initialize the decorator registry with dependencies"""
    _registry.set_dependencies(cache, auth_manager, rate_limiter, metrics)
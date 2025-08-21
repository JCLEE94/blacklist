"""Exception classes for the blacklist system"""

from .auth_exceptions import AuthenticationError, AuthorizationError
from .base_exceptions import BlacklistError
from .config_exceptions import ConfigurationError, DependencyError
from .data_exceptions import DataError, DataProcessingError
from .error_utils import create_error_response, handle_exception, log_exception
from .infrastructure_exceptions import (CacheError, ConnectionError,
                                        DatabaseError)
from .service_exceptions import (MonitoringError, RateLimitError,
                                 ServiceUnavailableError)
from .validation_exceptions import ValidationError

__all__ = [
    # Base
    "BlacklistError",
    # Validation
    "ValidationError",
    # Infrastructure
    "CacheError",
    "DatabaseError",
    "ConnectionError",
    # Authentication/Authorization
    "AuthenticationError",
    "AuthorizationError",
    # Service
    "RateLimitError",
    "ServiceUnavailableError",
    "MonitoringError",
    # Data
    "DataProcessingError",
    "DataError",
    # Configuration
    "ConfigurationError",
    "DependencyError",
    # Utilities
    "handle_exception",
    "log_exception",
    "create_error_response",
]

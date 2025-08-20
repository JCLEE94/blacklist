"""Exception classes for the blacklist system"""

# Import all exception classes from their respective modules
from .auth_exceptions import AuthenticationError
from .auth_exceptions import AuthorizationError
from .base_exceptions import BlacklistError
from .config_exceptions import ConfigurationError
from .config_exceptions import DependencyError
from .data_exceptions import DataError
from .data_exceptions import DataProcessingError
from .error_utils import create_error_response
from .error_utils import handle_exception
from .error_utils import log_exception
from .infrastructure_exceptions import CacheError
from .infrastructure_exceptions import ConnectionError
from .infrastructure_exceptions import DatabaseError
from .service_exceptions import MonitoringError
from .service_exceptions import RateLimitError
from .service_exceptions import ServiceUnavailableError
from .validation_exceptions import ValidationError

# Export all classes for backward compatibility
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

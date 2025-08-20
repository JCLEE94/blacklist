"""Error handler package - modular structure"""

# Import all classes and functions from submodules for backward compatibility
from .context_manager import ErrorContext
from .core_handler import ErrorHandler
from .custom_errors import AuthenticationError
from .custom_errors import AuthorizationError
from .custom_errors import BaseError
from .custom_errors import CollectionError
from .custom_errors import DatabaseError
from .custom_errors import ExternalServiceError
from .custom_errors import ResourceNotFoundError
from .custom_errors import ValidationError
from .decorators import handle_api_errors
from .decorators import log_performance
from .decorators import retry_on_error
from .decorators import retry_on_failure
from .decorators import safe_execute
from .flask_integration import register_error_handlers
from .validators import validate_and_convert
from .validators import validate_ip_format
from .validators import validate_required_fields

# Create global error handler instance
error_handler = ErrorHandler()


# Export convenience functions that use the global instance
def handle_api_errors_global(func):
    """Global API error handler decorator"""
    return error_handler.handle_api_error(func)


def safe_execute_global(
    func,
    default=None,
    error_message="작업 실행 중 오류",
    raise_on_error=False,
):
    """Global safe execute function"""
    return error_handler.safe_execute(func, default, error_message, raise_on_error)


# Export all for backward compatibility
__all__ = [
    # Classes
    "BaseError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ExternalServiceError",
    "CollectionError",
    "DatabaseError",
    "ErrorHandler",
    "ErrorContext",
    # Functions
    "handle_api_errors",
    "safe_execute",
    "retry_on_error",
    "retry_on_failure",
    "log_performance",
    "register_error_handlers",
    "validate_required_fields",
    "validate_ip_format",
    "validate_and_convert",
    # Global instances
    "error_handler",
    "handle_api_errors_global",
    "safe_execute_global",
]

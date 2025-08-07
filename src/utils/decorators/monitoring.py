"""
Monitoring Decorators - Unified monitoring and metrics functionality
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Dict, Optional

from .registry import get_registry

logger = logging.getLogger(__name__)


def unified_monitoring(
    track_performance: bool = True,
    track_response_size: bool = False,
    track_errors: bool = True,
    custom_metrics: Optional[Dict[str, Any]] = None,
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
            registry = get_registry()

            try:
                result = func(*args, **kwargs)

                # Track response size if requested
                if track_response_size:
                    try:
                        if hasattr(result, "get_data"):
                            response_size = len(result.get_data())
                        elif isinstance(result, str):
                            response_size = len(result.encode("utf-8"))
                        elif isinstance(result, (dict, list)):
                            response_size = len(json.dumps(result).encode("utf-8"))
                    except Exception:
                        response_size = 0

                return result

            except Exception as e:
                error_occurred = True
                if track_errors and registry.metrics:
                    try:
                        registry.metrics.increment_counter(
                            f"error.{func.__name__}",
                            tags={"error_type": type(e).__name__},
                        )
                    except Exception:
                        pass
                raise

            finally:
                # Track performance metrics
                if track_performance and registry.metrics:
                    try:
                        execution_time = (time.time() - start_time) * 1000  # ms

                        # Record timing
                        registry.metrics.record_timing(
                            f"execution_time.{func.__name__}", execution_time
                        )

                        # Record response size
                        if track_response_size and response_size > 0:
                            registry.metrics.record_histogram(
                                f"response_size.{func.__name__}", response_size
                            )

                        # Record success/failure
                        status = "error" if error_occurred else "success"
                        registry.metrics.increment_counter(
                            f"requests.{func.__name__}.{status}"
                        )

                        # Record custom metrics
                        if custom_metrics:
                            for metric_name, metric_value in custom_metrics.items():
                                registry.metrics.record_gauge(
                                    f"custom.{metric_name}", metric_value
                                )

                    except Exception as e:
                        logger.warning(f"Metrics recording error: {e}")

        return monitoring_wrapper

    return monitoring_decorator

"""
Validation Decorators - Unified input validation functionality
"""

from flask import Flask, Blueprint, jsonify, request, redirect, url_for, render_template
import logging

logger = logging.getLogger(__name__)

from datetime import datetime
from functools import wraps
from typing import Dict, Optional


def unified_validation(
    schema: Optional[Dict] = None,
    validate_json: bool = False,
    validate_params: Optional[Dict] = None,
    validate_headers: Optional[Dict] = None,
):
    """
    Unified validation decorator
    Consolidates input validation logic
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
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

                    if requirements.get("required", False) and not value:
                        errors.append("Required parameter '{param}' missing")

                    if value and "type" in requirements:
                        try:
                            if requirements["type"] == "int":
                                int(value)
                            elif requirements["type"] == "float":
                                float(value)
                        except ValueError:
                            errors.append(
                                "Parameter '{param}' must be {requirements['type']}"
                            )

            # Validate headers
            if validate_headers:
                for header, requirements in validate_headers.items():
                    value = request.headers.get(header)

                    if requirements.get("required", False) and not value:
                        errors.append("Required header '{header}' missing")

            # Return validation errors
            if errors:
                return (
                    jsonify(
                        {
                            "error": "Validation failed",
                            "validation_errors": errors,
                            "timestamp": datetime.now().isoformat(),
                        }
                    ),
                    400,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator

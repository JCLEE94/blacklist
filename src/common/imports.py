#!/usr/bin/env python3
"""
Common Imports Module

Centralized import statements used across the project.
Reduces duplicate imports and provides consistent typing.

Sample input: Import this module instead of individual imports
Expected output: Consistent and clean import patterns
"""

# Standard library imports
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import requests

# Third-party imports
from flask import Blueprint, Flask, jsonify, redirect, render_template, request, url_for
from loguru import logger

# Project-specific imports (conditional)
try:
    from ..utils.structured_logging import get_logger
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent.parent))
    from utils.structured_logging import get_logger

# Export commonly used types
__all__ = [
    # Standard library
    "logging",
    "os",
    "datetime",
    "timedelta",
    "Path",
    # Typing
    "Any",
    "Dict",
    "List",
    "Optional",
    "Union",
    "Tuple",
    # Flask
    "Blueprint",
    "Flask",
    "jsonify",
    "request",
    "render_template",
    "redirect",
    "url_for",
    # Third-party
    "pd",
    "requests",
    "logger",
    # Project
    "get_logger",
]


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Import availability
    total_tests += 1
    try:
        test_imports = {
            "logging": logging,
            "datetime": datetime,
            "Dict": Dict,
            "Flask": Flask,
            "requests": requests,
        }

        for name, module in test_imports.items():
            if module is None:
                all_validation_failures.append(f"Import test: {name} is None")

    except Exception as e:
        all_validation_failures.append(f"Import test: Failed to access imports - {e}")

    # Test 2: Logger functionality
    total_tests += 1
    try:
        test_logger = get_logger(__name__)
        if not hasattr(test_logger, "info"):
            all_validation_failures.append("Logger test: Logger missing info method")
    except Exception as e:
        all_validation_failures.append(f"Logger test: Failed to create logger - {e}")

    # Test 3: Flask imports
    total_tests += 1
    try:
        test_bp = Blueprint("test", __name__)
        if test_bp.name != "test":
            all_validation_failures.append("Flask test: Blueprint creation failed")
    except Exception as e:
        all_validation_failures.append(f"Flask test: Failed to create Blueprint - {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Common imports module is validated and ready for use")
        sys.exit(0)

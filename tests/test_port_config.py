"""
Dynamic Test Port Configuration
Automatically detects running service port for tests
"""

import os
import requests
from typing import Optional


def detect_service_port() -> int:
    """Detect which port the service is running on"""
    # Common ports to check
    ports_to_check = [32542, 2542, 8080, 3000]

    for port in ports_to_check:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                return port
        except:
            continue

    # Default to Docker port if none detected
    return 32542


def get_test_base_url() -> str:
    """Get the base URL for tests"""
    port = detect_service_port()
    return f"http://localhost:{port}"


# Global configuration
TEST_SERVICE_PORT = detect_service_port()
TEST_BASE_URL = get_test_base_url()

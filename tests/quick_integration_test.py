#!/usr/bin/env python3
"""
Quick Integration Test for Blacklist Management System
Tests cookie-based authentication and basic functionality
"""

import json
import sys
import time
from datetime import datetime

import requests

# Test configuration
BASE_URL = "https://blacklist.jclee.me"
LOCAL_URL = "http://localhost:8541"


def print_test(test_name, passed, message=""):
    """Print test result with formatting"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")


def test_health_endpoint(base_url):
    """Test health endpoint"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        data = response.json()

        passed = (
            response.status_code == 200
            and data.get("status") == "healthy"
            and "details" in data
        )

        message = f"Status: {data.get('status')}, Total IPs: {data.get('details', {}).get('total_ips', 0)}"
        print_test("Health Endpoint", passed, message)
        return passed
    except Exception as e:
        print_test("Health Endpoint", False, str(e))
        return False


def test_collection_status(base_url):
    """Test collection status endpoint"""
    try:
        response = requests.get(f"{base_url}/api/collection/status", timeout=10)
        data = response.json()

        passed = response.status_code == 200
        enabled = data.get("collection_enabled", False)

        message = f"Collection Enabled: {enabled}"
        print_test("Collection Status", passed, message)
        return passed
    except Exception as e:
        print_test("Collection Status", False, str(e))
        return False


def test_fortigate_endpoint(base_url):
    """Test FortiGate endpoint"""
    try:
        response = requests.get(f"{base_url}/api/fortigate", timeout=10)
        data = response.json()

        passed = response.status_code == 200 and "status" in data and "ipList" in data

        ip_count = len(data.get("ipList", []))
        message = f"IP Count: {ip_count}"
        print_test("FortiGate Endpoint", passed, message)
        return passed
    except Exception as e:
        print_test("FortiGate Endpoint", False, str(e))
        return False


def test_regtech_trigger(base_url):
    """Test REGTECH collection trigger"""
    try:
        # Try to trigger collection
        response = requests.post(
            f"{base_url}/api/collection/regtech/trigger",
            json={"start_date": "20250101", "end_date": "20250117"},
            timeout=30,
        )

        # Accept both 200 (success) and 503 (already running) as valid
        passed = response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            message = (
                f"Success: {data.get('success')}, Message: {data.get('message', '')}"
            )
        else:
            message = f"Status Code: {response.status_code}"

        print_test("REGTECH Trigger", passed, message)
        return passed
    except Exception as e:
        print_test("REGTECH Trigger", False, str(e))
        return False


def test_secudium_disabled(base_url):
    """Test SECUDIUM is properly disabled"""
    try:
        response = requests.post(
            f"{base_url}/api/collection/secudium/trigger", timeout=10
        )

        # Should return 503 Service Unavailable
        passed = response.status_code == 503
        data = response.json() if response.text else {}

        message = (
            f"Status: {response.status_code}, Disabled: {data.get('disabled', False)}"
        )
        print_test("SECUDIUM Disabled", passed, message)
        return passed
    except Exception as e:
        print_test("SECUDIUM Disabled", False, str(e))
        return False


def test_cookie_configuration():
    """Test cookie configuration in local environment"""
    try:
        # This test checks if cookies are properly configured
        from src.core.regtech_collector import RegtechCollector

        collector = RegtechCollector("data/test")

        # Check all required cookies are present
        required_cookies = ["_ga", "regtech-front", "regtech-va", "_ga_7WRDYHF66J"]
        all_present = all(cookie in collector.cookies for cookie in required_cookies)

        # Check Bearer token format
        has_bearer = collector.cookies.get("regtech-va", "").startswith("Bearer")

        passed = all_present and has_bearer
        message = f"Cookies configured: {all_present}, Bearer token: {has_bearer}"
        print_test("Cookie Configuration", passed, message)
        return passed
    except ImportError:
        print_test(
            "Cookie Configuration",
            False,
            "Cannot import RegtechCollector (run from project root)",
        )
        return False
    except Exception as e:
        print_test("Cookie Configuration", False, str(e))
        return False


def run_integration_tests(base_url=BASE_URL):
    """Run all integration tests"""
    print(f"\n🧪 Running Integration Tests for {base_url}")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tests = [
        ("Health Check", lambda: test_health_endpoint(base_url)),
        ("Collection Status", lambda: test_collection_status(base_url)),
        ("FortiGate Endpoint", lambda: test_fortigate_endpoint(base_url)),
        ("REGTECH Trigger", lambda: test_regtech_trigger(base_url)),
        ("SECUDIUM Disabled", lambda: test_secudium_disabled(base_url)),
    ]

    # Add local-only tests if testing locally
    if "localhost" in base_url:
        tests.append(("Cookie Configuration", test_cookie_configuration))

    results = []
    for test_name, test_func in tests:
        results.append(test_func())
        time.sleep(1)  # Small delay between tests

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {success_rate:.1f}%")

    if success_rate == 100:
        print("\n🎉 All tests passed!")
    elif success_rate >= 80:
        print("\n⚠️  Most tests passed, but some issues detected")
    else:
        print("\n❌ Multiple test failures detected")

    return success_rate == 100


if __name__ == "__main__":
    # Check if running against local or production
    if len(sys.argv) > 1 and sys.argv[1] == "--local":
        base_url = LOCAL_URL
    else:
        base_url = LOCAL_URL

    success = run_integration_tests(base_url)
    sys.exit(0 if success else 1)

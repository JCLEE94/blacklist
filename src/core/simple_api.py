#!/usr/bin/env python3
"""
Simple API Routes for Minimal Flask App

Provides basic health check and simple API endpoints for minimal app configuration.
Used when full app features are not needed.

Links:
- Flask documentation: https://flask.palletsprojects.com/
- Basic health checks: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

Sample input: register_simple_api(flask_app)
Expected output: Basic API routes registered with /health endpoint
"""

import logging
from datetime import datetime
from flask import Flask, jsonify

logger = logging.getLogger(__name__)


def register_simple_api(app: Flask):
    """Register simple API routes with Flask app"""
    
    @app.route('/health')
    @app.route('/healthz')
    @app.route('/ready')
    def health_check():
        """Basic health check endpoint for load balancers and monitoring"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': 'minimal',
            'app': 'blacklist-minimal'
        })
    
    @app.route('/')
    def root():
        """Root endpoint with basic app information"""
        return jsonify({
            'name': 'Blacklist Management System',
            'version': 'minimal',
            'status': 'running',
            'endpoints': ['/health', '/api/collection/*']
        })
    
    @app.route('/api/status')
    def api_status():
        """Simple API status endpoint"""
        return jsonify({
            'api': 'active',
            'mode': 'minimal',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    logger.info("Simple API routes registered")


if __name__ == "__main__":
    import sys
    
    # Test validation
    validation_failures = []
    total_tests = 0
    
    # Test 1: Basic import
    total_tests += 1
    try:
        from flask import Flask
        test_app = Flask(__name__)
        register_simple_api(test_app)
    except Exception as e:
        validation_failures.append(f"Basic import test: {e}")
    
    # Test 2: Route registration
    total_tests += 1
    try:
        with test_app.test_client() as client:
            response = client.get('/health')
            if response.status_code != 200:
                validation_failures.append(f"Health endpoint: Expected 200, got {response.status_code}")
    except Exception as e:
        validation_failures.append(f"Route test: {e}")
    
    # Test 3: JSON response format
    total_tests += 1
    try:
        with test_app.test_client() as client:
            response = client.get('/health')
            data = response.get_json()
            if not data or 'status' not in data:
                validation_failures.append("Health endpoint: Missing status in JSON response")
    except Exception as e:
        validation_failures.append(f"JSON format test: {e}")
    
    # Final validation result
    if validation_failures:
        print(f"❌ VALIDATION FAILED - {len(validation_failures)} of {total_tests} tests failed:")
        for failure in validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Function is validated and formal tests can now be written")
        sys.exit(0)
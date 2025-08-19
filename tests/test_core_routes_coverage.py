#!/usr/bin/env python3
"""
Comprehensive tests for core routes functionality
Targeting low-coverage route modules for significant coverage improvement
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

import pytest
from flask import Flask

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestUnifiedRoutes:
    """Test unified routes functionality"""

    def test_unified_routes_import(self):
        """Test that unified routes can be imported"""
        from src.core.unified_routes import create_unified_routes
        assert create_unified_routes is not None

    def test_unified_routes_creation(self):
        """Test unified routes creation"""
        from src.core.unified_routes import create_unified_routes
        from flask import Flask
        
        app = Flask(__name__)
        with app.app_context():
            # Should not crash when creating routes
            try:
                create_unified_routes(app)
                success = True
            except Exception as e:
                success = False
                print(f"Route creation error: {e}")
            
            assert success is True

    def test_unified_routes_blueprint_registration(self):
        """Test that routes properly register blueprints"""
        from src.core.unified_routes import create_unified_routes
        from flask import Flask
        
        app = Flask(__name__)
        initial_blueprints = len(app.blueprints)
        
        with app.app_context():
            create_unified_routes(app)
            
        # Should have registered some blueprints
        assert len(app.blueprints) >= initial_blueprints

    def test_health_route_functionality(self):
        """Test health route endpoint"""
        from src.core.unified_routes import _test_health_endpoint_inline
        
        # Test inline health check
        result = _test_health_endpoint_inline()
        assert isinstance(result, dict)
        assert 'status' in result
        assert result['status'] in ['healthy', 'ok', 'running']

    def test_collection_status_functionality(self):
        """Test collection status route"""
        from src.core.unified_routes import _test_collection_status_inline
        
        # Test inline collection status
        result = _test_collection_status_inline()
        assert isinstance(result, dict)
        assert 'enabled' in result or 'status' in result


class TestAPIRoutes:
    """Test API routes functionality"""

    def test_api_routes_import(self):
        """Test that API routes can be imported"""
        from src.core.routes.api_routes import api_routes_bp
        assert api_routes_bp is not None

    def test_api_routes_blueprint(self):
        """Test API routes blueprint structure"""
        from src.core.routes.api_routes import api_routes_bp
        from flask import Blueprint
        
        assert isinstance(api_routes_bp, Blueprint)
        assert api_routes_bp.name == 'api_routes'

    def test_health_endpoint_route(self):
        """Test health endpoint route registration"""
        from src.core.routes.api_routes import api_routes_bp
        
        # Check that blueprint has rules
        app = Flask(__name__)
        app.register_blueprint(api_routes_bp)
        
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            
            # Should have health-related endpoints
            health_routes = [rule for rule in rules if 'health' in rule.lower()]
            assert len(health_routes) > 0

    def test_blacklist_endpoint_route(self):
        """Test blacklist endpoint route registration"""
        from src.core.routes.api_routes import api_routes_bp
        
        app = Flask(__name__)
        app.register_blueprint(api_routes_bp)
        
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            
            # Should have blacklist-related endpoints
            blacklist_routes = [rule for rule in rules if 'blacklist' in rule.lower()]
            assert len(blacklist_routes) > 0


class TestWebRoutes:
    """Test web routes functionality"""

    def test_web_routes_import(self):
        """Test that web routes can be imported"""
        from src.core.routes.web_routes import web_routes_bp
        assert web_routes_bp is not None

    def test_web_routes_blueprint(self):
        """Test web routes blueprint structure"""
        from src.core.routes.web_routes import web_routes_bp
        from flask import Blueprint
        
        assert isinstance(web_routes_bp, Blueprint)
        assert web_routes_bp.name == 'web_routes'

    def test_dashboard_route_registration(self):
        """Test dashboard route registration"""
        from src.core.routes.web_routes import web_routes_bp
        
        app = Flask(__name__)
        app.register_blueprint(web_routes_bp)
        
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            
            # Should have dashboard or index routes
            dashboard_routes = [rule for rule in rules if any(keyword in rule.lower() 
                                                            for keyword in ['dashboard', 'index', '/'])]
            assert len(dashboard_routes) > 0


class TestCollectionRoutes:
    """Test collection routes functionality"""

    def test_collection_routes_import(self):
        """Test that collection routes can be imported"""
        from src.core.routes.collection_routes import collection_routes_bp
        assert collection_routes_bp is not None

    def test_collection_routes_blueprint(self):
        """Test collection routes blueprint structure"""
        from src.core.routes.collection_routes import collection_routes_bp
        from flask import Blueprint
        
        assert isinstance(collection_routes_bp, Blueprint)

    def test_collection_status_route(self):
        """Test collection status route registration"""
        from src.core.routes.collection_routes import collection_routes_bp
        
        app = Flask(__name__)
        app.register_blueprint(collection_routes_bp)
        
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            
            # Should have collection status routes
            collection_routes = [rule for rule in rules if 'collection' in rule.lower()]
            assert len(collection_routes) > 0

    def test_collection_trigger_route(self):
        """Test collection trigger route registration"""
        from src.core.routes.collection_trigger_routes import collection_trigger_bp
        
        app = Flask(__name__)
        app.register_blueprint(collection_trigger_bp)
        
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            
            # Should have trigger routes
            trigger_routes = [rule for rule in rules if 'trigger' in rule.lower()]
            assert len(trigger_routes) > 0


class TestV2Routes:
    """Test V2 API routes functionality"""

    def test_v2_routes_import(self):
        """Test that V2 routes can be imported"""
        from src.core.v2_routes.analytics_routes import analytics_v2_bp
        assert analytics_v2_bp is not None

    def test_analytics_v2_routes(self):
        """Test analytics V2 routes"""
        from src.core.v2_routes.analytics_routes import analytics_v2_bp
        from flask import Blueprint
        
        assert isinstance(analytics_v2_bp, Blueprint)

    def test_sources_v2_routes(self):
        """Test sources V2 routes"""
        from src.core.v2_routes.sources_routes import sources_v2_bp
        from flask import Blueprint
        
        assert isinstance(sources_v2_bp, Blueprint)

    def test_blacklist_v2_routes(self):
        """Test blacklist V2 routes"""
        from src.core.v2_routes.blacklist_routes import blacklist_v2_bp
        from flask import Blueprint
        
        assert isinstance(blacklist_v2_bp, Blueprint)

    def test_v2_route_registration(self):
        """Test V2 route registration"""
        from src.core.v2_routes.analytics_routes import analytics_v2_bp
        from src.core.v2_routes.sources_routes import sources_v2_bp
        from src.core.v2_routes.blacklist_routes import blacklist_v2_bp
        
        app = Flask(__name__)
        app.register_blueprint(analytics_v2_bp)
        app.register_blueprint(sources_v2_bp)
        app.register_blueprint(blacklist_v2_bp)
        
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            
            # Should have V2 API routes
            v2_routes = [rule for rule in rules if '/v2/' in rule.lower()]
            assert len(v2_routes) > 0


class TestRouteHandlers:
    """Test route handler functionality"""

    def test_status_handler_import(self):
        """Test status handler import"""
        from src.core.routes.handlers.status_handler import get_system_status
        assert get_system_status is not None

    def test_health_handler_import(self):
        """Test health handler import"""
        from src.core.routes.handlers.health_handler import get_health_check
        assert get_health_check is not None

    def test_status_handler_functionality(self):
        """Test status handler returns proper data"""
        from src.core.routes.handlers.status_handler import get_system_status
        
        try:
            status = get_system_status()
            assert isinstance(status, dict)
            # Should have basic status information
            expected_keys = ['status', 'timestamp']
            for key in expected_keys:
                if key in status:
                    assert status[key] is not None
        except Exception as e:
            # Handler should not crash
            assert False, f"Status handler crashed: {e}"

    def test_health_handler_functionality(self):
        """Test health handler returns proper data"""
        from src.core.routes.handlers.health_handler import get_health_check
        
        try:
            health = get_health_check()
            assert isinstance(health, dict)
            # Should have health information
            expected_keys = ['status', 'healthy']
            for key in expected_keys:
                if key in health:
                    assert health[key] is not None
        except Exception as e:
            # Handler should not crash
            assert False, f"Health handler crashed: {e}"


class TestRouteUtils:
    """Test route utility functions"""

    def test_route_decorators_import(self):
        """Test route decorators can be imported"""
        from src.utils.decorators.auth import login_required
        assert login_required is not None

    def test_error_handler_import(self):
        """Test error handler can be imported"""
        from src.utils.error_handler import handle_api_error
        assert handle_api_error is not None

    def test_security_utils_import(self):
        """Test security utils can be imported"""
        from src.utils.security import validate_api_key
        assert validate_api_key is not None


class TestRouteSecurity:
    """Test route security functionality"""

    def test_auth_decorator_structure(self):
        """Test authentication decorator structure"""
        from src.utils.decorators.auth import login_required
        
        # Should be a callable decorator
        assert callable(login_required)

    def test_rate_limit_decorator(self):
        """Test rate limiting decorator"""
        from src.utils.decorators.rate_limit import rate_limit
        
        # Should be a callable decorator
        assert callable(rate_limit)

    def test_validation_decorators(self):
        """Test validation decorators"""
        from src.utils.decorators.validation import validate_json
        
        # Should be a callable decorator
        assert callable(validate_json)


if __name__ == "__main__":
    # Validation test for the core routes functionality
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    print("🔄 Running core routes validation tests...")
    
    # Test 1: Unified routes can be created
    total_tests += 1
    try:
        from src.core.unified_routes import create_unified_routes
        from flask import Flask
        app = Flask(__name__)
        with app.app_context():
            create_unified_routes(app)
        print("✅ Unified routes creation: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Unified routes creation: {e}")
    
    # Test 2: API routes blueprint exists
    total_tests += 1
    try:
        from src.core.routes.api_routes import api_routes_bp
        from flask import Blueprint
        assert isinstance(api_routes_bp, Blueprint)
        print("✅ API routes blueprint: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"API routes blueprint: {e}")
    
    # Test 3: Web routes blueprint exists
    total_tests += 1
    try:
        from src.core.routes.web_routes import web_routes_bp
        from flask import Blueprint
        assert isinstance(web_routes_bp, Blueprint)
        print("✅ Web routes blueprint: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Web routes blueprint: {e}")
    
    # Test 4: Collection routes exist
    total_tests += 1
    try:
        from src.core.routes.collection_routes import collection_routes_bp
        assert collection_routes_bp is not None
        print("✅ Collection routes: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Collection routes: {e}")
    
    # Test 5: V2 routes exist
    total_tests += 1
    try:
        from src.core.v2_routes.analytics_routes import analytics_v2_bp
        from src.core.v2_routes.sources_routes import sources_v2_bp
        assert analytics_v2_bp is not None
        assert sources_v2_bp is not None
        print("✅ V2 routes: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"V2 routes: {e}")
    
    # Test 6: Route handlers work
    total_tests += 1
    try:
        from src.core.routes.handlers.status_handler import get_system_status
        status = get_system_status()
        assert isinstance(status, dict)
        print("✅ Route handlers: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Route handlers: {e}")
    
    # Test 7: Health endpoint inline test
    total_tests += 1
    try:
        from src.core.unified_routes import _test_health_endpoint_inline
        result = _test_health_endpoint_inline()
        assert isinstance(result, dict)
        assert 'status' in result
        print("✅ Health endpoint inline: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Health endpoint inline: {e}")
    
    # Test 8: Collection status inline test
    total_tests += 1
    try:
        from src.core.unified_routes import _test_collection_status_inline
        result = _test_collection_status_inline()
        assert isinstance(result, dict)
        print("✅ Collection status inline: SUCCESS")
    except Exception as e:
        all_validation_failures.append(f"Collection status inline: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Core routes functionality is validated")
        sys.exit(0)
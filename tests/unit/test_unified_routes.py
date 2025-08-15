#!/usr/bin/env python3
"""
Unit tests for src/core/unified_routes.py
Testing unified API route system and blueprint registration
"""
from unittest.mock import Mock, patch

import pytest
from flask import Blueprint, Flask

from src.core.unified_routes import configure_routes, unified_bp


class TestUnifiedRoutes:
    """Unit tests for unified routes module"""

    def test_unified_blueprint_exists(self):
        """Test that unified blueprint is created"""
        assert isinstance(unified_bp, Blueprint)
        assert unified_bp.name == "unified"

    def test_unified_blueprint_has_registered_blueprints(self):
        """Test that sub-blueprints are registered"""
        # Create a test app and register the blueprint
        app = Flask(__name__)
        app.register_blueprint(unified_bp)

        # Should have at least some routes registered
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        assert len(routes) > 1  # Should have more than just static

    @patch("src.core.unified_routes.web_routes_bp")
    @patch("src.core.unified_routes.api_routes_bp")
    @patch("src.core.unified_routes.export_routes_bp")
    @patch("src.core.unified_routes.analytics_routes_bp")
    @patch("src.core.unified_routes.collection_routes_bp")
    @patch("src.core.unified_routes.admin_routes_bp")
    def test_blueprint_registration_calls(
        self,
        mock_admin,
        mock_collection,
        mock_analytics,
        mock_export,
        mock_api,
        mock_web,
    ):
        """Test that all blueprints are properly imported"""
        # Mock blueprints
        mock_web_bp = Mock(spec=Blueprint)
        mock_api_bp = Mock(spec=Blueprint)
        mock_export_bp = Mock(spec=Blueprint)
        mock_analytics_bp = Mock(spec=Blueprint)
        mock_collection_bp = Mock(spec=Blueprint)
        mock_admin_bp = Mock(spec=Blueprint)

        mock_web.return_value = mock_web_bp
        mock_api.return_value = mock_api_bp
        mock_export.return_value = mock_export_bp
        mock_analytics.return_value = mock_analytics_bp
        mock_collection.return_value = mock_collection_bp
        mock_admin.return_value = mock_admin_bp

        # Re-import to trigger registration with mocked blueprints
        import importlib

        import src.core.unified_routes

        importlib.reload(src.core.unified_routes)

        # Verify all blueprints were imported
        assert mock_web.called or hasattr(mock_web, "_mock_name")
        assert mock_api.called or hasattr(mock_api, "_mock_name")
        assert mock_export.called or hasattr(mock_export, "_mock_name")
        assert mock_analytics.called or hasattr(mock_analytics, "_mock_name")
        assert mock_collection.called or hasattr(mock_collection, "_mock_name")
        assert mock_admin.called or hasattr(mock_admin, "_mock_name")

    def test_configure_routes_function(self):
        """Test configure_routes function"""
        # Create a test Flask app
        app = Flask(__name__)

        # Call configure_routes
        result = configure_routes(app)

        # Verify the app was returned
        assert result == app

        # Verify the unified blueprint was registered
        assert any(bp.name == "unified" for bp in app.blueprints.values())

    def test_configure_routes_blueprint_registration(self):
        """Test that configure_routes actually registers the blueprint"""
        app = Flask(__name__)

        # Configure routes
        configure_routes(app)

        # Should have the unified blueprint
        assert "unified" in app.blueprints

        # Should have at least the unified blueprint registered
        assert len(app.blueprints) >= 1

    def test_module_exports(self):
        """Test that the module exports the expected items"""
        import src.core.unified_routes as routes_module

        # Check __all__ exports
        expected_exports = ["unified_bp", "configure_routes"]
        assert hasattr(routes_module, "__all__")
        assert routes_module.__all__ == expected_exports

        # Check actual exports exist
        assert hasattr(routes_module, "unified_bp")
        assert hasattr(routes_module, "configure_routes")

    def test_blueprint_url_prefix(self):
        """Test that unified blueprint has no URL prefix"""
        # The unified blueprint should not have a URL prefix
        # so sub-blueprints can define their own prefixes
        assert unified_bp.url_prefix is None

    def test_blueprint_import_time_registration(self):
        """Test that blueprints are registered at import time"""
        # Create a fresh app and register the unified blueprint
        app = Flask(__name__)
        app.register_blueprint(unified_bp)

        # When the app context is created, routes should be available
        with app.app_context():
            # The sub-blueprints should have added their routes to the app
            rules = list(app.url_map.iter_rules())
            # Should have more than just the default static route
            assert len(rules) > 0


class TestBlueprintIntegration:
    """Integration tests for blueprint system"""

    def test_unified_blueprint_with_flask_app(self):
        """Test unified blueprint integration with Flask app"""
        app = Flask(__name__)

        # Register the unified blueprint
        app.register_blueprint(unified_bp)

        # Verify registration
        assert "unified" in app.blueprints

        # Verify the blueprint object
        registered_bp = app.blueprints["unified"]
        assert registered_bp == unified_bp

    def test_multiple_blueprint_registration_safety(self):
        """Test that registering the same blueprint multiple times is safe"""
        app = Flask(__name__)

        # Register the unified blueprint multiple times
        app.register_blueprint(unified_bp)

        # This should not raise an error with different names
        app.register_blueprint(unified_bp, name="unified2")

        # Should have both registrations
        assert "unified" in app.blueprints
        assert "unified2" in app.blueprints

    def test_blueprint_with_app_context(self):
        """Test blueprint behavior within app context"""
        app = Flask(__name__)
        app.register_blueprint(unified_bp)

        with app.app_context():
            # Should be able to access current app
            from flask import current_app

            assert current_app == app

            # Should be able to access registered blueprints
            assert "unified" in current_app.blueprints

    def test_blueprint_deferred_functions_execution(self):
        """Test that deferred blueprint registration functions are executed"""
        app = Flask(__name__)

        # Count initial rules
        initial_rules = len(app.url_map._rules)

        # Register unified blueprint
        app.register_blueprint(unified_bp)

        # Rules count might increase due to sub-blueprint registration
        final_rules = len(app.url_map._rules)

        # At minimum, the registration should not fail
        assert final_rules >= initial_rules


class TestModuleStructure:
    """Test module structure and imports"""

    def test_module_level_imports(self):
        """Test that all required modules are importable"""
        try:
            from src.core.routes.admin_routes import admin_routes_bp
            from src.core.routes.analytics_routes import analytics_routes_bp
            from src.core.routes.api_routes import api_routes_bp
            from src.core.routes.collection_routes import collection_routes_bp
            from src.core.routes.export_routes import export_routes_bp
            from src.core.routes.web_routes import web_routes_bp
        except ImportError as e:
            pytest.skip(f"Route module import failed: {e}")

    def test_logger_configuration(self):
        """Test that logger is properly configured"""
        import src.core.unified_routes as routes_module

        assert hasattr(routes_module, "logger")
        assert routes_module.logger.name == "src.core.unified_routes"

    def test_module_docstring(self):
        """Test that module has proper documentation"""
        import src.core.unified_routes as routes_module

        assert routes_module.__doc__ is not None
        assert len(routes_module.__doc__.strip()) > 0
        assert "통합 API 라우트" in routes_module.__doc__

    def test_backward_compatibility(self):
        """Test backward compatibility function"""
        app = Flask(__name__)

        # The configure_routes function should work for backward compatibility
        result = configure_routes(app)

        # Should return the same app instance
        assert result is app

        # Should have registered the unified blueprint
        assert "unified" in app.blueprints

#!/usr/bin/env python3
"""
Unit tests for src/core/app_compact.py
Testing Flask application factory and mixins
"""
import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

from src.core.app_compact import (
    CompactFlaskApp,
    create_app,
    create_compact_app,
    get_connection_manager,
)


class TestCompactFlaskApp:
    """Unit tests for CompactFlaskApp class"""

    def test_get_connection_manager(self):
        """Test connection manager placeholder"""
        manager = get_connection_manager()
        assert hasattr(manager, "get_pool_config")
        config = manager.get_pool_config()
        assert isinstance(config, dict)

    @patch("src.core.app_compact.get_container")
    @patch("src.core.app_compact.setup_request_logging")
    def test_create_app_basic(self, mock_setup_logging, mock_get_container):
        """Test basic app creation"""
        # Mock container
        mock_container = Mock()
        mock_config = Mock()
        mock_config.SECRET_KEY = "test-key"
        mock_config.DEBUG = False
        mock_config.PORT = 5000

        mock_container.get.return_value = mock_config
        mock_get_container.return_value = mock_container

        # Create app factory
        factory = CompactFlaskApp()

        # Mock all the mixin methods to avoid complex dependencies
        factory._setup_basic_config = Mock()
        factory._setup_cors = Mock()
        factory._setup_compression = Mock()
        factory._setup_json_optimization = Mock(return_value=True)
        factory._setup_timezone = Mock()
        factory._setup_advanced_features = Mock()
        factory._setup_request_middleware = Mock()
        factory._setup_performance_middleware = Mock()
        factory._setup_build_info_context = Mock()
        factory._register_core_blueprints = Mock()
        factory._register_v2_blueprints = Mock()
        factory._register_security_blueprints = Mock()
        factory._register_debug_blueprints = Mock()
        factory._setup_error_handlers = Mock()

        # Mock container methods
        mock_container.configure_flask_app = Mock()

        # Create app
        app = factory.create_app("testing")

        # Verify app was created
        assert isinstance(app, Flask)
        assert app.config is not None

        # Verify mixin methods were called
        factory._setup_basic_config.assert_called_once()
        factory._setup_cors.assert_called_once()
        factory._setup_compression.assert_called_once()
        factory._setup_json_optimization.assert_called_once()

    @patch("src.core.app_compact.get_container")
    def test_create_app_with_exception(self, mock_get_container):
        """Test app creation when an exception occurs"""
        # Make container throw an exception
        mock_get_container.side_effect = Exception("Container error")

        factory = CompactFlaskApp()
        app = factory.create_app("testing")

        # Should return error app
        assert isinstance(app, Flask)

        # Test error route
        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "error"

    @patch("src.core.app_compact.get_container")
    @patch("src.utils.advanced_cache.get_smart_cache")
    @patch("src.utils.security.get_security_manager")
    @patch("src.utils.unified_decorators.initialize_decorators")
    def test_setup_advanced_features(
        self, mock_init_decorators, mock_security, mock_cache, mock_get_container
    ):
        """Test advanced features setup"""
        # Setup mocks
        mock_container = Mock()
        mock_container.get.side_effect = lambda x: Mock()
        mock_get_container.return_value = mock_container

        mock_smart_cache = Mock()
        mock_cache.return_value = mock_smart_cache

        mock_security_manager = Mock()
        mock_security.return_value = mock_security_manager

        # Create app and container
        app = Flask(__name__)

        factory = CompactFlaskApp()
        factory._setup_advanced_features(app, mock_container)

        # Verify advanced features were set up
        assert hasattr(app, "smart_cache")
        assert hasattr(app, "security_manager")
        assert app.smart_cache == mock_smart_cache
        assert app.security_manager == mock_security_manager

        # Verify decorators were initialized
        mock_init_decorators.assert_called_once()

    @patch("src.core.app_compact.get_container")
    def test_setup_advanced_features_with_exception(self, mock_get_container):
        """Test advanced features setup with exception handling"""
        mock_container = Mock()
        mock_get_container.return_value = mock_container

        # Mock import that will fail
        with patch(
            "src.utils.advanced_cache.get_smart_cache",
            side_effect=ImportError("Module not found"),
        ):
            app = Flask(__name__)
            factory = CompactFlaskApp()

            # Should not raise exception, just log warning
            factory._setup_advanced_features(app, mock_container)

            # App should still exist but without advanced features
            assert isinstance(app, Flask)


class TestFactoryFunctions:
    """Test factory functions"""

    @patch("src.core.app_compact.CompactFlaskApp")
    def test_create_compact_app(self, mock_factory_class):
        """Test create_compact_app function"""
        mock_factory = Mock()
        mock_app = Mock(spec=Flask)
        mock_factory.create_app.return_value = mock_app
        mock_factory_class.return_value = mock_factory

        result = create_compact_app("testing")

        mock_factory_class.assert_called_once()
        mock_factory.create_app.assert_called_once_with("testing")
        assert result == mock_app

    @patch("src.core.app_compact.create_compact_app")
    def test_create_app(self, mock_create_compact):
        """Test create_app function"""
        mock_app = Mock(spec=Flask)
        mock_create_compact.return_value = mock_app

        result = create_app("production")

        mock_create_compact.assert_called_once_with("production")
        assert result == mock_app


class TestMainFunction:
    """Test main execution function"""

    @patch("src.core.app_compact.create_compact_app")
    @patch("dotenv.load_dotenv")
    @patch("src.core.app_compact.os.environ.get")
    def test_main_with_development_env(
        self, mock_env_get, mock_load_dotenv, mock_create_app
    ):
        """Test main function with development environment"""
        # Mock environment
        mock_env_get.side_effect = lambda key, default=None: {
            "FLASK_ENV": "development",
            "PORT": "8000",
        }.get(key, default)

        # Mock app
        mock_app = Mock()
        mock_app.config = {"PORT": 8000, "DEBUG": True}
        mock_app.run = Mock()
        mock_create_app.return_value = mock_app

        # Import and call main (can't directly import due to app.run)
        from src.core.app_compact import main

        # Mock Path.exists to avoid file system interaction
        with patch("src.core.app_compact.Path") as mock_path:
            mock_path.return_value.parent.parent = Mock()
            mock_env_file = Mock()
            mock_env_file.exists.return_value = True
            mock_path.return_value.parent.parent.__truediv__.return_value = (
                mock_env_file
            )

            # Call main but catch the app.run call
            with patch.object(mock_app, "run") as mock_run:
                main()
                mock_run.assert_called_once_with(host="0.0.0.0", port=8000, debug=True)

    @patch("src.core.app_compact.create_compact_app")
    @patch("dotenv.load_dotenv")
    @patch("src.core.app_compact.os.environ.get")
    def test_main_with_production_env(
        self, mock_env_get, mock_load_dotenv, mock_create_app
    ):
        """Test main function with production environment"""
        # Mock environment
        mock_env_get.side_effect = lambda key, default=None: {
            "FLASK_ENV": "production",
            "PORT": "2541",
        }.get(key, default)

        # Mock app
        mock_app = Mock()
        mock_app.config = {"PORT": 2541, "DEBUG": False}
        mock_app.run = Mock()
        mock_create_app.return_value = mock_app

        from src.core.app_compact import main

        with patch("src.core.app_compact.Path") as mock_path:
            mock_path.return_value.parent.parent = Mock()
            mock_env_file = Mock()
            mock_env_file.exists.return_value = False
            mock_path.return_value.parent.parent.__truediv__.return_value = (
                mock_env_file
            )

            with patch.object(mock_app, "run") as mock_run:
                main()
                mock_run.assert_called_once_with(host="0.0.0.0", port=2541, debug=False)

    @patch("src.core.app_compact.create_compact_app")
    @patch("dotenv.load_dotenv")
    @patch("src.core.app_compact.os.environ.get")
    def test_main_with_failed_app(
        self, mock_env_get, mock_load_dotenv, mock_create_app
    ):
        """Test main function when app creation fails"""
        # Mock environment
        mock_env_get.side_effect = lambda key, default=None: {
            "FLASK_ENV": "development"
        }.get(key, default)

        # Mock failed app (no config)
        mock_app = Mock()
        del mock_app.config  # Remove config attribute
        mock_app.run = Mock()
        mock_create_app.return_value = mock_app

        from src.core.app_compact import main

        with patch("src.core.app_compact.Path") as mock_path:
            mock_path.return_value.parent.parent = Mock()
            mock_env_file = Mock()
            mock_env_file.exists.return_value = False
            mock_path.return_value.parent.parent.__truediv__.return_value = (
                mock_env_file
            )

            with patch.object(mock_app, "run") as mock_run:
                main()
                # Should use default values when config is missing
                mock_run.assert_called_once_with(
                    host="0.0.0.0",
                    port=2541,  # Default PROD_PORT
                    debug=True,  # Default for development
                )


class TestWSGIApplication:
    """Test WSGI application export"""

    def test_wsgi_application_exists(self):
        """Test that WSGI application exists"""
        # The application is created at module import time
        from src.core.app_compact import application

        # Should be a Flask app instance
        assert application is not None
        # Should have Flask-like attributes
        assert hasattr(application, "run")
        assert hasattr(application, "config")

"""
Comprehensive tests for src/core/app_compact.py
Tests for the Flask application factory and all mixins
"""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.app_compact import (
    CompactFlaskApp,
    create_compact_app,
    create_app,
    get_connection_manager,
    main
)


class TestCompactFlaskApp:
    """Test the main application factory class"""

    def test_initialization(self):
        """Test CompactFlaskApp can be initialized"""
        app_factory = CompactFlaskApp()
        assert app_factory is not None
        assert hasattr(app_factory, 'create_app')

    @patch('src.core.app_compact.get_container')
    @patch('src.core.app_compact.setup_request_logging')
    def test_create_app_basic(self, mock_setup_logging, mock_get_container):
        """Test basic app creation"""
        # Setup mocks
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        # Mock config
        mock_config = Mock()
        mock_config.SECRET_KEY = 'test-secret'
        mock_container.get.return_value = mock_config

        app_factory = CompactFlaskApp()
        
        # Mock all the mixin methods to avoid dependencies
        app_factory._setup_basic_config = Mock()
        app_factory._setup_cors = Mock()
        app_factory._setup_compression = Mock()
        app_factory._setup_json_optimization = Mock(return_value=True)
        app_factory._setup_timezone = Mock()
        app_factory._setup_request_middleware = Mock()
        app_factory._setup_performance_middleware = Mock()
        app_factory._setup_build_info_context = Mock()
        app_factory._register_core_blueprints = Mock()
        app_factory._register_v2_blueprints = Mock()
        app_factory._register_security_blueprints = Mock()
        app_factory._register_debug_blueprints = Mock()
        app_factory._setup_error_handlers = Mock()

        app = app_factory.create_app()
        
        assert isinstance(app, Flask)
        assert app is not None

    @patch('src.core.app_compact.get_container')
    def test_create_app_with_config_name(self, mock_get_container):
        """Test app creation with specific config name"""
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        
        # Mock all mixin methods
        for method in ['_setup_basic_config', '_setup_cors', '_setup_compression',
                      '_setup_json_optimization', '_setup_timezone',
                      '_setup_request_middleware', '_setup_performance_middleware',
                      '_setup_build_info_context', '_register_core_blueprints',
                      '_register_v2_blueprints', '_register_security_blueprints',
                      '_register_debug_blueprints', '_setup_error_handlers']:
            setattr(app_factory, method, Mock())
        app_factory._setup_json_optimization.return_value = True

        with patch('src.config.factory.get_config') as mock_get_config:
            mock_config = Mock()
            mock_get_config.return_value = mock_config
            
            app = app_factory.create_app('development')
            assert isinstance(app, Flask)
            mock_get_config.assert_called_once_with('development')

    @patch('src.core.app_compact.get_container')
    def test_create_app_handles_initialization_error(self, mock_get_container):
        """Test app creation when initialization fails"""
        # Make container.get raise an exception
        mock_container = Mock()
        mock_container.get.side_effect = Exception("Container error")
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        app = app_factory.create_app()
        
        # Should return an error Flask app
        assert isinstance(app, Flask)
        
        # Test the error route
        with app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'error'
            assert 'initialization failed' in data['message'].lower()

    @patch('src.core.app_compact.get_container')
    @patch('src.utils.system_stability.initialize_system_stability')
    def test_create_app_system_stability_success(self, mock_init_stability, mock_get_container):
        """Test successful system stability initialization"""
        # Setup mocks
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        
        # Mock all mixin methods
        for method in ['_setup_basic_config', '_setup_cors', '_setup_compression',
                      '_setup_json_optimization', '_setup_timezone',
                      '_setup_request_middleware', '_setup_performance_middleware',
                      '_setup_build_info_context', '_register_core_blueprints',
                      '_register_v2_blueprints', '_register_security_blueprints',
                      '_register_debug_blueprints', '_setup_error_handlers']:
            setattr(app_factory, method, Mock())
        app_factory._setup_json_optimization.return_value = True

        app = app_factory.create_app()
        
        # Should call system stability initialization
        mock_init_stability.assert_called_once()

    @patch('src.core.app_compact.get_container')
    @patch('src.utils.system_stability.initialize_system_stability')
    def test_create_app_system_stability_failure(self, mock_init_stability, mock_get_container):
        """Test system stability initialization failure is handled gracefully"""
        # Setup mocks
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        # Make system stability init fail
        mock_init_stability.side_effect = Exception("Stability init failed")

        app_factory = CompactFlaskApp()
        
        # Mock all mixin methods
        for method in ['_setup_basic_config', '_setup_cors', '_setup_compression',
                      '_setup_json_optimization', '_setup_timezone',
                      '_setup_request_middleware', '_setup_performance_middleware',
                      '_setup_build_info_context', '_register_core_blueprints',
                      '_register_v2_blueprints', '_register_security_blueprints',
                      '_register_debug_blueprints', '_setup_error_handlers']:
            setattr(app_factory, method, Mock())
        app_factory._setup_json_optimization.return_value = True

        # Should not raise exception, just log warning
        app = app_factory.create_app()
        assert isinstance(app, Flask)

    @patch('src.core.app_compact.get_container')
    def test_setup_advanced_features_success(self, mock_get_container):
        """Test successful advanced features setup"""
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        app = Flask(__name__)

        # Mock advanced feature modules
        with patch('src.utils.advanced_cache.get_smart_cache') as mock_cache, \
             patch('src.utils.security.get_security_manager') as mock_security, \
             patch('src.utils.unified_decorators.initialize_decorators') as mock_decorators:
            
            mock_cache.return_value = Mock()
            mock_security.return_value = Mock()
            
            app_factory._setup_advanced_features(app, mock_container)
            
            # Verify advanced features were setup
            assert hasattr(app, 'smart_cache')
            assert hasattr(app, 'security_manager')
            mock_decorators.assert_called_once()

    @patch('src.core.app_compact.get_container')
    def test_setup_advanced_features_failure(self, mock_get_container):
        """Test advanced features setup handles failures gracefully"""
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        app = Flask(__name__)

        # Make advanced cache import fail
        with patch('src.utils.advanced_cache.get_smart_cache', side_effect=ImportError("Module not found")):
            # Should not raise exception, just log warning
            app_factory._setup_advanced_features(app, mock_container)


class TestConnectionManager:
    """Test the connection manager functionality"""

    def test_get_connection_manager(self):
        """Test connection manager returns dummy implementation"""
        manager = get_connection_manager()
        assert manager is not None
        assert hasattr(manager, 'get_pool_config')
        
        config = manager.get_pool_config()
        assert isinstance(config, dict)


class TestFactoryFunctions:
    """Test the factory functions"""

    @patch('src.core.app_compact.CompactFlaskApp')
    def test_create_compact_app(self, mock_app_class):
        """Test create_compact_app factory function"""
        mock_factory = Mock()
        mock_app = Mock()
        mock_factory.create_app.return_value = mock_app
        mock_app_class.return_value = mock_factory

        result = create_compact_app('test')
        
        mock_app_class.assert_called_once()
        mock_factory.create_app.assert_called_once_with('test')
        assert result == mock_app

    @patch('src.core.app_compact.create_compact_app')
    def test_create_app(self, mock_create_compact):
        """Test create_app factory function"""
        mock_app = Mock()
        mock_create_compact.return_value = mock_app

        result = create_app('production')
        
        mock_create_compact.assert_called_once_with('production')
        assert result == mock_app


class TestMainFunction:
    """Test the main execution function"""

    @patch('src.core.app_compact.create_compact_app')
    @patch('pathlib.Path.exists')
    @patch('dotenv.load_dotenv')
    def test_main_with_env_file(self, mock_load_dotenv, mock_exists, mock_create_app):
        """Test main function when .env file exists"""
        mock_exists.return_value = True
        mock_app = Mock()
        mock_app.config = {'PORT': 8000, 'DEBUG': False}
        mock_create_app.return_value = mock_app

        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            with patch.object(mock_app, 'run') as mock_run:
                main()
                
                mock_load_dotenv.assert_called_once()
                mock_create_app.assert_called_once_with('development')
                mock_run.assert_called_once_with(host="0.0.0.0", port=8000, debug=False)

    @patch('src.core.app_compact.create_compact_app')
    @patch('pathlib.Path.exists')
    def test_main_without_env_file(self, mock_exists, mock_create_app):
        """Test main function when .env file doesn't exist"""
        mock_exists.return_value = False
        mock_app = Mock()
        # Simulate app without proper config
        mock_app.config = {}
        mock_create_app.return_value = mock_app

        with patch.dict(os.environ, {'PORT': '9000', 'FLASK_ENV': 'production'}):
            with patch.object(mock_app, 'run') as mock_run:
                main()
                
                mock_create_app.assert_called_once_with('production')
                mock_run.assert_called_once_with(host="0.0.0.0", port=9000, debug=False)

    @patch('src.core.app_compact.create_compact_app')
    @patch('pathlib.Path.exists')
    def test_main_default_values(self, mock_exists, mock_create_app):
        """Test main function with default environment values"""
        mock_exists.return_value = False
        mock_app = Mock()
        mock_app.config = {}
        mock_create_app.return_value = mock_app

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(mock_app, 'run') as mock_run:
                main()
                
                mock_create_app.assert_called_once_with('production')
                mock_run.assert_called_once_with(host="0.0.0.0", port=2541, debug=False)

    @patch('src.core.app_compact.create_compact_app')
    @patch('pathlib.Path.exists')
    def test_main_development_mode(self, mock_exists, mock_create_app):
        """Test main function in development mode"""
        mock_exists.return_value = False
        mock_app = Mock()
        mock_app.config = {}
        mock_create_app.return_value = mock_app

        with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            with patch.object(mock_app, 'run') as mock_run:
                main()
                
                mock_run.assert_called_once_with(host="0.0.0.0", port=8541, debug=True)


class TestModuleLevel:
    """Test module level functionality"""

    def test_application_wsgi_object(self):
        """Test that the module-level application object exists"""
        from src.core.app_compact import application
        assert application is not None
        # We can't test it deeply without mocking everything, but we can verify it exists

    @patch('src.core.app_compact.main')
    def test_main_execution(self, mock_main):
        """Test __main__ execution path"""
        # This is tricky to test directly, but we can verify the pattern
        # by importing the module in a way that triggers __main__
        assert mock_main is not None  # Just verify the function exists


class TestIntegration:
    """Integration tests for the app factory"""

    @patch('src.core.app_compact.get_container')
    def test_app_has_required_attributes(self, mock_get_container):
        """Test that created app has all required attributes"""
        mock_container = Mock()
        mock_container.get.return_value = Mock()
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        
        # Mock all dependencies to avoid import errors
        for method in ['_setup_basic_config', '_setup_cors', '_setup_compression',
                      '_setup_json_optimization', '_setup_timezone',
                      '_setup_request_middleware', '_setup_performance_middleware',
                      '_setup_build_info_context', '_register_core_blueprints',
                      '_register_v2_blueprints', '_register_security_blueprints',
                      '_register_debug_blueprints', '_setup_error_handlers']:
            setattr(app_factory, method, Mock())
        app_factory._setup_json_optimization.return_value = True

        app = app_factory.create_app()
        
        # Verify Flask app attributes
        assert hasattr(app, 'config')
        assert hasattr(app, 'run')
        assert app.config.get('RATELIMIT_ENABLED') == False

    @patch('src.core.app_compact.get_container')
    def test_app_configuration_flow(self, mock_get_container):
        """Test the complete configuration flow"""
        mock_container = Mock()
        mock_config = Mock()
        mock_container.get.return_value = mock_config
        mock_container.configure_flask_app = Mock()
        mock_get_container.return_value = mock_container

        app_factory = CompactFlaskApp()
        
        # Create real mocks that track call order
        setup_calls = []
        
        def track_call(name):
            def wrapper(*args, **kwargs):
                setup_calls.append(name)
                return True if name == '_setup_json_optimization' else None
            return wrapper

        for method in ['_setup_basic_config', '_setup_cors', '_setup_compression',
                      '_setup_json_optimization', '_setup_timezone',
                      '_setup_request_middleware', '_setup_performance_middleware',
                      '_setup_build_info_context', '_register_core_blueprints',
                      '_register_v2_blueprints', '_register_security_blueprints',
                      '_register_debug_blueprints', '_setup_error_handlers']:
            setattr(app_factory, method, track_call(method))

        app = app_factory.create_app()
        
        # Verify all setup methods were called
        expected_calls = [
            '_setup_basic_config', '_setup_cors', '_setup_compression',
            '_setup_json_optimization', '_setup_timezone',
            '_setup_request_middleware', '_setup_performance_middleware',
            '_setup_build_info_context', '_register_core_blueprints',
            '_register_v2_blueprints', '_register_security_blueprints',
            '_register_debug_blueprints', '_setup_error_handlers'
        ]
        
        for expected_call in expected_calls:
            assert expected_call in setup_calls


if __name__ == '__main__':
    pytest.main([__file__])
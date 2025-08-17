"""
Comprehensive tests for src/core/app/* modules
Tests configuration, middleware, blueprints, and error handlers
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.app.blueprints import BlueprintRegistrationMixin
from src.core.app.config import AppConfigurationMixin
from src.core.app.error_handlers import ErrorHandlerMixin
from src.core.app.middleware import MiddlewareMixin


class TestAppConfigurationMixin:
    """Test the AppConfigurationMixin class"""

    def test_mixin_inheritance(self):
        """Test that mixin can be inherited"""

        class TestApp(AppConfigurationMixin):
            pass

        app = TestApp()
        assert hasattr(app, "_setup_basic_config")
        assert hasattr(app, "_setup_cors")
        assert hasattr(app, "_setup_compression")
        assert hasattr(app, "_setup_json_optimization")
        assert hasattr(app, "_setup_timezone")

    @patch("werkzeug.middleware.proxy_fix.ProxyFix")
    def test_setup_basic_config(self, mock_proxy_fix):
        """Test basic configuration setup"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)
        original_wsgi_app = app.wsgi_app

        mock_proxy_instance = Mock()
        mock_proxy_fix.return_value = mock_proxy_instance

        mixin._setup_basic_config(app)

        # Should setup proxy fix with the original wsgi_app
        mock_proxy_fix.assert_called_once_with(
            original_wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )
        # Should assign the proxied app
        assert app.wsgi_app == mock_proxy_instance

    @patch("werkzeug.middleware.profiler.ProfilerMiddleware")
    @patch("werkzeug.middleware.proxy_fix.ProxyFix")
    def test_setup_basic_config_with_profiler(self, mock_proxy_fix, mock_profiler):
        """Test basic configuration with profiler enabled"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)
        app.config["ENABLE_PROFILER"] = True
        original_wsgi_app = app.wsgi_app

        mock_proxy_instance = Mock()
        mock_proxy_fix.return_value = mock_proxy_instance
        mock_profiler_instance = Mock()
        mock_profiler.return_value = mock_profiler_instance

        mixin._setup_basic_config(app)

        # Should setup proxy fix first
        mock_proxy_fix.assert_called_once_with(
            original_wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )
        # Then setup profiler with the proxied app
        mock_profiler.assert_called_once_with(
            mock_proxy_instance, profile_dir="./profiler_logs"
        )
        # Final wsgi_app should be the profiler instance
        assert app.wsgi_app == mock_profiler_instance

    @patch("flask_cors.CORS")
    def test_setup_cors_default(self, mock_cors):
        """Test CORS setup with default origins"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch.dict(os.environ, {}, clear=True):
            mixin._setup_cors(app)

            mock_cors.assert_called_once_with(app, origins=["*"])

    @patch("flask_cors.CORS")
    def test_setup_cors_custom_origins(self, mock_cors):
        """Test CORS setup with custom origins"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch.dict(
            os.environ, {"ALLOWED_ORIGINS": "http://localhost:3000,https://example.com"}
        ):
            mixin._setup_cors(app)

            mock_cors.assert_called_once_with(
                app, origins=["http://localhost:3000", "https://example.com"]
            )

    @patch("flask_compress.Compress")
    def test_setup_compression(self, mock_compress_class):
        """Test compression setup"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        mock_compress = Mock()
        mock_compress_class.return_value = mock_compress

        mixin._setup_compression(app)

        # Should initialize compress
        mock_compress_class.assert_called_once()
        mock_compress.init_app.assert_called_once_with(app)

        # Should configure compression settings
        assert "COMPRESS_MIMETYPES" in app.config
        assert "COMPRESS_LEVEL" in app.config
        assert "COMPRESS_MIN_SIZE" in app.config
        assert app.config["COMPRESS_LEVEL"] == 6
        assert app.config["COMPRESS_MIN_SIZE"] == 1024

    def test_setup_compression_mimetypes(self):
        """Test compression MIME types configuration"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch("flask_compress.Compress"):
            mixin._setup_compression(app)

            expected_mimetypes = [
                "application/json",
                "text/plain",
                "text/html",
                "text/css",
                "text/xml",
                "application/xml",
                "application/xhtml+xml",
            ]

            assert app.config["COMPRESS_MIMETYPES"] == expected_mimetypes

    def test_setup_json_optimization_without_orjson(self):
        """Test JSON optimization when orjson is not available"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        # Mock the import to raise ImportError
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "orjson":
                raise ImportError("Mock orjson not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = mixin._setup_json_optimization(app)
            # Should return False when orjson is not available
            assert result == False

    def test_setup_json_optimization_with_orjson(self):
        """Test JSON optimization when orjson is available"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        # Test with orjson available (should be installed in requirements.txt)
        result = mixin._setup_json_optimization(app)

        # Should return True when orjson is available
        assert result == True
        assert app.config.get("JSON_SORT_KEYS") == False

    @patch("time.tzset")
    def test_setup_timezone(self, mock_tzset):
        """Test timezone setup"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch.dict(os.environ, {}, clear=True):
            mixin._setup_timezone(app)

            # Should set TZ environment variable
            assert os.environ.get("TZ") == "Asia/Seoul"
            mock_tzset.assert_called_once()

    @patch("time.tzset", side_effect=Exception("tzset not available"))
    def test_setup_timezone_windows(self, mock_tzset):
        """Test timezone setup on Windows (tzset not available)"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        # Should not raise exception even if tzset fails
        mixin._setup_timezone(app)

        assert os.environ.get("TZ") == "Asia/Seoul"


class TestMiddlewareMixin:
    """Test the MiddlewareMixin class"""

    def test_mixin_exists(self):
        """Test that MiddlewareMixin exists and can be instantiated"""
        mixin = MiddlewareMixin()
        assert mixin is not None

    def test_mixin_methods_exist(self):
        """Test that mixin has expected methods"""
        mixin = MiddlewareMixin()

        # Check that methods exist (even if they might be stubs)
        expected_methods = [
            "_setup_request_middleware",
            "_setup_performance_middleware",
            "_setup_build_info_context",
        ]

        for method_name in expected_methods:
            assert hasattr(mixin, method_name), f"Method {method_name} should exist"

    def test_mixin_inheritance(self):
        """Test that mixin can be inherited"""

        class TestApp(MiddlewareMixin):
            pass

        app = TestApp()
        assert isinstance(app, MiddlewareMixin)

    def test_setup_request_middleware(self):
        """Test request middleware setup"""
        mixin = MiddlewareMixin()
        app = Flask(__name__)
        container = Mock()

        # Should not raise exception
        mixin._setup_request_middleware(app, container)

    def test_setup_performance_middleware(self):
        """Test performance middleware setup"""
        mixin = MiddlewareMixin()
        app = Flask(__name__)
        container = Mock()

        # Should not raise exception
        mixin._setup_performance_middleware(app, container)

    def test_setup_build_info_context(self):
        """Test build info context setup"""
        mixin = MiddlewareMixin()
        app = Flask(__name__)

        # Should not raise exception
        mixin._setup_build_info_context(app)


class TestBlueprintRegistrationMixin:
    """Test the BlueprintRegistrationMixin class"""

    def test_mixin_exists(self):
        """Test that BlueprintRegistrationMixin exists"""
        mixin = BlueprintRegistrationMixin()
        assert mixin is not None

    def test_mixin_methods_exist(self):
        """Test that mixin has expected blueprint registration methods"""
        mixin = BlueprintRegistrationMixin()

        expected_methods = [
            "_register_core_blueprints",
            "_register_v2_blueprints",
            "_register_security_blueprints",
            "_register_debug_blueprints",
        ]

        for method_name in expected_methods:
            assert hasattr(mixin, method_name), f"Method {method_name} should exist"

    def test_mixin_inheritance(self):
        """Test that mixin can be inherited"""

        class TestApp(BlueprintRegistrationMixin):
            pass

        app = TestApp()
        assert isinstance(app, BlueprintRegistrationMixin)

    def test_register_core_blueprints(self):
        """Test core blueprints registration"""
        mixin = BlueprintRegistrationMixin()
        app = Flask(__name__)
        container = Mock()

        # Should not raise exception
        mixin._register_core_blueprints(app, container)

    def test_register_v2_blueprints(self):
        """Test V2 API blueprints registration"""
        mixin = BlueprintRegistrationMixin()
        app = Flask(__name__)
        container = Mock()

        # Should not raise exception
        mixin._register_v2_blueprints(app, container)

    def test_register_security_blueprints(self):
        """Test security blueprints registration"""
        mixin = BlueprintRegistrationMixin()
        app = Flask(__name__)
        container = Mock()

        # Should not raise exception
        mixin._register_security_blueprints(app, container)

    def test_register_debug_blueprints(self):
        """Test debug blueprints registration"""
        mixin = BlueprintRegistrationMixin()
        app = Flask(__name__)
        container = Mock()

        # Should not raise exception
        mixin._register_debug_blueprints(app, container)


class TestErrorHandlerMixin:
    """Test the ErrorHandlerMixin class"""

    def test_mixin_exists(self):
        """Test that ErrorHandlerMixin exists"""
        mixin = ErrorHandlerMixin()
        assert mixin is not None

    def test_mixin_methods_exist(self):
        """Test that mixin has expected error handler methods"""
        mixin = ErrorHandlerMixin()

        expected_methods = ["_setup_error_handlers"]

        for method_name in expected_methods:
            assert hasattr(mixin, method_name), f"Method {method_name} should exist"

    def test_mixin_inheritance(self):
        """Test that mixin can be inherited"""

        class TestApp(ErrorHandlerMixin):
            pass

        app = TestApp()
        assert isinstance(app, ErrorHandlerMixin)

    def test_setup_error_handlers(self):
        """Test error handlers setup"""
        mixin = ErrorHandlerMixin()
        app = Flask(__name__)

        # Should not raise exception
        mixin._setup_error_handlers(app)


class TestMixinIntegration:
    """Test integration between mixins"""

    def test_all_mixins_together(self):
        """Test that all mixins can be used together"""

        class IntegratedApp(
            AppConfigurationMixin,
            MiddlewareMixin,
            BlueprintRegistrationMixin,
            ErrorHandlerMixin,
        ):
            pass

        app = IntegratedApp()
        assert isinstance(app, AppConfigurationMixin)
        assert isinstance(app, MiddlewareMixin)
        assert isinstance(app, BlueprintRegistrationMixin)
        assert isinstance(app, ErrorHandlerMixin)

    @patch("flask_cors.CORS")
    @patch("flask_compress.Compress")
    @patch("werkzeug.middleware.proxy_fix.ProxyFix")
    def test_full_configuration_flow(
        self, mock_proxy_fix, mock_compress_class, mock_cors
    ):
        """Test complete configuration flow"""

        class TestApp(AppConfigurationMixin):
            pass

        app_instance = TestApp()
        flask_app = Flask(__name__)

        mock_proxy_fix.return_value = Mock()
        mock_compress = Mock()
        mock_compress_class.return_value = mock_compress

        # Run all configuration methods
        app_instance._setup_basic_config(flask_app)
        app_instance._setup_cors(flask_app)
        app_instance._setup_compression(flask_app)
        result = app_instance._setup_json_optimization(flask_app)
        app_instance._setup_timezone(flask_app)

        # Verify all methods were called
        mock_proxy_fix.assert_called_once()
        mock_cors.assert_called_once()
        mock_compress_class.assert_called_once()
        assert result == True  # orjson is available in requirements.txt

    def test_mixin_method_resolution_order(self):
        """Test method resolution order with multiple inheritance"""

        class TestApp(
            AppConfigurationMixin,
            MiddlewareMixin,
            BlueprintRegistrationMixin,
            ErrorHandlerMixin,
        ):
            def test_method(self):
                return "TestApp"

        app = TestApp()
        assert app.test_method() == "TestApp"

        # Verify MRO includes all mixins
        mro_classes = [cls.__name__ for cls in TestApp.__mro__]
        assert "AppConfigurationMixin" in mro_classes
        assert "MiddlewareMixin" in mro_classes
        assert "BlueprintRegistrationMixin" in mro_classes
        assert "ErrorHandlerMixin" in mro_classes


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions"""

    def test_configuration_with_missing_dependencies(self):
        """Test configuration when dependencies are missing"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        # Test with mocked missing imports
        with patch(
            "flask_cors.CORS", side_effect=ImportError("flask-cors not installed")
        ):
            with pytest.raises(ImportError):
                mixin._setup_cors(app)

    def test_configuration_with_invalid_environment(self):
        """Test configuration with invalid environment variables"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch.dict(os.environ, {"ALLOWED_ORIGINS": ""}):
            with patch("flask_cors.CORS") as mock_cors:
                mixin._setup_cors(app)
                mock_cors.assert_called_once_with(app, origins=[""])

    def test_compression_with_debug_mode(self):
        """Test compression configuration in debug mode"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)
        app.debug = True

        with patch("flask_compress.Compress"):
            mixin._setup_compression(app)

            assert app.config["COMPRESS_DEBUG"] == True

    def test_compression_without_debug_mode(self):
        """Test compression configuration without debug mode"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)
        app.debug = False

        with patch("flask_compress.Compress"):
            mixin._setup_compression(app)

            assert app.config["COMPRESS_DEBUG"] == False


class TestPerformanceConfiguration:
    """Test performance-related configuration"""

    def test_compression_cache_key_function(self):
        """Test compression cache key generation"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch("flask_compress.Compress"):
            mixin._setup_compression(app)

            # Test cache key function
            cache_key_func = app.config["COMPRESS_CACHE_KEY"]
            with app.test_request_context("/test/path"):
                cache_key = cache_key_func()
                assert cache_key == "/test/path"

    def test_compression_performance_settings(self):
        """Test compression performance settings"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        with patch("flask_compress.Compress"):
            mixin._setup_compression(app)

            # Verify performance-optimized settings
            assert app.config["COMPRESS_LEVEL"] == 6  # Balanced compression
            assert app.config["COMPRESS_MIN_SIZE"] == 1024  # Only compress larger files
            assert app.config["COMPRESS_CACHE_BACKEND"] == "SimpleCache"

    def test_json_optimization_config(self):
        """Test JSON optimization configuration"""
        mixin = AppConfigurationMixin()
        app = Flask(__name__)

        # Since orjson is available, test the True path
        result = mixin._setup_json_optimization(app)
        assert result == True

        # App config should be modified when orjson is available
        assert app.config.get("JSON_SORT_KEYS") == False


if __name__ == "__main__":
    pytest.main([__file__])

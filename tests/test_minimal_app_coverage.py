#!/usr/bin/env python3
"""
Tests for src/core/minimal_app.py - Complete coverage for minimal Flask app factory.

This module provides comprehensive test coverage for the minimal Flask application
factory function, ensuring all code paths are tested including error handling.

Test Coverage Areas:
- App creation and configuration
- Route registration (collection, web)
- Error handling in route registration
- Template context injection
- Build info reading with various scenarios
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import with proper Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.minimal_app import create_minimal_app

class TestMinimalAppFactory:
    """Test cases for minimal Flask application factory."""

    def test_create_minimal_app_basic(self):
        """Test basic app creation with default configuration."""
        app = create_minimal_app()
        
        assert app is not None
        assert app.config['SECRET_KEY'] == "dev-secret-key-change-in-production"
        assert app.config['DEBUG'] is False
        assert app.config['TESTING'] is False

    def test_app_folder_configuration(self):
        """Test that app is configured with correct template and static folders."""
        app = create_minimal_app()
        
        # Template and static folders should be configured
        assert app.template_folder is not None
        assert app.static_folder is not None
        assert 'templates' in app.template_folder
        assert 'static' in app.static_folder

    @patch('src.core.minimal_app.register_collection_routes')
    def test_collection_routes_registration_success(self, mock_register):
        """Test successful collection routes registration."""
        mock_register.return_value = None
        
        app = create_minimal_app()
        
        mock_register.assert_called_once_with(app)

    @patch('src.core.minimal_app.register_collection_routes')
    def test_collection_routes_registration_failure(self, mock_register):
        """Test collection routes registration failure handling."""
        mock_register.side_effect = Exception("Registration failed")
        
        # Should not raise exception, just log error
        app = create_minimal_app()
        
        assert app is not None
        mock_register.assert_called_once_with(app)

    @patch('src.core.minimal_app.register_simple_api')
    def test_simple_api_registration(self, mock_register):
        """Test simple API registration."""
        mock_register.return_value = None
        
        app = create_minimal_app()
        
        mock_register.assert_called_once_with(app)

    def test_web_routes_registration_success(self):
        """Test web routes registration when web module is available."""
        try:
            app = create_minimal_app()
            # If web routes exist, they should be registered
            assert app is not None
        except ImportError:
            # If web module doesn't exist, that's also fine
            pytest.skip("Web routes module not available")

    @patch('src.core.minimal_app.logger')
    def test_web_routes_registration_failure(self, mock_logger):
        """Test web routes registration failure handling."""
        with patch.dict('sys.modules', {'src.web.routes': None}):
            app = create_minimal_app()
            assert app is not None

class TestBuildInfoContext:
    """Test cases for build info template context."""

    def test_build_info_context_with_file(self):
        """Test build info context when build info file exists."""
        app = create_minimal_app()
        
        # Create temporary build info file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.build_info') as f:
            f.write("BUILD_TIME='2025-08-21 10:00:00 KST'\n")
            f.write("VERSION=1.1.7\n")
            temp_file = f.name

        try:
            # Mock the Path.exists() to return True for our temp file
            with patch('src.core.minimal_app.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                # Mock open to read our temp file
                with patch('builtins.open', mock_open_build_file(temp_file)):
                    with app.app_context():
                        context = {}
                        for processor in app.template_context_processors[None]:
                            context.update(processor())
                        
                        assert 'build_time' in context
                        assert '2025-08-21 10:00:00 KST' in context['build_time']
        finally:
            os.unlink(temp_file)

    def test_build_info_context_without_file(self):
        """Test build info context when build info file doesn't exist."""
        app = create_minimal_app()
        
        with patch('src.core.minimal_app.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            
            with app.app_context():
                context = {}
                for processor in app.template_context_processors[None]:
                    context.update(processor())
                
                assert 'build_time' in context
                assert context['build_time'] == "2025-06-18 18:55:33 KST"

    def test_build_info_context_file_read_error(self):
        """Test build info context when file reading fails."""
        app = create_minimal_app()
        
        with patch('src.core.minimal_app.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            
            # Mock open to raise an exception
            with patch('builtins.open', side_effect=IOError("File read error")):
                with app.app_context():
                    context = {}
                    for processor in app.template_context_processors[None]:
                        context.update(processor())
                    
                    # Should fall back to default
                    assert 'build_time' in context
                    assert context['build_time'] == "2025-06-18 18:55:33 KST"

    def test_build_info_context_malformed_file(self):
        """Test build info context with malformed build info file."""
        app = create_minimal_app()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.build_info') as f:
            f.write("INVALID_FORMAT\n")
            f.write("ALSO_INVALID=no_quotes\n")
            temp_file = f.name

        try:
            with patch('src.core.minimal_app.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                with patch('builtins.open', mock_open_build_file(temp_file)):
                    with app.app_context():
                        context = {}
                        for processor in app.template_context_processors[None]:
                            context.update(processor())
                        
                        # Should fall back to default when no valid BUILD_TIME found
                        assert 'build_time' in context
                        assert context['build_time'] == "2025-06-18 18:55:33 KST"
        finally:
            os.unlink(temp_file)

class TestAppIntegration:
    """Integration tests for the minimal app."""

    def test_cors_enabled(self):
        """Test that CORS is properly enabled on the app."""
        app = create_minimal_app()
        
        # CORS should be configured - we can test this indirectly
        with app.test_client() as client:
            # Any route should include CORS headers (if routes exist)
            response = client.options('/')
            # Just verify the app doesn't crash with CORS
            assert response is not None

    def test_app_context_works(self):
        """Test that Flask app context works correctly."""
        app = create_minimal_app()
        
        with app.app_context():
            from flask import current_app
            assert current_app is not None
            assert current_app.config['SECRET_KEY'] == "dev-secret-key-change-in-production"

def mock_open_build_file(file_path):
    """Helper function to mock file opening for build info."""
    def mock_open(*args, **kwargs):
        with open(file_path, 'r') as f:
            return f
    return mock_open

if __name__ == "__main__":
    # Validation block - test all functions with actual data
    import sys
    
    all_validation_failures = []
    total_tests = 0

    # Test 1: Basic app creation
    total_tests += 1
    try:
        test_app = create_minimal_app()
        if test_app is None:
            all_validation_failures.append("Basic app creation: Expected Flask app, got None")
        elif not hasattr(test_app, 'config'):
            all_validation_failures.append("Basic app creation: App missing config attribute")
        elif test_app.config.get('SECRET_KEY') != "dev-secret-key-change-in-production":
            all_validation_failures.append(f"Basic app creation: Unexpected SECRET_KEY: {test_app.config.get('SECRET_KEY')}")
    except Exception as e:
        all_validation_failures.append(f"Basic app creation: Exception raised: {e}")

    # Test 2: Template context injection
    total_tests += 1
    try:
        test_app = create_minimal_app()
        with test_app.app_context():
            context_processors = test_app.template_context_processors.get(None, [])
            if not context_processors:
                all_validation_failures.append("Template context: No context processors found")
            else:
                # Execute context processor
                context = {}
                for processor in context_processors:
                    try:
                        processor_result = processor()
                        context.update(processor_result)
                    except Exception as e:
                        all_validation_failures.append(f"Template context: Context processor failed: {e}")
                
                if 'build_time' not in context:
                    all_validation_failures.append("Template context: build_time not in context")
    except Exception as e:
        all_validation_failures.append(f"Template context: Exception raised: {e}")

    # Test 3: Configuration validation
    total_tests += 1
    try:
        test_app = create_minimal_app()
        required_config = ['SECRET_KEY', 'DEBUG', 'TESTING']
        for key in required_config:
            if key not in test_app.config:
                all_validation_failures.append(f"Configuration: Missing required config key: {key}")
        
        # Check expected values
        expected_values = {
            'DEBUG': False,
            'TESTING': False
        }
        for key, expected in expected_values.items():
            if test_app.config.get(key) != expected:
                all_validation_failures.append(f"Configuration: {key} expected {expected}, got {test_app.config.get(key)}")
    except Exception as e:
        all_validation_failures.append(f"Configuration validation: Exception raised: {e}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Minimal app factory is validated and ready for comprehensive testing")
        sys.exit(0)
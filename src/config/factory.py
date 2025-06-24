"""
Configuration factory
"""
import os
from typing import Type
from .base import BaseConfig
from .production import ProductionConfig
from .development import DevelopmentConfig
from .testing import TestingConfig
from src.core.constants import ENV_PRODUCTION, ENV_DEVELOPMENT, ENV_TESTING


def get_config(config_name: str = None) -> Type[BaseConfig]:
    """
    Get configuration class based on environment name
    
    Args:
        config_name: Environment name (production, development, testing)
        
    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', ENV_PRODUCTION)
    
    config_mapping = {
        ENV_PRODUCTION: ProductionConfig,
        ENV_DEVELOPMENT: DevelopmentConfig,
        ENV_TESTING: TestingConfig,
        # Aliases
        'prod': ProductionConfig,
        'dev': DevelopmentConfig,
        'test': TestingConfig,
    }
    
    config_class = config_mapping.get(config_name.lower(), ProductionConfig)
    
    # Validate configuration
    errors = config_class.validate()
    if errors:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Configuration warnings: {'; '.join(errors)}")
    
    return config_class
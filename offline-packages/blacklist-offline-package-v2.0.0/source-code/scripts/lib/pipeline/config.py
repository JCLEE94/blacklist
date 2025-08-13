#!/usr/bin/env python3
"""
Pipeline Configuration - Central configuration management
"""

import os
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Pipeline configuration data class"""

    registry: str = os.getenv("REGISTRY", "registry.jclee.me")
    image_name: str = os.getenv("IMAGE_NAME", "blacklist")
    namespace: str = os.getenv("NAMESPACE", "blacklist")
    argocd_server: str = os.getenv("ARGOCD_SERVER", "argo.jclee.me")
    python_version: str = os.getenv("PYTHON_VERSION", "3.10")
    dry_run: bool = os.getenv("DRY_RUN", "false").lower() == "true"
    verbose: bool = os.getenv("VERBOSE", "false").lower() == "true"
    project_root: str = os.getenv("PROJECT_ROOT", os.getcwd())

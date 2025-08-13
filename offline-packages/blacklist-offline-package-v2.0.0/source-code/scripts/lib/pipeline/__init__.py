#!/usr/bin/env python3
"""
Pipeline Package - Modularized CI/CD pipeline functionality
Maintains backward compatibility with the original cicd_testability module
"""

# Import all components to maintain backward compatibility
from .base import PipelineStage
from .build import BuildStage
from .config import PipelineConfig
from .deploy import DeploymentStage
from .orchestrator import PipelineOrchestrator
from .quality import CodeQualityStage
from .test import TestStage

# Export all public interfaces
__all__ = [
    "PipelineConfig",
    "PipelineStage",
    "CodeQualityStage",
    "TestStage",
    "BuildStage",
    "DeploymentStage",
    "PipelineOrchestrator",
]


def main():
    """CLI entry point for backward compatibility"""
    import sys

    from .orchestrator import main as orchestrator_main

    # Delegate to orchestrator main function
    orchestrator_main()


if __name__ == "__main__":
    main()

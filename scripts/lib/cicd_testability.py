#!/usr/bin/env python3
"""
CI/CD Testability - Backward compatibility wrapper for modularized pipeline
This module maintains backward compatibility while delegating to modular pipeline packages
"""

# Import all components from the modularized package to maintain backward compatibility
from .pipeline import (
    BuildStage,
    CodeQualityStage,
    DeploymentStage,
    PipelineConfig,
    PipelineOrchestrator,
    PipelineStage,
    TestStage,
    main,
)

# Re-export everything for backward compatibility
__all__ = [
    "PipelineConfig",
    "PipelineStage",
    "CodeQualityStage", 
    "TestStage",
    "BuildStage",
    "DeploymentStage",
    "PipelineOrchestrator",
    "main",
]

# Support direct execution for backward compatibility
if __name__ == "__main__":
    main()

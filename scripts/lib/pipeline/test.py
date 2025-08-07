#!/usr/bin/env python3
"""
Test Pipeline Stage - Test execution and coverage reporting
"""

import json
import logging
import subprocess
from pathlib import Path

from .base import PipelineStage
from .config import PipelineConfig

logger = logging.getLogger(__name__)


class TestStage(PipelineStage):
    """Test execution stage"""

    def __init__(self, config: PipelineConfig):
        super().__init__("test", config)
        self.coverage_threshold = 80

    def run(self) -> bool:
        """Execute tests"""
        try:
            # Run pytest
            cmd = [
                "pytest",
                "-v",
                "--cov=src",
                "--cov-report=json",
                "--cov-report=term",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=300)  # 5min timeout

            if result.returncode != 0:
                logger.error(f"Tests failed:\n{result.stdout.decode()}")
                return False

            # Check coverage
            if Path("coverage.json").exists():
                with open("coverage.json") as f:
                    coverage_data = json.load(f)
                    coverage_percent = coverage_data["totals"]["percent_covered"]

                    if coverage_percent < self.coverage_threshold:
                        logger.warning(
                            f"Coverage {coverage_percent:.1f}% is below threshold {self.coverage_threshold}%"
                        )
                        return False

            return True

        except subprocess.TimeoutExpired:
            self.errors.append("Test execution timed out after 5 minutes")
            return False
        except Exception as e:
            self.errors.append(f"Test execution failed: {e}")
            return False

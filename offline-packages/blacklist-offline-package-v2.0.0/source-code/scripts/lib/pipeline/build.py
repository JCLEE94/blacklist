#!/usr/bin/env python3
"""
Build Pipeline Stage - Docker image building and tagging
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from .base import PipelineStage
from .config import PipelineConfig

logger = logging.getLogger(__name__)


class BuildStage(PipelineStage):
    """Docker build stage"""

    def __init__(self, config: PipelineConfig):
        super().__init__("build", config)
        self.image_tags = []

    def run(self) -> bool:
        """Build Docker image"""
        try:
            # Prepare build context
            if not Path("deployment/Dockerfile").exists():
                logger.error("Dockerfile not found")
                return False

            # Generate tags
            commit_sha = self._get_commit_sha()
            date_tag = datetime.now().strftime("%Y%m%d-%H%M%S")

            self.image_tags = [
                f"{self.config.registry}/{self.config.image_name}:latest",
                f"{self.config.registry}/{self.config.image_name}:sha-{commit_sha[:7]}",
                f"{self.config.registry}/{self.config.image_name}:date-{date_tag}",
            ]

            # Build Docker images
            for tag in self.image_tags:
                cmd = [
                    "docker",
                    "build",
                    "-f",
                    "deployment/Dockerfile",
                    "-t",
                    tag,
                    "--cache-from",
                    f"{self.config.registry}/{self.config.image_name}:latest",
                    ".",
                ]

                if self.config.verbose:
                    logger.info(f"Building image: {tag}")

                result = subprocess.run(
                    cmd, capture_output=True, timeout=600
                )  # 10min timeout
                if result.returncode != 0:
                    logger.error(f"Build failed for {tag}: {result.stderr.decode()}")
                    return False

            return True

        except subprocess.TimeoutExpired:
            self.errors.append("Docker build timed out after 10 minutes")
            return False
        except Exception as e:
            self.errors.append(f"Docker build failed: {e}")
            return False

    def _get_commit_sha(self) -> str:
        """Get current Git commit SHA"""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"

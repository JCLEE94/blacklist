#!/usr/bin/env python3
"""
Pipeline Base - Base classes for pipeline stages
"""

import logging
from datetime import datetime
from typing import Any, Dict

from .config import PipelineConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PipelineStage:
    """Pipeline stage base class"""

    def __init__(self, name: str, config: PipelineConfig):
        self.name = name
        self.config = config
        self.start_time = None
        self.end_time = None
        self.status = "pending"
        self.errors = []

    def pre_hook(self):
        """Hook before stage execution"""
        logger.info(f"Starting stage: {self.name}")
        self.start_time = datetime.now()

    def post_hook(self):
        """Hook after stage execution"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Completed stage: {self.name} in {duration:.2f} seconds")

    def run(self) -> bool:
        """Execute stage (default implementation)"""
        logger.info(f"Executing stage: {self.name}")
        
        # Default successful execution
        # Subclasses should override this method for specific functionality
        return True

    def execute(self) -> Dict[str, Any]:
        """Execute stage wrapper with error handling"""
        try:
            self.pre_hook()

            if self.config.dry_run:
                logger.info(f"[DRY RUN] Would execute: {self.name}")
                success = True
            else:
                success = self.run()

            self.status = "success" if success else "failed"

        except Exception as e:
            logger.error(f"Stage {self.name} failed: {str(e)}")
            self.status = "error"
            self.errors.append(str(e))
            success = False

        finally:
            self.post_hook()

        return {
            "stage": self.name,
            "status": self.status,
            "duration": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time
                else None
            ),
            "errors": self.errors,
        }

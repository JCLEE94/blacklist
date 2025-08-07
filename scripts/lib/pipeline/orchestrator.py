#!/usr/bin/env python3
"""
Pipeline Orchestrator - Manages and executes the complete CI/CD pipeline
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from .build import BuildStage
from .config import PipelineConfig
from .deploy import DeploymentStage
from .quality import CodeQualityStage
from .test import TestStage

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Pipeline orchestrator"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stages = [
            CodeQualityStage(config),
            TestStage(config),
            BuildStage(config),
            DeploymentStage(config),
        ]

    def run(self, skip_stages: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run complete pipeline"""
        skip_stages = skip_stages or []
        results = {
            "started_at": datetime.now().isoformat(),
            "config": self.config.__dict__,
            "stages": [],
        }

        for stage in self.stages:
            if stage.name in skip_stages:
                logger.info(f"Skipping stage: {stage.name}")
                continue

            result = stage.execute()
            results["stages"].append(result)

            # Stop on failure
            if result["status"] != "success":
                logger.error(f"Pipeline failed at stage: {stage.name}")
                break

        results["completed_at"] = datetime.now().isoformat()
        results["overall_status"] = (
            "success"
            if all(s["status"] == "success" for s in results["stages"])
            else "failed"
        )

        return results


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD Pipeline Test Runner")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--skip", nargs="+", help="Stages to skip")
    parser.add_argument("--stage", help="Run single stage only")

    args = parser.parse_args()

    # Create configuration
    config = PipelineConfig(dry_run=args.dry_run, verbose=args.verbose)

    # Run single stage
    if args.stage:
        stage_map = {
            "code-quality": CodeQualityStage,
            "test": TestStage,
            "build": BuildStage,
            "deployment": DeploymentStage,
        }

        if args.stage not in stage_map:
            logger.error(f"Unknown stage: {args.stage}")
            sys.exit(1)

        stage = stage_map[args.stage](config)
        result = stage.execute()
        print(json.dumps(result, indent=2))

    else:
        # Run complete pipeline
        orchestrator = PipelineOrchestrator(config)
        results = orchestrator.run(skip_stages=args.skip)

        print(json.dumps(results, indent=2))

        # Set exit code
        sys.exit(0 if results["overall_status"] == "success" else 1)


if __name__ == "__main__":
    main()

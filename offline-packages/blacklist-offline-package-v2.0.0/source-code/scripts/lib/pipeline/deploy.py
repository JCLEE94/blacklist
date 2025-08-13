#!/usr/bin/env python3
"""
Deployment Pipeline Stage - ArgoCD deployment and health checks
"""

import json
import logging
import subprocess

from .base import PipelineStage
from .config import PipelineConfig

logger = logging.getLogger(__name__)


class DeploymentStage(PipelineStage):
    """Deployment stage"""

    def __init__(self, config: PipelineConfig):
        super().__init__("deployment", config)

    def run(self) -> bool:
        """Execute deployment"""
        # ArgoCD app sync
        if not self._sync_argocd_app():
            return False

        # Health check
        if not self._verify_deployment():
            # Attempt rollback
            logger.warning("Deployment verification failed, attempting rollback...")
            return self._rollback_deployment()

        return True

    def _sync_argocd_app(self) -> bool:
        """Sync ArgoCD application"""
        try:
            cmd = [
                "argocd",
                "app",
                "sync",
                self.config.image_name,
                "--server",
                self.config.argocd_server,
                "--grpc-web",
            ]

            result = subprocess.run(
                cmd, capture_output=True, timeout=120
            )  # 2min timeout
            if result.returncode != 0:
                logger.error(f"ArgoCD sync failed: {result.stderr.decode()}")
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("ArgoCD sync timed out")
            return False
        except Exception as e:
            logger.error(f"ArgoCD sync failed: {e}")
            return False

    def _verify_deployment(self) -> bool:
        """Verify deployment health"""
        try:
            # Check pod status
            cmd = [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.config.namespace,
                "-l",
                f"app={self.config.image_name}",
                "-o",
                "json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"Failed to get pods: {result.stderr}")
                return False

            pods = json.loads(result.stdout)
            ready_pods = sum(
                1
                for pod in pods.get("items", [])
                if pod.get("status", {}).get("containerStatuses")
                and all(
                    c.get("ready", False) for c in pod["status"]["containerStatuses"]
                )
            )

            logger.info(f"Ready pods: {ready_pods}")
            return ready_pods > 0

        except subprocess.TimeoutExpired:
            logger.error("Deployment verification timed out")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse kubectl output: {e}")
            return False
        except Exception as e:
            logger.error(f"Deployment verification failed: {e}")
            return False

    def _rollback_deployment(self) -> bool:
        """Rollback deployment"""
        try:
            cmd = [
                "argocd",
                "app",
                "rollback",
                self.config.image_name,
                "--server",
                self.config.argocd_server,
                "--grpc-web",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                logger.error(f"Rollback failed: {result.stderr.decode()}")
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.error("Rollback timed out")
            return False
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

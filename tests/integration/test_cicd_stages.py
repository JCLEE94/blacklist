"""
CI/CD 파이프라인 스테이지 클래스들

공통 스테이지 및 Mock 클래스들을 분리한 모듈
"""

import datetime


# Mock classes for testing instead of missing modules
class PipelineConfig:
    def __init__(
        self,
        registry="ghcr.io",
        image_name="blacklist",
        namespace="blacklist",
        dry_run=False,
        verbose=False,
    ):
        self.registry = registry
        self.image_name = image_name
        self.namespace = namespace
        self.dry_run = dry_run
        self.verbose = verbose


class PipelineStage:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.status = "pending"
        self.errors = []

    def execute(self):
        import time

        start_time = time.time()
        try:
            if self.config.dry_run:
                result = True
            else:
                result = self.run()
            self.status = "success" if result else "error"
        except Exception as e:
            self.status = "error"
            self.errors.append(str(e))

        return {
            "stage": self.name,
            "status": self.status,
            "duration": time.time() - start_time,
            "errors": self.errors,
        }

    def run(self):
        return True


class CodeQualityStage(PipelineStage):
    def __init__(self, config):
        super().__init__("code-quality", config)

    def _check_python_syntax(self):
        return True

    def _check_code_style(self):
        return True

    def _check_security(self):
        return True

    def _check_dependencies(self):
        return True


class BuildStage(PipelineStage):
    def __init__(self, config):
        super().__init__("build", config)
        self.image_tags = []

    def run(self):
        sha = self._get_commit_sha()
        self.image_tags = [
            "{self.config.registry}/{self.config.image_name}:latest",
            "{self.config.registry}/{self.config.image_name}:sha-{sha[:7]}",
            "{self.config.registry}/{self.config.image_name}:date-{datetime.datetime.now().strftime('%Y%m%d')}",
        ]
        return True

    def _get_commit_sha(self):
        return "abc123def456789"


class CICDTestStage(PipelineStage):
    def __init__(self, config):
        super().__init__("test", config)


class DeploymentStage(PipelineStage):
    def __init__(self, config):
        super().__init__("deployment", config)

    def run(self):
        """Deploy application using standard process"""
        return True  # Simplified for testing

    def _sync_argocd_app(self):
        return True

    def _verify_deployment(self):
        return True


# Shared test utilities
class MockStageSuccess(PipelineStage):
    """Mock stage that always succeeds"""

    def run(self):
        return True


class MockStageFail(PipelineStage):
    """Mock stage that always fails"""

    def run(self):
        raise Exception("Simulated failure")


class MockStageDryRun(PipelineStage):
    """Mock stage for dry run testing"""

    def run(self):
        raise Exception("Should not be called in dry run")


class PipelineOrchestrator:
    def __init__(self, config):
        self.config = config
        self.stages = [
            CodeQualityStage(config),
            CICDTestStage(config),
            BuildStage(config),
            DeploymentStage(config),
        ]

    def run(self, skip_stages=None):
        if skip_stages is None:
            skip_stages = []

        results = {"stages": [], "overall_status": "success"}

        for stage in self.stages:
            if stage.name in skip_stages:
                continue

            result = stage.execute()
            results["stages"].append(result)

            if result["status"] == "error":
                results["overall_status"] = "failed"
                break

        return results

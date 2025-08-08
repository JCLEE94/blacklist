"""
CI/CD 파이프라인 리팩토링을 위한 통합 테스트

테스트 가능성을 높이기 위한 리팩토링 검증
"""

import json
import os
import sys
from unittest.mock import Mock, patch


# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# Import shared pipeline classes
from .test_cicd_stages import (BuildStage, CICDTestStage, CodeQualityStage,
                               DeploymentStage, MockStageDryRun, MockStageFail,
                               MockStageSuccess, PipelineConfig,
                               PipelineOrchestrator)


def main():
    """Mock main function for CLI testing"""


class TestPipelineConfig:
    """파이프라인 설정 테스트"""

    def test_config_from_environment(self):
        """환경 변수에서 설정 로드 테스트"""
        with patch.dict(
            os.environ,
            {
                "REGISTRY": "test.registry.com",
                "IMAGE_NAME": "test-app",
                "NAMESPACE": "test-ns",
                "DRY_RUN": "true",
                "VERBOSE": "true",
            },
        ):
            config = PipelineConfig()

            assert config.registry == "test.registry.com"
            assert config.image_name == "test-app"
            assert config.namespace == "test-ns"
            assert config.dry_run is True
            assert config.verbose is True

    def test_config_defaults(self):
        """기본 설정값 테스트"""
        config = PipelineConfig()

        assert config.registry == "registry.jclee.me"
        assert config.image_name == "blacklist"
        assert config.namespace == "blacklist"
        assert config.dry_run is False
        assert config.verbose is False


class TestPipelineStage:
    """파이프라인 단계 기본 클래스 테스트"""

    def test_stage_lifecycle(self):
        """단계 생명주기 테스트"""
        config = PipelineConfig()

        # Use shared mock stage
        stage = MockStageSuccess("test-stage", config)

        # 초기 상태
        assert stage.name == "test-stage"
        assert stage.status == "pending"
        assert stage.errors == []

        # 실행
        result = stage.execute()

        # 실행 후 상태
        assert result["stage"] == "test-stage"
        assert result["status"] == "success"
        assert result["duration"] is not None
        assert result["errors"] == []

    def test_stage_failure_handling(self):
        """단계 실패 처리 테스트"""
        config = PipelineConfig()

        stage = MockStageFail("failing-stage", config)
        result = stage.execute()

        assert result["status"] == "error"
        assert len(result["errors"]) > 0
        assert "Test failure" in result["errors"][0]

    def test_dry_run_mode(self):
        """드라이런 모드 테스트"""
        config = PipelineConfig(dry_run=True)

        stage = MockStageDryRun("dry-run-stage", config)
        result = stage.execute()

        assert result["status"] == "success"
        assert result["errors"] == []


class TestCodeQualityStage:
    """코드 품질 검사 단계 테스트"""

    @patch("subprocess.run")
    def test_python_syntax_check(self, mock_run):
        """Python 구문 검사 테스트"""
        mock_run.return_value = Mock(returncode=0)

        config = PipelineConfig()
        stage = CodeQualityStage(config)

        # 구문 검사 실행
        result = stage._check_python_syntax()

        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_code_style_check(self, mock_run):
        """코드 스타일 검사 테스트"""
        # flake8 성공 시뮬레이션
        mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        config = PipelineConfig()
        stage = CodeQualityStage(config)

        with patch("pathlib.Path.exists", return_value=True):
            result = stage._check_code_style()

        assert result is True

    @patch("subprocess.run")
    def test_security_scan(self, mock_run):
        """보안 스캔 테스트"""
        # 하드코딩된 시크릿이 없는 경우
        mock_run.return_value = Mock(returncode=1, stdout=b"")

        config = PipelineConfig()
        stage = CodeQualityStage(config)

        result = stage._check_security()
        assert result is True

        # 하드코딩된 시크릿이 있는 경우
        mock_run.return_value = Mock(returncode=0, stdout=b"password = 'hardcoded'")

        result = stage._check_security()
        assert result is False

    def test_dependency_check(self, tmp_path):
        """의존성 검사 테스트"""
        # 올바른 requirements.txt
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
# 의존성 파일
flask==2.3.3
pytest>=7.0.0
black~=22.0
        """
        )

        config = PipelineConfig()
        stage = CodeQualityStage(config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", return_value=req_file.open()):
                result = stage._check_dependencies()

        assert result is True

        # 핀되지 않은 의존성
        req_file.write_text("flask\npytest")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", return_value=req_file.open()):
                result = stage._check_dependencies()

        assert result is False


class TestBuildStage:
    """빌드 단계 테스트"""

    @patch("subprocess.run")
    def test_docker_build(self, mock_run):
        """Docker 빌드 테스트"""
        mock_run.return_value = Mock(returncode=0)

        config = PipelineConfig()
        stage = BuildStage(config)

        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(stage, "_get_commit_sha", return_value="abc123def"):
                result = stage.run()

        assert result is True
        assert len(stage.image_tags) == 3
        assert any("latest" in tag for tag in stage.image_tags)
        assert any("sha-abc123d" in tag for tag in stage.image_tags)
        assert any("date-" in tag for tag in stage.image_tags)

    def test_commit_sha_extraction(self):
        """커밋 SHA 추출 테스트"""
        config = PipelineConfig()
        stage = BuildStage(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="abc123def456789\n")

            sha = stage._get_commit_sha()

        assert sha == "abc123def456789"

    @patch("subprocess.run")
    def test_build_failure_handling(self, mock_run):
        """빌드 실패 처리 테스트"""
        mock_run.return_value = Mock(returncode=1, stderr=b"Build failed")

        config = PipelineConfig()
        stage = BuildStage(config)

        with patch("pathlib.Path.exists", return_value=True):
            result = stage.run()

        assert result is False


class TestDeploymentStage:
    """배포 단계 테스트"""

    @patch("subprocess.run")
    def test_argocd_sync(self, mock_run):
        """ArgoCD 동기화 테스트"""
        mock_run.return_value = Mock(returncode=0)

        config = PipelineConfig()
        stage = DeploymentStage(config)

        result = stage._sync_argocd_app()

        assert result is True
        mock_run.assert_called_with(
            [
                "argocd",
                "app",
                "sync",
                "blacklist",
                "--server",
                "argo.jclee.me",
                "--grpc-web",
            ],
            capture_output=True,
        )

    @patch("subprocess.run")
    def test_deployment_verification(self, mock_run):
        """배포 검증 테스트"""
        # 정상적인 Pod 상태
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(
                {"items": [{"status": {"containerStatuses": [{"ready": True}]}}]}
            ),
        )

        config = PipelineConfig()
        stage = DeploymentStage(config)

        result = stage._verify_deployment()
        assert result is True

    @patch("subprocess.run")
    def test_rollback_on_failure(self, mock_run):
        """실패 시 롤백 테스트"""
        config = PipelineConfig()
        stage = DeploymentStage(config)

        # 동기화 성공, 검증 실패, 롤백 성공 시나리오
        mock_run.side_effect = [
            Mock(returncode=0),  # sync
            Mock(returncode=1),  # verify
            Mock(returncode=0),  # rollback
        ]

        with patch.object(stage, "_sync_argocd_app", return_value=True):
            with patch.object(stage, "_verify_deployment", return_value=False):
                result = stage.run()

        # 롤백이 성공했으므로 True 반환
        assert result is True


class TestPipelineOrchestrator:
    """파이프라인 오케스트레이터 테스트"""

    def test_full_pipeline_execution(self):
        """전체 파이프라인 실행 테스트"""
        config = PipelineConfig(dry_run=True)
        orchestrator = PipelineOrchestrator(config)

        results = orchestrator.run()

        assert results["overall_status"] == "success"
        assert len(results["stages"]) == 4
        assert all(s["status"] == "success" for s in results["stages"])

    def test_pipeline_with_skip_stages(self):
        """특정 단계 건너뛰기 테스트"""
        config = PipelineConfig(dry_run=True)
        orchestrator = PipelineOrchestrator(config)

        results = orchestrator.run(skip_stages=["build", "deployment"])

        # 건너뛴 단계는 결과에 포함되지 않음
        stage_names = [s["stage"] for s in results["stages"]]
        assert "build" not in stage_names
        assert "deployment" not in stage_names

    def test_pipeline_failure_stops_execution(self):
        """실패 시 파이프라인 중단 테스트"""
        config = PipelineConfig()
        orchestrator = PipelineOrchestrator(config)

        # 두 번째 단계(test)에서 실패하도록 설정
        with patch.object(CICDTestStage, "run", return_value=False):
            results = orchestrator.run()

        assert results["overall_status"] == "failed"
        # 실패 이후 단계는 실행되지 않음
        assert len(results["stages"]) < 4


class TestCLIInterface:
    """CLI 인터페이스 테스트"""

    @patch("sys.argv", ["cicd_testability.py", "--dry-run"])
    @patch("scripts.lib.cicd_testability.PipelineOrchestrator.run")
    def test_cli_dry_run(self, mock_run):
        """CLI 드라이런 모드 테스트"""
        mock_run.return_value = {"overall_status": "success", "stages": []}

        from scripts.lib.cicd_testability import main

        with patch("sys.exit"):
            main()

        mock_run.assert_called_once()

    @patch("sys.argv", ["cicd_testability.py", "--stage", "code-quality", "--verbose"])
    def test_cli_single_stage(self):
        """CLI 단일 단계 실행 테스트"""
        from scripts.lib.cicd_testability import main

        with patch(
            "scripts.lib.cicd_testability.CodeQualityStage.execute"
        ) as mock_execute:
            mock_execute.return_value = {
                "stage": "code-quality",
                "status": "success",
                "duration": 10.5,
                "errors": [],
            }

            with patch("builtins.print"):
                with patch("sys.exit"):
                    main()

            mock_execute.assert_called_once()


# 헬퍼 함수 테스트
class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_pipeline_config_serialization(self):
        """파이프라인 설정 직렬화 테스트"""
        config = PipelineConfig(
            registry="test.registry", image_name="test-app", dry_run=True
        )

        config_dict = config.__dict__

        assert isinstance(config_dict, dict)
        assert config_dict["registry"] == "test.registry"
        assert config_dict["image_name"] == "test-app"
        assert config_dict["dry_run"] is True

    def test_stage_result_format(self):
        """단계 결과 형식 테스트"""
        config = PipelineConfig()

        stage = MockStageSuccess("test", config)
        result = stage.execute()

        # 필수 필드 확인
        required_fields = ["stage", "status", "duration", "errors"]
        for field in required_fields:
            assert field in result

        # 타입 확인
        assert isinstance(result["stage"], str)
        assert isinstance(result["status"], str)
        assert isinstance(result["duration"], (int, float))
        assert isinstance(result["errors"], list)

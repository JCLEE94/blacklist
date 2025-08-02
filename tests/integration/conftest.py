"""
CI/CD 통합 테스트를 위한 pytest fixtures
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml


@pytest.fixture
def temp_workspace():
    """임시 작업 공간 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # 기본 디렉토리 구조 생성
        (workspace / ".github" / "workflows").mkdir(parents=True)
        (workspace / "k8s").mkdir(parents=True)
        (workspace / "deployment").mkdir(parents=True)
        (workspace / "scripts").mkdir(parents=True)
        (workspace / "src").mkdir(parents=True)

        yield workspace


@pytest.fixture
def mock_github_event():
    """모의 GitHub 이벤트"""
    return {
        "ref": "refs/heads/main",
        "repository": {"full_name": "JCLEE94/blacklist", "default_branch": "main"},
        "head_commit": {
            "id": "abc123def456789",
            "message": "feat: 새로운 기능 추가",
            "author": {"name": "Test User", "email": "test@example.com"},
        },
        "pusher": {"name": "test-user"},
    }


@pytest.fixture
def sample_workflow():
    """샘플 GitHub Actions 워크플로우"""
    return {
        "name": "Test Pipeline",
        "on": {
            "push": {
                "branches": ["main", "develop"],
                "paths-ignore": ["**.md", "docs/**"],
            },
            "pull_request": {"branches": ["main"]},
        },
        "env": {"REGISTRY": "registry.jclee.me", "IMAGE_NAME": "blacklist"},
        "jobs": {
            "code-quality": {
                "runs-on": "self-hosted",
                "steps": [
                    {"name": "Checkout", "uses": "actions/checkout@v3"},
                    {"name": "Setup Python", "uses": "actions/setup-python@v4"},
                ],
            },
            "test": {"runs-on": "self-hosted", "needs": "code-quality"},
            "build": {"runs-on": "self-hosted", "needs": "test"},
            "deploy": {"runs-on": "self-hosted", "needs": "build"},
        },
    }


@pytest.fixture
def sample_argocd_app():
    """샘플 ArgoCD Application"""
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": "blacklist",
            "namespace": "argocd",
            "annotations": {
                "argocd-image-updater.argoproj.io/image-list": "blacklist=registry.jclee.me/blacklist:latest",
                "argocd-image-updater.argoproj.io/blacklist.update-strategy": "latest",
            },
        },
        "spec": {
            "project": "default",
            "source": {
                "repoURL": "https://github.com/JCLEE94/blacklist.git",
                "targetRevision": "main",
                "path": "k8s",
            },
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": "blacklist",
            },
            "syncPolicy": {"automated": {"prune": True, "selfHeal": True}},
        },
    }


@pytest.fixture
def sample_deployment():
    """샘플 Kubernetes Deployment"""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "blacklist", "namespace": "blacklist"},
        "spec": {
            "replicas": 3,
            "selector": {"matchLabels": {"app": "blacklist"}},
            "template": {
                "metadata": {"labels": {"app": "blacklist"}},
                "spec": {
                    "containers": [
                        {
                            "name": "blacklist",
                            "image": "registry.jclee.me/blacklist:latest",
                            "ports": [{"containerPort": 8541}],
                            "livenessProbe": {
                                "httpGet": {"path": "/health", "port": 8541},
                                "initialDelaySeconds": 30,
                            },
                            "readinessProbe": {
                                "httpGet": {"path": "/health", "port": 8541},
                                "initialDelaySeconds": 10,
                            },
                        }
                    ]
                },
            },
        },
    }


@pytest.fixture
def mock_subprocess():
    """subprocess.run 모킹"""
    with patch("subprocess.run") as mock_run:
        # 기본 성공 응답
        mock_run.return_value = Mock(returncode=0, stdout=b"Success", stderr=b"")
        yield mock_run


@pytest.fixture
def mock_docker_client():
    """Docker 클라이언트 모킹"""
    client = Mock()

    # 이미지 빌드 모킹
    client.images.build.return_value = (Mock(tags=["test:latest"]), [])

    # 이미지 푸시 모킹
    client.images.push.return_value = "Pushed successfully"

    # 컨테이너 실행 모킹
    container = Mock()
    container.logs.return_value = b"Container running"
    container.status = "running"
    client.containers.run.return_value = container

    return client


@pytest.fixture
def mock_kubectl():
    """kubectl 명령 모킹"""

    def kubectl_side_effect(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])

        if "get" in cmd and "pods" in cmd:
            return Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "items": [
                            {
                                "metadata": {"name": "blacklist-abc123"},
                                "status": {
                                    "phase": "Running",
                                    "containerStatuses": [
                                        {"name": "blacklist", "ready": True}
                                    ],
                                },
                            }
                        ]
                    }
                ).encode(),
            )
        elif "apply" in cmd:
            return Mock(returncode=0, stdout=b"configured")
        elif "rollout" in cmd:
            return Mock(returncode=0, stdout=b"deployment rolled out")

        return Mock(returncode=0, stdout=b"OK")

    with patch("subprocess.run", side_effect=kubectl_side_effect) as mock:
        yield mock


@pytest.fixture
def mock_argocd():
    """ArgoCD CLI 모킹"""

    def argocd_side_effect(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])

        if "app" in cmd and "sync" in cmd:
            return Mock(returncode=0, stdout=b"Application synced")
        elif "app" in cmd and "list" in cmd:
            return Mock(
                returncode=0,
                stdout=b"NAME       STATUS  HEALTH\nblacklist  Synced  Healthy",
            )
        elif "app" in cmd and "rollback" in cmd:
            return Mock(returncode=0, stdout=b"Rolled back")

        return Mock(returncode=0, stdout=b"OK")

    with patch("subprocess.run", side_effect=argocd_side_effect) as mock:
        yield mock


@pytest.fixture
def pipeline_config():
    """파이프라인 설정"""
    return {
        "registry": "registry.jclee.me",
        "image_name": "blacklist",
        "namespace": "blacklist",
        "argocd_server": "argo.jclee.me",
        "python_version": "3.10",
        "dry_run": False,
        "verbose": True,
    }


# 헬퍼 함수들
def create_test_file(path: Path, content: str):
    """테스트 파일 생성"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_workflow_file(workspace: Path, workflow: dict):
    """워크플로우 파일 생성"""
    workflow_path = workspace / ".github" / "workflows" / "test.yml"
    create_test_file(workflow_path, yaml.dump(workflow))
    return workflow_path


def create_k8s_manifest(workspace: Path, name: str, manifest: dict):
    """Kubernetes 매니페스트 생성"""
    manifest_path = workspace / "k8s" / f"{name}.yaml"
    create_test_file(manifest_path, yaml.dump(manifest))
    return manifest_path


# 테스트 데이터 생성기
@pytest.fixture
def test_data_generator():
    """테스트 데이터 생성기"""

    def generate_commit_data(count=5):
        """커밋 데이터 생성"""
        commits = []
        for i in range(count):
            commits.append(
                {
                    "sha": f"commit{i:03d}sha",
                    "message": f"Test commit {i}",
                    "author": {"name": f"User{i}", "email": f"user{i}@test.com"},
                }
            )
        return commits

    def generate_docker_tags(base_name="test", count=3):
        """Docker 태그 생성"""
        tags = [f"{base_name}:latest"]
        for i in range(1, count):
            tags.append(f"{base_name}:v{i}.0.0")
        return tags

    return {"commits": generate_commit_data, "docker_tags": generate_docker_tags}

#!/usr/bin/env python3
"""
통합 테스트: CI/CD Pipeline
GitHub Actions, Docker Build, ArgoCD 통합 테스트
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_github_actions_workflows():
    """통합 테스트: GitHub Actions 워크플로우 검증"""
    print("\n🧪 Testing GitHub Actions workflows...")

    workflows_path = Path(".github/workflows")
    assert workflows_path.exists(), "Workflows directory not found"

    workflow_files = list(workflows_path.glob("*.yml")) + list(
        workflows_path.glob("*.yaml")
    )
    assert len(workflow_files) > 0, "No workflow files found"

    for workflow_file in workflow_files:
        print(f"\n  Validating {workflow_file.name}...")

        with open(workflow_file, "r") as f:
            workflow = yaml.safe_load(f)

            # 필수 요소 검증
            assert "name" in workflow, f"Missing 'name' in {workflow_file.name}"
            assert "on" in workflow, f"Missing 'on' trigger in {workflow_file.name}"
            assert "jobs" in workflow, f"Missing 'jobs' in {workflow_file.name}"

            # Trigger 검증
            triggers = workflow["on"]
            if isinstance(triggers, dict):
                if "push" in triggers:
                    print(f"  ✅ Push trigger configured")
                if "pull_request" in triggers:
                    print(f"  ✅ Pull request trigger configured")
                if "workflow_dispatch" in triggers:
                    print(f"  ✅ Manual dispatch enabled")

            # Jobs 검증
            jobs = workflow["jobs"]
            for job_name, job_config in jobs.items():
                assert "runs-on" in job_config, f"Missing 'runs-on' in job {job_name}"
                assert "steps" in job_config, f"Missing 'steps' in job {job_name}"

                # Self-hosted runner 확인
                if job_config["runs-on"] == "self-hosted":
                    print(f"  ✅ Job '{job_name}' uses self-hosted runner")

                # 환경변수 확인
                if "env" in job_config or "env" in workflow:
                    print(f"  ✅ Environment variables configured")

    print(f"\n✅ Validated {len(workflow_files)} workflow files")
    return True


def test_docker_build_configuration():
    """통합 테스트: Docker 빌드 설정 검증"""
    print("\n🧪 Testing Docker build configuration...")

    # simple-cicd.yml 검증
    simple_cicd_path = Path(".github/workflows/simple-cicd.yml")
    if simple_cicd_path.exists():
        with open(simple_cicd_path, "r") as f:
            workflow = yaml.safe_load(f)

            build_job = workflow["jobs"].get("build-and-push", {})

            # Registry 설정 확인
            env = workflow.get("env", {})
            assert "REGISTRY" in env, "Registry not configured"
            assert env["REGISTRY"] == "registry.jclee.me", "Incorrect registry"

            print(f"✅ Registry configured: {env['REGISTRY']}")

            # Docker 빌드 스텝 확인
            steps = build_job.get("steps", [])
            docker_build_found = False

            for step in steps:
                if "run" in step and "docker build" in step["run"]:
                    docker_build_found = True
                    print("✅ Docker build command found")

                    # 태그 전략 확인
                    if "docker tag" in step["run"]:
                        print("✅ Multi-tag strategy configured")

            assert docker_build_found, "Docker build step not found"

    # gitops-cicd.yml 검증
    gitops_cicd_path = Path(".github/workflows/gitops-cicd.yml")
    if gitops_cicd_path.exists():
        with open(gitops_cicd_path, "r") as f:
            workflow = yaml.safe_load(f)

            # BuildKit 설정 확인
            build_job = workflow["jobs"].get("build-push", {})
            steps = build_job.get("steps", [])

            buildx_found = False
            for step in steps:
                if "uses" in step and "docker/setup-buildx-action" in step["uses"]:
                    buildx_found = True
                    print("✅ Docker Buildx configured")

                    # Insecure registry 설정 확인
                    if "with" in step and "config-inline" in step["with"]:
                        print("✅ Insecure registry support configured")

            assert buildx_found, "Docker Buildx not configured"

    return True


def test_kustomize_integration():
    """통합 테스트: Kustomize 통합 검증"""
    print("\n🧪 Testing Kustomize integration...")

    # GitOps 워크플로우에서 Kustomize 사용 확인
    gitops_cicd_path = Path(".github/workflows/gitops-cicd.yml")

    if gitops_cicd_path.exists():
        with open(gitops_cicd_path, "r") as f:
            content = f.read()

            assert "kustomize" in content, "Kustomize not found in workflow"
            assert (
                "kustomize edit set image" in content
            ), "Kustomize image update not configured"

            print("✅ Kustomize image update configured")

            # 환경별 업데이트 확인
            if "overlays/prod" in content:
                print("✅ Production overlay update configured")
            if "overlays/dev" in content:
                print("✅ Development overlay update configured")

    # Kustomization 파일 구조 확인
    base_kustomization = Path("k8s-gitops/base/kustomization.yaml")
    assert base_kustomization.exists(), "Base kustomization.yaml not found"

    with open(base_kustomization, "r") as f:
        kustomization = yaml.safe_load(f)

        assert "resources" in kustomization, "Resources not defined"
        assert len(kustomization["resources"]) > 0, "No resources listed"

        print(f"✅ Base kustomization has {len(kustomization['resources'])} resources")

    return True


def test_argocd_integration():
    """통합 테스트: ArgoCD 통합 검증"""
    print("\n🧪 Testing ArgoCD integration...")

    # ArgoCD 애플리케이션 파일들 확인
    argocd_apps = list(Path("k8s-gitops/argocd").glob("*.yaml"))
    assert len(argocd_apps) > 0, "No ArgoCD application files found"

    image_updater_configured = False

    for app_file in argocd_apps:
        with open(app_file, "r") as f:
            app = yaml.safe_load(f)

            # Image Updater 어노테이션 확인
            metadata = app.get("metadata", {})
            annotations = metadata.get("annotations", {})

            if any("argocd-image-updater" in key for key in annotations.keys()):
                image_updater_configured = True
                print(f"✅ Image Updater configured in {app_file.name}")

                # Update strategy 확인
                for key, value in annotations.items():
                    if "update-strategy" in key:
                        print(f"  Strategy: {value}")
                    if "image-list" in key:
                        print(f"  Image: {value}")

    assert image_updater_configured, "ArgoCD Image Updater not configured"

    # Sync policy 확인
    for app_file in argocd_apps:
        with open(app_file, "r") as f:
            app = yaml.safe_load(f)

            spec = app.get("spec", {})
            sync_policy = spec.get("syncPolicy", {})

            if "automated" in sync_policy:
                automated = sync_policy["automated"]

                if automated.get("prune"):
                    print(f"✅ Auto-prune enabled in {app_file.name}")
                if automated.get("selfHeal"):
                    print(f"✅ Self-heal enabled in {app_file.name}")

    return True


def test_version_tagging_strategy():
    """통합 테스트: 버전 태깅 전략"""
    print("\n🧪 Testing version tagging strategy...")

    workflows = Path(".github/workflows").glob("*.yml")

    version_strategies = []

    for workflow_file in workflows:
        with open(workflow_file, "r") as f:
            content = f.read()

            # 버전 생성 패턴 찾기
            if "date +%Y%m%d%H%M%S" in content:
                version_strategies.append("timestamp")
                print(f"✅ Timestamp versioning in {workflow_file.name}")

            if "github.sha" in content:
                version_strategies.append("git-sha")
                print(f"✅ Git SHA versioning in {workflow_file.name}")

            if "refs/tags/v" in content:
                version_strategies.append("git-tag")
                print(f"✅ Git tag versioning in {workflow_file.name}")

            # Multi-tag 전략 확인
            if content.count("tags:") > 0 or "docker tag" in content:
                print(f"✅ Multi-tag strategy in {workflow_file.name}")

    assert len(version_strategies) > 0, "No version strategy found"

    return True


def test_cicd_error_handling():
    """통합 테스트: CI/CD 에러 처리"""
    print("\n🧪 Testing CI/CD error handling...")

    workflows = Path(".github/workflows").glob("*.yml")

    error_handling_features = []

    for workflow_file in workflows:
        with open(workflow_file, "r") as f:
            workflow = yaml.safe_load(f)

            # continue-on-error 확인
            for job_name, job in workflow.get("jobs", {}).items():
                for step in job.get("steps", []):
                    if step.get("continue-on-error"):
                        error_handling_features.append("continue-on-error")
                        print(f"✅ Continue-on-error in {workflow_file.name}")

            # if conditions 확인
            for job_name, job in workflow.get("jobs", {}).items():
                if "if" in job:
                    error_handling_features.append("conditional-job")
                    print(f"✅ Conditional job execution in {workflow_file.name}")

                for step in job.get("steps", []):
                    if "if" in step:
                        error_handling_features.append("conditional-step")

            # needs와 결과 확인
            for job_name, job in workflow.get("jobs", {}).items():
                if "needs" in job:
                    error_handling_features.append("job-dependencies")

    print(f"\n✅ Error handling features: {len(set(error_handling_features))}")

    return True


def test_deployment_environments():
    """통합 테스트: 배포 환경 설정"""
    print("\n🧪 Testing deployment environments...")

    environments = []

    # Kustomize overlays 확인
    overlays_path = Path("k8s-gitops/overlays")
    if overlays_path.exists():
        for env_dir in overlays_path.iterdir():
            if env_dir.is_dir():
                environments.append(env_dir.name)
                print(f"✅ Environment configured: {env_dir.name}")

                # 환경별 설정 확인
                kustomization_file = env_dir / "kustomization.yaml"
                if kustomization_file.exists():
                    with open(kustomization_file, "r") as f:
                        kustomization = yaml.safe_load(f)

                        if "namespace" in kustomization:
                            print(f"  Namespace: {kustomization['namespace']}")

                        if "configMapGenerator" in kustomization:
                            print(f"  ConfigMap customization found")

                        if "images" in kustomization:
                            print(f"  Image customization found")

    assert len(environments) >= 1, "No environments configured"

    # ArgoCD 앱에서 환경 확인
    argocd_apps = Path("k8s-gitops/argocd/applications")
    if argocd_apps.exists():
        for app_file in argocd_apps.glob("*.yaml"):
            if "prod" in app_file.name.lower():
                print("✅ Production ArgoCD app found")
            if "dev" in app_file.name.lower():
                print("✅ Development ArgoCD app found")

    return True


def test_security_scanning():
    """통합 테스트: 보안 스캔 설정"""
    print("\n🧪 Testing security scanning configuration...")

    security_tools = []

    workflows = Path(".github/workflows").glob("*.yml")

    for workflow_file in workflows:
        with open(workflow_file, "r") as f:
            content = f.read()

            # 보안 도구 확인
            if "bandit" in content:
                security_tools.append("bandit")
                print(f"✅ Bandit (Python security) in {workflow_file.name}")

            if "safety" in content:
                security_tools.append("safety")
                print(f"✅ Safety (dependency check) in {workflow_file.name}")

            if "semgrep" in content:
                security_tools.append("semgrep")
                print(f"✅ Semgrep (SAST) in {workflow_file.name}")

            if "trivy" in content:
                security_tools.append("trivy")
                print(f"✅ Trivy (container scan) in {workflow_file.name}")

    if len(security_tools) == 0:
        print("⚠️ No security scanning tools configured")
    else:
        print(f"\n✅ Security tools configured: {len(set(security_tools))}")

    return True


def run_all_cicd_integration_tests():
    """모든 CI/CD 파이프라인 통합 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 Running CI/CD Pipeline Integration Tests")
    print("=" * 60)

    tests = [
        ("GitHub Actions Workflows", test_github_actions_workflows),
        ("Docker Build Configuration", test_docker_build_configuration),
        ("Kustomize Integration", test_kustomize_integration),
        ("ArgoCD Integration", test_argocd_integration),
        ("Version Tagging Strategy", test_version_tagging_strategy),
        ("Error Handling", test_cicd_error_handling),
        ("Deployment Environments", test_deployment_environments),
        ("Security Scanning", test_security_scanning),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} test failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} test failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_cicd_integration_tests()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
통합 테스트: Deployment System
Docker, Kubernetes, ArgoCD 배포 시스템 테스트
"""
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_dockerfile_build():
    """통합 테스트: Dockerfile 빌드 검증"""
    print("\n🧪 Testing Dockerfile build validation...")

    dockerfile_path = Path("deployment/Dockerfile")

    # 1. Dockerfile 존재 확인
    assert dockerfile_path.exists(), "Dockerfile not found"
    print("✅ Dockerfile exists")

    # 2. Dockerfile 구문 검증
    with open(dockerfile_path, "r") as f:
        content = f.read()

        # 필수 요소 확인
        assert "FROM python:" in content, "Missing base image"
        assert "WORKDIR" in content, "Missing WORKDIR"
        assert "COPY requirements.txt" in content, "Missing requirements copy"
        assert "RUN pip install" in content, "Missing pip install"
        assert "EXPOSE" in content, "Missing EXPOSE"
        assert "CMD" in content or "ENTRYPOINT" in content, "Missing CMD/ENTRYPOINT"

        print("✅ Dockerfile syntax validation passed")

        # 멀티스테이지 빌드 확인
        if content.count("FROM") > 1:
            print("✅ Multi-stage build detected")

        # 보안 설정 확인
        if "USER" in content and "USER root" not in content.split("USER")[-1]:
            print("✅ Non-root user configured")

    return True


def test_kubernetes_manifests():
    """통합 테스트: Kubernetes 매니페스트 검증"""
    print("\n🧪 Testing Kubernetes manifests...")

    k8s_base_path = Path("k8s-gitops/base")
    k8s_overlays_path = Path("k8s-gitops/overlays")

    # 1. 기본 매니페스트 검증
    required_files = ["deployment.yaml", "service.yaml", "kustomization.yaml"]

    for file_name in required_files:
        file_path = k8s_base_path / file_name
        assert file_path.exists(), "Missing {file_name}"

        # YAML 구문 검증
        try:
            with open(file_path, "r") as f:
                yaml_content = yaml.safe_load(f)
                assert yaml_content is not None, "Empty {file_name}"
        except yaml.YAMLError as e:
            assert False, "Invalid YAML in {file_name}: {e}"

    print("✅ Base manifests validation passed")

    # 2. Deployment 상세 검증
    with open(k8s_base_path / "deployment.yaml", "r") as f:
        deployment = yaml.safe_load(f)

        assert deployment["kind"] == "Deployment"
        assert "metadata" in deployment
        assert "spec" in deployment

        spec = deployment["spec"]
        assert "replicas" in spec
        assert "selector" in spec
        assert "template" in spec

        # Container 설정 검증
        containers = spec["template"]["spec"]["containers"]
        assert len(containers) > 0, "No containers defined"

        container = containers[0]
        assert "name" in container
        assert "image" in container
        assert "ports" in container

        # Health checks
        assert "livenessProbe" in container, "Missing liveness probe"
        assert "readinessProbe" in container, "Missing readiness probe"

        print("✅ Deployment configuration validation passed")

    # 3. Service 검증
    with open(k8s_base_path / "service.yaml", "r") as f:
        service = yaml.safe_load(f)

        assert service["kind"] == "Service"
        assert "spec" in service
        assert "ports" in service["spec"]
        assert "selector" in service["spec"]

        print("✅ Service configuration validation passed")

    # 4. Kustomization 검증
    for env in ["dev", "prod"]:
        kustomization_path = k8s_overlays_path / env / "kustomization.yaml"
        if kustomization_path.exists():
            with open(kustomization_path, "r") as f:
                kustomization = yaml.safe_load(f)

                assert "resources" in kustomization
                assert "namespace" in kustomization

                print(f"✅ {env.upper()} overlay validation passed")

    return True


def test_argocd_application():
    """통합 테스트: ArgoCD Application 설정"""
    print("\n🧪 Testing ArgoCD application configuration...")

    argocd_path = Path("k8s-gitops/argocd")

    # ArgoCD 앱 파일들 확인
    app_files = list(argocd_path.glob("*.yaml"))
    assert len(app_files) > 0, "No ArgoCD application files found"

    for app_file in app_files:
        with open(app_file, "r") as f:
            app_config = yaml.safe_load(f)

            assert app_config["kind"] == "Application"
            assert "metadata" in app_config
            assert "spec" in app_config

            spec = app_config["spec"]
            assert "source" in spec
            assert "destination" in spec
            assert "project" in spec

            # Source 검증
            source = spec["source"]
            assert "repoURL" in source
            assert "path" in source
            assert "targetRevision" in source

            # Destination 검증
            destination = spec["destination"]
            assert "server" in destination
            assert "namespace" in destination

            # Sync policy 검증
            if "syncPolicy" in spec:
                sync_policy = spec["syncPolicy"]
                if "automated" in sync_policy:
                    assert "prune" in sync_policy["automated"]
                    assert "selfHeal" in sync_policy["automated"]

            print(f"✅ {app_file.name} validation passed")

    return True


def test_docker_compose():
    """통합 테스트: Docker Compose 설정"""
    print("\n🧪 Testing Docker Compose configuration...")

    compose_path = Path("deployment/docker-compose.yml")

    if compose_path.exists():
        with open(compose_path, "r") as f:
            compose = yaml.safe_load(f)

            assert "services" in compose
            assert "blacklist" in compose["services"]

            blacklist_service = compose["services"]["blacklist"]
            assert "build" in blacklist_service or "image" in blacklist_service
            assert "ports" in blacklist_service
            assert "environment" in blacklist_service

            # 볼륨 확인
            if "volumes" in blacklist_service:
                print("✅ Volumes configured")

            # 네트워크 확인
            if "networks" in compose:
                print("✅ Networks configured")

            print("✅ Docker Compose validation passed")
    else:
        print("⚠️ Docker Compose file not found (optional)")

    return True


def test_deployment_scripts():
    """통합 테스트: 배포 스크립트 검증"""
    print("\n🧪 Testing deployment scripts...")

    scripts_path = Path("scripts")

    # 주요 배포 스크립트 확인
    important_scripts = ["k8s-management.sh", "deploy.sh", "check-deployment-status.sh"]

    found_scripts = []
    for script_name in important_scripts:
        script_path = scripts_path / script_name
        if script_path.exists():
            found_scripts.append(script_name)

            # 실행 권한 확인 (심볼릭)
            with open(script_path, "r") as f:
                first_line = f.readline()
                assert first_line.startswith(
                    "#!/bin/bash"
                ), "{script_name} missing shebang"

            print(f"✅ {script_name} validation passed")

    assert len(found_scripts) > 0, "No deployment scripts found"

    return True


def test_registry_configuration():
    """통합 테스트: Registry 설정 검증"""
    print("\n🧪 Testing registry configuration...")

    # GitHub Actions 워크플로우에서 registry 설정 확인
    workflows_path = Path(".github/workflows")

    registry_configs = []
    for workflow_file in workflows_path.glob("*.yml"):
        with open(workflow_file, "r") as f:
            content = f.read()

            if "REGISTRY" in content:
                # Registry 설정 추출
                for line in content.split("\n"):
                    if "REGISTRY:" in line or "registry:" in line:
                        registry_configs.append(line.strip())

    assert len(registry_configs) > 0, "No registry configuration found"

    # registry.jclee.me 사용 확인
    using_private_registry = any(
        "registry.jclee.me" in config for config in registry_configs
    )
    if using_private_registry:
        print("✅ Private registry (registry.jclee.me) configured")

    return True


def test_health_probes():
    """통합 테스트: Health Probe 설정 검증"""
    print("\n🧪 Testing health probe configuration...")

    deployment_path = Path("k8s-gitops/base/deployment.yaml")

    with open(deployment_path, "r") as f:
        deployment = yaml.safe_load(f)

        container = deployment["spec"]["template"]["spec"]["containers"][0]

        # Liveness probe
        liveness = container.get("livenessProbe", {})
        assert "httpGet" in liveness, "Liveness probe should use httpGet"
        assert liveness["httpGet"]["path"] == "/health", "Incorrect liveness path"
        assert "initialDelaySeconds" in liveness
        assert "periodSeconds" in liveness

        print("✅ Liveness probe validation passed")

        # Readiness probe
        readiness = container.get("readinessProbe", {})
        assert "httpGet" in readiness, "Readiness probe should use httpGet"
        assert readiness["httpGet"]["path"] == "/health", "Incorrect readiness path"
        assert "initialDelaySeconds" in readiness
        assert "periodSeconds" in readiness

        print("✅ Readiness probe validation passed")

        # 타이밍 검증
        assert (
            readiness["initialDelaySeconds"] < liveness["initialDelaySeconds"]
        ), "Readiness should start before liveness"

    return True


def test_resource_limits():
    """통합 테스트: 리소스 제한 설정"""
    print("\n🧪 Testing resource limits configuration...")

    deployment_path = Path("k8s-gitops/base/deployment.yaml")

    with open(deployment_path, "r") as f:
        deployment = yaml.safe_load(f)

        container = deployment["spec"]["template"]["spec"]["containers"][0]

        assert "resources" in container, "Missing resource configuration"
        resources = container["resources"]

        # Requests
        assert "requests" in resources, "Missing resource requests"
        assert "memory" in resources["requests"]
        assert "cpu" in resources["requests"]

        print(
            "✅ Resource requests: CPU={resources['requests']['cpu']}, Memory={resources['requests']['memory']}"
        )

        # Limits
        assert "limits" in resources, "Missing resource limits"
        assert "memory" in resources["limits"]
        assert "cpu" in resources["limits"]

        print(
            "✅ Resource limits: CPU={resources['limits']['cpu']}, Memory={resources['limits']['memory']}"
        )

    return True


def test_hpa_configuration():
    """통합 테스트: HPA (Horizontal Pod Autoscaler) 설정"""
    print("\n🧪 Testing HPA configuration...")

    hpa_path = Path("k8s-gitops/overlays/prod/hpa.yaml")

    if hpa_path.exists():
        with open(hpa_path, "r") as f:
            hpa = yaml.safe_load(f)

            assert hpa["kind"] == "HorizontalPodAutoscaler"
            spec = hpa["spec"]

            assert "scaleTargetRe" in spec
            assert "minReplicas" in spec
            assert "maxReplicas" in spec

            # 최소/최대 replicas 검증
            assert spec["minReplicas"] >= 1
            assert spec["maxReplicas"] > spec["minReplicas"]

            print(
                "✅ HPA configured: min={spec['minReplicas']}, max={spec['maxReplicas']}"
            )
    else:
        print("⚠️ HPA not configured (optional)")

    return True


def run_all_deployment_integration_tests():
    """모든 배포 통합 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 Running Deployment Integration Tests")
    print("=" * 60)

    tests = [
        ("Dockerfile Build", test_dockerfile_build),
        ("Kubernetes Manifests", test_kubernetes_manifests),
        ("ArgoCD Application", test_argocd_application),
        ("Docker Compose", test_docker_compose),
        ("Deployment Scripts", test_deployment_scripts),
        ("Registry Configuration", test_registry_configuration),
        ("Health Probes", test_health_probes),
        ("Resource Limits", test_resource_limits),
        ("HPA Configuration", test_hpa_configuration),
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
    success = run_all_deployment_integration_tests()
    sys.exit(0 if success else 1)

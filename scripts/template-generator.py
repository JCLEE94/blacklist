#!/usr/bin/env python3
"""
Template Generator - Kubernetes 매니페스트 및 ArgoCD 애플리케이션 생성기
NodePort 할당 정보를 기반으로 일관된 템플릿을 생성합니다.
"""

import json
import yaml
import os
from pathlib import Path
from datetime import datetime


class TemplateGenerator:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.nodeport_config_file = self.project_root / ".nodeport-current.json"
        self.templates_dir = self.project_root / "templates-generated"

    def load_nodeport_config(self):
        """NodePort 설정을 로드합니다."""
        if not self.nodeport_config_file.exists():
            raise FileNotFoundError(
                f"NodePort 설정 파일이 없습니다: {self.nodeport_config_file}"
            )

        with open(self.nodeport_config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_k8s_service_template(self, nodeport_config):
        """Kubernetes Service 템플릿을 생성합니다."""
        project_name = nodeport_config["project_name"]
        primary_port = nodeport_config["primary_nodeport"]

        service_template = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{project_name}-service",
                "namespace": project_name,
                "labels": {
                    "app": project_name,
                    "version": "v1",
                    "generated-by": "template-generator",
                },
            },
            "spec": {
                "type": "NodePort",
                "selector": {"app": project_name},
                "ports": [
                    {
                        "name": "http",
                        "port": 8541,
                        "targetPort": 8541,
                        "nodePort": primary_port,
                        "protocol": "TCP",
                    }
                ],
            },
        }

        return service_template

    def generate_msa_services_template(self, nodeport_config):
        """MSA 서비스들을 위한 템플릿을 생성합니다."""
        project_name = nodeport_config["project_name"]
        additional_ports = nodeport_config["additional_ports"]

        services = {}

        for service_name, nodeport in additional_ports.items():
            # 서비스별 포트 매핑
            service_port_map = {
                "api-gateway": 8080,
                "collection-service": 8000,
                "analytics-service": 8002,
                "blacklist-service": 8001,
            }

            target_port = service_port_map.get(service_name, 8080)

            service_template = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": f"{project_name}-{service_name}",
                    "namespace": project_name,
                    "labels": {
                        "app": f"{project_name}-{service_name}",
                        "service": service_name,
                        "generated-by": "template-generator",
                    },
                },
                "spec": {
                    "type": "NodePort",
                    "selector": {"app": f"{project_name}-{service_name}"},
                    "ports": [
                        {
                            "name": "http",
                            "port": target_port,
                            "targetPort": target_port,
                            "nodePort": nodeport,
                            "protocol": "TCP",
                        }
                    ],
                },
            }

            services[service_name] = service_template

        return services

    def generate_argocd_application_template(self, nodeport_config):
        """ArgoCD Application 템플릿을 생성합니다."""
        project_name = nodeport_config["project_name"]

        argocd_app = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": f"{project_name}-app",
                "namespace": "argocd",
                "labels": {"app": project_name, "generated-by": "template-generator"},
            },
            "spec": {
                "project": "default",
                "source": {
                    "repoURL": "https://github.com/JCLEE94/blacklist",
                    "targetRevision": "HEAD",
                    "path": "k8s/overlays/production",
                },
                "destination": {
                    "server": "https://kubernetes.default.svc",
                    "namespace": project_name,
                },
                "syncPolicy": {
                    "automated": {"prune": True, "selfHeal": True},
                    "syncOptions": ["CreateNamespace=true"],
                },
            },
        }

        return argocd_app

    def generate_kustomization_template(self, nodeport_config):
        """Kustomization 템플릿을 생성합니다."""
        project_name = nodeport_config["project_name"]
        primary_port = nodeport_config["primary_nodeport"]

        kustomization = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "metadata": {"name": f"{project_name}-kustomization"},
            "namespace": project_name,
            "resources": ["deployment.yaml", "service.yaml", "configmap.yaml"],
            "patchesStrategicMerge": ["service-patch.yaml"],
            "commonLabels": {"app": project_name, "generated-by": "template-generator"},
            "images": [
                {
                    "name": project_name,
                    "newName": f"registry.jclee.me/{project_name}",
                    "newTag": "latest",
                }
            ],
            "replicas": [{"name": f"{project_name}-deployment", "count": 2}],
        }

        return kustomization

    def save_templates(self, nodeport_config):
        """모든 템플릿을 파일로 저장합니다."""
        # 템플릿 디렉토리 생성
        self.templates_dir.mkdir(exist_ok=True)

        templates = {
            "k8s-service.yaml": self.generate_k8s_service_template(nodeport_config),
            "argocd-application.yaml": self.generate_argocd_application_template(
                nodeport_config
            ),
            "kustomization.yaml": self.generate_kustomization_template(nodeport_config),
        }

        # MSA 서비스 템플릿 추가
        msa_services = self.generate_msa_services_template(nodeport_config)
        for service_name, template in msa_services.items():
            templates[f"msa-{service_name}-service.yaml"] = template

        saved_files = []

        # 템플릿 저장
        for filename, template in templates.items():
            filepath = self.templates_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(template, f, default_flow_style=False, allow_unicode=True)
            saved_files.append(str(filepath))

        # 생성 정보 저장
        generation_info = {
            "generated_at": datetime.now().isoformat(),
            "project_name": nodeport_config["project_name"],
            "primary_nodeport": nodeport_config["primary_nodeport"],
            "templates_generated": len(saved_files),
            "files": saved_files,
        }

        info_file = self.templates_dir / "generation-info.json"
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(generation_info, f, indent=2, ensure_ascii=False)

        return generation_info

    def generate_all_templates(self):
        """모든 템플릿을 생성합니다."""
        try:
            nodeport_config = self.load_nodeport_config()
            generation_info = self.save_templates(nodeport_config)

            print(f"✅ 템플릿 생성 완료")
            print(f"프로젝트: {generation_info['project_name']}")
            print(f"기본 NodePort: {generation_info['primary_nodeport']}")
            print(f"생성된 템플릿: {generation_info['templates_generated']}개")
            print(f"저장 위치: {self.templates_dir}")

            return generation_info

        except Exception as e:
            print(f"❌ 템플릿 생성 실패: {e}")
            return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Kubernetes 및 ArgoCD 템플릿 생성기")
    parser.add_argument("--project-root", type=str, help="프로젝트 루트 디렉토리 경로")
    parser.add_argument("--output-dir", type=str, help="템플릿 출력 디렉토리")

    args = parser.parse_args()

    generator = TemplateGenerator(args.project_root)

    if args.output_dir:
        generator.templates_dir = Path(args.output_dir)

    generation_info = generator.generate_all_templates()

    if generation_info:
        print(f"\n📁 생성된 파일 목록:")
        for filepath in generation_info["files"]:
            print(f"  - {filepath}")


if __name__ == "__main__":
    main()

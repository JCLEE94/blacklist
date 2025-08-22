#!/usr/bin/env python3
"""
Auth Manager - ArgoCD 인증 확인 및 관리자
ArgoCD 클러스터 연결 상태와 인증을 확인합니다.
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime


class ArgoAuthManager:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.auth_config_file = self.project_root / ".argocd-auth-status.json"
        self.argocd_server = "argo.jclee.me"

    def check_argocd_cli_installed(self):
        """ArgoCD CLI 설치 여부를 확인합니다."""
        try:
            result = subprocess.run(
                ["argocd", "version", "--client"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0, (
                result.stdout if result.returncode == 0 else result.stderr
            )
        except Exception as e:
            return False, f"CLI 확인 실패: {e}"

    def check_server_connectivity(self):
        """ArgoCD 서버 연결성을 확인합니다."""
        try:
            # ArgoCD 서버 연결 테스트
            result = subprocess.run(
                [
                    "argocd",
                    "cluster",
                    "list",
                    "--server",
                    self.argocd_server,
                    "--grpc-web",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, "서버 연결 성공"
            else:
                # 인증이 필요한 경우일 수 있음
                if "authentication required" in result.stderr.lower():
                    return False, "인증이 필요합니다"
                elif "connection refused" in result.stderr.lower():
                    return False, "서버 연결 거부됨"
                else:
                    return False, f"연결 실패: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "서버 응답 시간 초과"
        except Exception as e:
            return False, f"연결 테스트 실패: {e}"

    def check_authentication_status(self):
        """현재 인증 상태를 확인합니다."""
        try:
            result = subprocess.run(
                [
                    "argocd",
                    "account",
                    "get-user-info",
                    "--server",
                    self.argocd_server,
                    "--grpc-web",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except Exception as e:
            return False, f"인증 상태 확인 실패: {e}"

    def list_applications(self):
        """ArgoCD 애플리케이션 목록을 가져옵니다."""
        try:
            result = subprocess.run(
                [
                    "argocd",
                    "app",
                    "list",
                    "--server",
                    self.argocd_server,
                    "--grpc-web",
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                apps = json.loads(result.stdout) if result.stdout.strip() else []
                return True, apps
            else:
                return False, result.stderr.strip()

        except json.JSONDecodeError as e:
            return False, f"JSON 파싱 실패: {e}"
        except Exception as e:
            return False, f"애플리케이션 목록 조회 실패: {e}"

    def check_project_application(self, project_name):
        """특정 프로젝트의 ArgoCD 애플리케이션을 확인합니다."""
        success, apps_or_error = self.list_applications()

        if not success:
            return False, apps_or_error

        # 프로젝트와 관련된 앱 찾기
        project_apps = []
        for app in apps_or_error:
            app_name = app.get("metadata", {}).get("name", "")
            if project_name in app_name.lower():
                project_apps.append(
                    {
                        "name": app_name,
                        "namespace": app.get("metadata", {}).get("namespace", ""),
                        "sync_status": app.get("status", {})
                        .get("sync", {})
                        .get("status", ""),
                        "health_status": app.get("status", {})
                        .get("health", {})
                        .get("status", ""),
                        "repo_url": app.get("spec", {})
                        .get("source", {})
                        .get("repoURL", ""),
                        "path": app.get("spec", {}).get("source", {}).get("path", ""),
                    }
                )

        return True, project_apps

    def verify_auth_and_generate_report(self):
        """전체 인증 상태를 확인하고 보고서를 생성합니다."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "server": self.argocd_server,
            "cli_installed": False,
            "server_connectivity": False,
            "authentication": False,
            "project_applications": [],
            "errors": [],
            "recommendations": [],
        }

        # 1. CLI 설치 확인
        cli_ok, cli_msg = self.check_argocd_cli_installed()
        report["cli_installed"] = cli_ok
        if not cli_ok:
            report["errors"].append(f"ArgoCD CLI: {cli_msg}")
            report["recommendations"].append(
                "ArgoCD CLI를 설치하세요: curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64"
            )

        # 2. 서버 연결성 확인
        if cli_ok:
            conn_ok, conn_msg = self.check_server_connectivity()
            report["server_connectivity"] = conn_ok
            if not conn_ok:
                report["errors"].append(f"서버 연결: {conn_msg}")
                if "인증이 필요" in conn_msg:
                    report["recommendations"].append(
                        f"ArgoCD 로그인: argocd login {self.argocd_server} --grpc-web"
                    )

        # 3. 인증 상태 확인
        if cli_ok and report["server_connectivity"]:
            auth_ok, auth_msg = self.check_authentication_status()
            report["authentication"] = auth_ok
            if not auth_ok:
                report["errors"].append(f"인증 상태: {auth_msg}")
                report["recommendations"].append("로그인이 필요합니다")

        # 4. 프로젝트 애플리케이션 확인
        if report["authentication"]:
            project_name = self.project_root.name
            app_ok, apps_or_error = self.check_project_application(project_name)
            if app_ok:
                report["project_applications"] = apps_or_error
                if not apps_or_error:
                    report["recommendations"].append(
                        f"'{project_name}' 관련 ArgoCD 애플리케이션이 없습니다. 새로 생성하는 것을 고려하세요."
                    )
            else:
                report["errors"].append(f"애플리케이션 조회: {apps_or_error}")

        # 5. 전체 상태 요약
        report["overall_status"] = all(
            [
                report["cli_installed"],
                report["server_connectivity"],
                report["authentication"],
            ]
        )

        # 보고서 저장
        with open(self.auth_config_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def display_report(self, report):
        """보고서를 화면에 표시합니다."""
        print(f"🔐 ArgoCD 인증 상태 보고서")
        print(f"서버: {report['server']}")
        print(f"확인 시간: {report['timestamp']}")
        print()

        # 상태 표시
        status_emoji = "✅" if report["overall_status"] else "❌"
        print(
            f"{status_emoji} 전체 상태: {'정상' if report['overall_status'] else '문제 있음'}"
        )

        # 세부 상태
        cli_emoji = "✅" if report["cli_installed"] else "❌"
        print(
            f"  {cli_emoji} CLI 설치: {'완료' if report['cli_installed'] else '필요'}"
        )

        conn_emoji = "✅" if report["server_connectivity"] else "❌"
        print(
            f"  {conn_emoji} 서버 연결: {'성공' if report['server_connectivity'] else '실패'}"
        )

        auth_emoji = "✅" if report["authentication"] else "❌"
        print(f"  {auth_emoji} 인증: {'성공' if report['authentication'] else '필요'}")

        # 프로젝트 애플리케이션
        if report["project_applications"]:
            print(
                f"\n📱 프로젝트 애플리케이션 ({len(report['project_applications'])}개):"
            )
            for app in report["project_applications"]:
                sync_emoji = "✅" if app["sync_status"] == "Synced" else "⚠️"
                health_emoji = "✅" if app["health_status"] == "Healthy" else "⚠️"
                print(
                    f"  {sync_emoji} {health_emoji} {app['name']} (Sync: {app['sync_status']}, Health: {app['health_status']})"
                )

        # 오류 및 권장사항
        if report["errors"]:
            print(f"\n❌ 오류 ({len(report['errors'])}개):")
            for error in report["errors"]:
                print(f"  - {error}")

        if report["recommendations"]:
            print(f"\n💡 권장사항 ({len(report['recommendations'])}개):")
            for rec in report["recommendations"]:
                print(f"  - {rec}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ArgoCD 인증 관리자")
    parser.add_argument(
        "--verify", action="store_true", help="인증 상태를 확인하고 보고서를 생성합니다"
    )
    parser.add_argument(
        "--show", action="store_true", help="저장된 보고서를 표시합니다"
    )
    parser.add_argument("--project-root", type=str, help="프로젝트 루트 디렉토리 경로")

    args = parser.parse_args()

    manager = ArgoAuthManager(args.project_root)

    if args.verify:
        print("🔍 ArgoCD 인증 상태 확인 중...")
        report = manager.verify_auth_and_generate_report()
        manager.display_report(report)
        print(f"\n💾 보고서 저장됨: {manager.auth_config_file}")
    elif args.show:
        if manager.auth_config_file.exists():
            with open(manager.auth_config_file, "r", encoding="utf-8") as f:
                report = json.load(f)
            manager.display_report(report)
        else:
            print("❌ 저장된 보고서가 없습니다. --verify를 사용하여 생성하세요.")
    else:
        # 기본 동작: 확인 후 표시
        print("🔍 ArgoCD 인증 상태 확인 중...")
        report = manager.verify_auth_and_generate_report()
        manager.display_report(report)


if __name__ == "__main__":
    main()

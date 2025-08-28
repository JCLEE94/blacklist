"""
동적 버전 관리 유틸리티
Git 정보를 기반으로 동적 버전을 생성
"""

import os
import subprocess
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_dynamic_version():
    """
    Git 정보를 기반으로 동적 버전 생성
    형식: 1.3.{커밋수}.{해시}

    Returns:
        str: 동적 버전 문자열
    """
    try:
        # 프로젝트 루트 디렉토리 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir

        # .git 디렉토리가 있는 루트 찾기
        while project_root != os.path.dirname(project_root):
            if os.path.exists(os.path.join(project_root, ".git")):
                break
            project_root = os.path.dirname(project_root)

        # Git 커밋 수 가져오기
        try:
            git_count = (
                subprocess.check_output(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=project_root,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except:
            git_count = "0"

        # Git 해시 가져오기 (짧은 버전)
        try:
            git_hash = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short=8", "HEAD"],
                    cwd=project_root,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except:
            git_hash = "unknown"

        # 동적 버전 생성: 1.3.{커밋수}.{해시}
        dynamic_version = f"1.3.{git_count}.{git_hash}"

        logger.info(f"Generated dynamic version: {dynamic_version}")
        return dynamic_version

    except Exception as e:
        logger.warning(f"Failed to generate dynamic version: {e}")
        return "1.3.1.unknown"


@lru_cache(maxsize=1)
def get_build_info():
    """
    상세한 빌드 정보 반환

    Returns:
        dict: 빌드 정보 딕셔너리
    """
    try:
        # 프로젝트 루트 디렉토리 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir

        while project_root != os.path.dirname(project_root):
            if os.path.exists(os.path.join(project_root, ".git")):
                break
            project_root = os.path.dirname(project_root)

        build_info = {}

        # Git 커밋 수
        try:
            build_info["git_count"] = (
                subprocess.check_output(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=project_root,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except:
            build_info["git_count"] = "0"

        # Git 해시 (짧은 버전)
        try:
            build_info["git_hash"] = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short=8", "HEAD"],
                    cwd=project_root,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except:
            build_info["git_hash"] = "unknown"

        # Git 브랜치
        try:
            build_info["git_branch"] = (
                subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=project_root,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except:
            build_info["git_branch"] = "main"

        # 마지막 커밋 날짜
        try:
            build_info["build_date"] = (
                subprocess.check_output(
                    ["git", "log", "-1", "--format=%ci"],
                    cwd=project_root,
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except:
            from datetime import datetime

            build_info["build_date"] = datetime.utcnow().isoformat()

        # 동적 버전
        build_info["version"] = get_dynamic_version()

        return build_info

    except Exception as e:
        logger.warning(f"Failed to get build info: {e}")
        return {
            "version": "1.3.1.unknown",
            "git_count": "0",
            "git_hash": "unknown",
            "git_branch": "main",
            "build_date": "unknown",
        }


def clear_version_cache():
    """버전 캐시 클리어 (개발/테스트용)"""
    get_dynamic_version.cache_clear()
    get_build_info.cache_clear()
    logger.info("Version cache cleared")

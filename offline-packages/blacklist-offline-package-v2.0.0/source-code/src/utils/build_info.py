"""
Build information utility
"""

from pathlib import Path


def get_build_info():
    """Get build information from .build_info file"""
    try:
        build_info_path = Path(__file__).parent.parent.parent / ".build_info"
        if build_info_path.exists():
            build_info = {}
            with open(build_info_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        build_info[key] = value.strip("'\"")
            return build_info
        else:
            # Fallback if build info file doesn't exist
            return {
                "BUILD_TIME": "Unknown",
                "BUILD_VERSION": "v2.1-dev",
                "BUILD_COMMIT": "development",
            }
    except Exception as e:
        return {
            "BUILD_TIME": "Error loading build info",
            "BUILD_VERSION": "v2.1-error",
            "BUILD_COMMIT": "unknown",
        }


def get_build_time():
    """Get formatted build time"""
    build_info = get_build_info()
    return build_info.get("BUILD_TIME", "Unknown")


def get_build_version():
    """Get build version"""
    build_info = get_build_info()
    return build_info.get("BUILD_VERSION", "v2.1-dev")


def get_build_commit():
    """Get build commit"""
    build_info = get_build_info()
    return build_info.get("BUILD_COMMIT", "unknown")

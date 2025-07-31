#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - Full Compact App Integration
"""
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Configure logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import the compact app
try:
    from src.core.app_compact import application

    logger.info("Successfully imported app_compact - using full-featured app")
except Exception as e:
    logger.error(f"Failed to import from app_compact: {e}")
    import traceback

    logger.error(traceback.format_exc())

    # If app_compact fails, create a minimal error app
    from flask import Flask, jsonify

    application = Flask(__name__)

    @application.route("/health")
    def health():
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Failed to load app_compact: {str(e)}",
                    "mode": "emergency_fallback",
                }
            ),
            503,
        )


# Main execution
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 2541))
    logger.info(f"Starting Blacklist App on port {port}")
    application.run(host="0.0.0.0", port=port, debug=False)

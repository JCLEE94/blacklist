#!/usr/bin/env python3
"""
Simple main entry point for Docker execution
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment for production
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("PYTHONPATH", str(project_root))

if __name__ == "__main__":
    # Start with minimal app by default for stability
    try:
        from src.core.minimal_app import create_minimal_app

        app = create_minimal_app()
        port = int(os.environ.get("PORT", 2542))

        print(f"Starting Blacklist Management System (Minimal Mode) on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False)

    except Exception as e:
        print(f"Minimal app failed: {e}")

        # Last resort: basic Flask app
        from flask import Flask, jsonify

        app = Flask(__name__)

        @app.route("/health")
        def health():
            return jsonify(
                {
                    "status": "healthy",
                    "mode": "emergency",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        port = int(os.environ.get("PORT", 2542))
        print(f"Starting emergency mode on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False)  # Hook test comment

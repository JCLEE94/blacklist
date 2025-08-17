#!/usr/bin/env python3
"""
Run the server directly
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['REGTECH_USERNAME'] = 'nextrade'
os.environ['REGTECH_PASSWORD'] = 'test_password'
os.environ['COLLECTION_ENABLED'] = 'true'
os.environ['FORCE_DISABLE_COLLECTION'] = 'false'
os.environ['PORT'] = '2542'

from src.core.app_compact import create_app

if __name__ == "__main__":
    app = create_app()
    print("🚀 Starting server on port 2542...")
    app.run(host='0.0.0.0', port=2542, debug=False)
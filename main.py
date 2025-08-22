#!/usr/bin/env python3
"""
Simple main entry point for Docker execution
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment for production
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('PYTHONPATH', str(project_root))

if __name__ == '__main__':
    try:
        # Try to import and run the main app
        from src.core.main import create_app
        
        app = create_app()
        port = int(os.environ.get('PORT', 2542))
        
        print(f"Starting Blacklist Management System on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"Failed to start application: {e}")
        
        # Fallback to minimal app
        try:
            from src.core.minimal_app import create_minimal_app
            app = create_minimal_app()
            port = int(os.environ.get('PORT', 2542))
            
            print(f"Starting minimal fallback app on port {port}")
            app.run(host='0.0.0.0', port=port, debug=False)
            
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            sys.exit(1)
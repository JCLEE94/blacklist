#!/usr/bin/env python3
"""
Blacklist Application Entry Point
Main entry point for the Blacklist Management System
"""

import sys
import os
# Add root directory to path to maintain imports
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from src.core.app_compact import create_app
import logging
import argparse
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Blacklist Management System')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', default=2542, type=int, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Starting Blacklist Management System v1.0.37-DEPLOY-TEST-{datetime.now().strftime('%H:%M:%S')} on {args.host}:{args.port}")
    
    try:
        app = create_app()
        
        if args.debug:
            logger.info("Debug mode enabled")
            app.run(host=args.host, port=args.port, debug=True)
        else:
            logger.info("Production mode")
            app.run(host=args.host, port=args.port, debug=False)
            
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
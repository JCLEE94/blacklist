#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - 전체 기능 포함
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and use the full application
from src.core.app_compact import create_compact_app, application

# For compatibility with existing deployment
if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    env = os.environ.get('FLASK_ENV', 'production')
    port = int(os.environ.get('PORT', 8541))
    
    app = create_compact_app(env)
    app.run(host='0.0.0.0', port=port, debug=(env == 'development'))
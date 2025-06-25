#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - 통합 서비스 엔트리 포인트
모든 기능을 하나의 서비스로 통합
"""
import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use app_compact as primary application
try:
    from src.core.app_compact import create_compact_app
    application = create_compact_app()
    logger.info("✅ app_compact 성공적으로 로드됨")
except ImportError as e:
    logger.error(f"❌ app_compact import 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)  # app_compact 실패시 종료 (minimal_app 사용 안함)
except Exception as e:
    logger.error(f"❌ app_compact 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    import argparse
    from src.config.settings import settings
    
    parser = argparse.ArgumentParser(description='Blacklist Management System')
    parser.add_argument('--port', type=int, default=settings.port, help='Port to run on')
    parser.add_argument('--host', default=settings.host, help='Host to bind to')
    parser.add_argument('--debug', action='store_true', default=settings.debug, help='Enable debug mode')
    
    args = parser.parse_args()
    
    # 설정 검증
    validation = settings.validate()
    if not validation['valid']:
        logger.error(f"Configuration errors: {validation['errors']}")
        sys.exit(1)
    
    if validation['warnings']:
        for warning in validation['warnings']:
            logger.warning(f"Configuration warning: {warning}")
    
    print(f"Starting {settings.app_name} v{settings.app_version} on {args.host}:{args.port}")
    print(f"Environment: {settings.environment}, Debug: {args.debug}")
    
    application.run(host=args.host, port=args.port, debug=args.debug)
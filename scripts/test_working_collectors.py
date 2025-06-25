#\!/usr/bin/env python3
"""
HAR 기반 수집기 통합 테스트
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import logging
from src.core.collection_manager import CollectionManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_collection_system():
    logger.info("=== HAR 기반 수집 시스템 테스트 ===")
    
    try:
        manager = CollectionManager()
        
        # 1. 초기 상태
        logger.info("1. 초기 상태 확인")
        status = manager.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 2. 수집 활성화
        logger.info("2. 수집 활성화")
        enable_result = manager.enable_collection()
        print(json.dumps(enable_result, indent=2, ensure_ascii=False))
        
        # 3. REGTECH 수집
        logger.info("3. REGTECH 수집 테스트")
        regtech_result = manager.trigger_regtech_collection()
        print(json.dumps(regtech_result, indent=2, ensure_ascii=False))
        
        # 4. SECUDIUM 수집
        logger.info("4. SECUDIUM 수집 테스트")
        secudium_result = manager.trigger_secudium_collection()
        print(json.dumps(secudium_result, indent=2, ensure_ascii=False))
        
        # 5. 최종 상태
        logger.info("5. 최종 상태 확인")
        final_status = manager.get_status()
        print(json.dumps(final_status, indent=2, ensure_ascii=False))
        
        # 결과 요약
        logger.info("=== 테스트 결과 요약 ===")
        if regtech_result.get('success'):
            logger.info(f"✅ REGTECH: {regtech_result.get('message')}")
        else:
            logger.error(f"❌ REGTECH: {regtech_result.get('message')}")
        
        if secudium_result.get('success'):
            logger.info(f"✅ SECUDIUM: {secudium_result.get('message')}")
        else:
            logger.error(f"❌ SECUDIUM: {secudium_result.get('message')}")
        
        total_ips = final_status.get('summary', {}).get('total_ips_collected', 0)
        logger.info(f"📊 총 수집된 IP: {total_ips:,}개")
        
        return True
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_collection_system()

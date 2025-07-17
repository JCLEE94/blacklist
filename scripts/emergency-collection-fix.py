#!/usr/bin/env python3
"""
긴급 수집 비활성화 스크립트
- 환경변수가 설정되어 있어도 무시되는 문제를 해결
- 모든 설정 소스에서 collection_enabled를 false로 강제 설정
"""

import json
import os
import sqlite3
from pathlib import Path

def fix_collection_status():
    """모든 수집 설정을 비활성화로 강제 설정"""
    
    # 1. Config 파일 수정
    config_path = Path("/app/instance/collection_config.json")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        config['collection_enabled'] = False
        config['sources']['regtech'] = False
        config['sources']['secudium'] = False
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Config 파일 업데이트: {config_path}")
    
    # 2. DB 설정 수정
    db_path = "/app/instance/blacklist.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # app_settings 테이블 확인 및 업데이트
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_settings'")
        if cursor.fetchone():
            cursor.execute("UPDATE app_settings SET value = 'false' WHERE key = 'collection_enabled'")
            print(f"✅ DB app_settings 업데이트: collection_enabled = false")
        
        conn.commit()
        conn.close()
    
    # 3. 환경변수 확인
    env_value = os.environ.get('COLLECTION_ENABLED', 'not set')
    print(f"ℹ️  환경변수 COLLECTION_ENABLED: {env_value}")
    
    print("\n🎯 수집 상태가 비활성화로 강제 설정되었습니다.")
    print("⚠️  애플리케이션 재시작이 필요할 수 있습니다.")

if __name__ == "__main__":
    fix_collection_status()
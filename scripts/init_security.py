#!/usr/bin/env python3
"""
보안 시스템 초기화 스크립트
API 키, JWT 토큰, 인증 시스템 설정
"""

import os
import sys
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def init_security_tables():
    """보안 관련 테이블 생성"""
    db_path = os.getenv("DATABASE_URL", "sqlite:///instance/blacklist.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")
    
    # 디렉토리 생성
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # API 키 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            usage_count INTEGER DEFAULT 0,
            last_used TIMESTAMP,
            permissions TEXT DEFAULT '["read"]'
        )
    """)
    
    # JWT 토큰 블랙리스트
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jti TEXT UNIQUE NOT NULL,
            token_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    
    # 사용자 세션
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ 보안 테이블 생성 완료")


def generate_default_api_key():
    """기본 API 키 생성"""
    db_path = os.getenv("DATABASE_URL", "sqlite:///instance/blacklist.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 기본 API 키 생성
    api_key = f"blk_{secrets.token_urlsafe(32)}"
    key_hash = secrets.token_hex(32)  # 실제로는 해시 함수 사용
    
    cursor.execute("""
        INSERT OR IGNORE INTO api_keys (key_hash, name, expires_at, permissions)
        VALUES (?, ?, ?, ?)
    """, (
        key_hash,
        "Default API Key",
        (datetime.utcnow() + timedelta(days=365)).isoformat(),
        '["read", "write", "admin"]'
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 기본 API 키 생성: {api_key}")
    print(f"   (이 키를 안전한 곳에 보관하세요)")
    
    return api_key


def update_env_file(api_key):
    """환경 변수 파일 업데이트"""
    env_path = project_root / ".env"
    
    # 기존 .env 읽기
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    
    # 보안 관련 환경 변수 추가/업데이트
    env_vars.update({
        'JWT_SECRET_KEY': env_vars.get('JWT_SECRET_KEY', secrets.token_urlsafe(32)),
        'SECRET_KEY': env_vars.get('SECRET_KEY', secrets.token_urlsafe(32)),
        'API_KEY_ENABLED': 'true',
        'JWT_ENABLED': 'true',
        'DEFAULT_API_KEY': api_key,
        'ADMIN_USERNAME': env_vars.get('ADMIN_USERNAME', 'admin'),
        'ADMIN_PASSWORD': env_vars.get('ADMIN_PASSWORD', secrets.token_urlsafe(16))
    })
    
    # .env 파일 작성
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print("✅ 환경 변수 파일 업데이트 완료")
    print(f"   Admin 계정: {env_vars['ADMIN_USERNAME']} / {env_vars['ADMIN_PASSWORD']}")


def init_security_config():
    """보안 설정 초기화"""
    config_path = project_root / "config" / "security.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    
    security_config = {
        "jwt": {
            "algorithm": "HS256",
            "access_token_expires": 3600,  # 1시간
            "refresh_token_expires": 604800  # 7일
        },
        "api_key": {
            "enabled": True,
            "header_name": "X-API-Key",
            "max_keys_per_user": 5
        },
        "rate_limiting": {
            "enabled": True,
            "default_limit": 100,
            "window_seconds": 60
        },
        "security_headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(security_config, f, indent=2)
    
    print("✅ 보안 설정 파일 생성 완료")


def main():
    """메인 실행 함수"""
    print("🔐 보안 시스템 초기화 시작")
    print("=" * 50)
    
    try:
        # 1. 보안 테이블 생성
        init_security_tables()
        
        # 2. 기본 API 키 생성
        api_key = generate_default_api_key()
        
        # 3. 환경 변수 업데이트
        update_env_file(api_key)
        
        # 4. 보안 설정 파일 생성
        init_security_config()
        
        print("\n" + "=" * 50)
        print("🎉 보안 시스템 초기화 완료!")
        print("\n📋 다음 단계:")
        print("1. 서비스 재시작: docker-compose restart")
        print("2. API 키 테스트: curl -H 'X-API-Key: <your-key>' http://localhost:32542/api/keys/verify")
        print("3. JWT 로그인: curl -X POST -H 'Content-Type: application/json' \\")
        print("              -d '{\"username\":\"admin\",\"password\":\"<password>\"}' \\")
        print("              http://localhost:32542/api/auth/login")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
애플리케이션 테스트 실행
"""
import os
import sys
from pathlib import Path

# 환경변수 설정
os.environ['DATABASE_URL'] = "postgresql://blacklist_user:blacklist_password_change_me@localhost:5432/blacklist"
os.environ['REDIS_URL'] = "redis://localhost:6379/0"
os.environ['FLASK_ENV'] = "development"
os.environ['PORT'] = "5000"

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    try:
        from src.core.app_compact import create_app
        
        app = create_app()
        print("🚀 애플리케이션 시작")
        print("📊 데이터베이스: PostgreSQL")
        print("🔗 캐시: Redis")
        print("🌐 URL: http://localhost:5000")
        print("❤️ 헬스체크: http://localhost:5000/health")
        print("📈 API 상태: http://localhost:5000/api/health")
        print("\n💡 Ctrl+C로 종료하세요\n")
        
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        print(f"❌ 애플리케이션 시작 실패: {e}")
        sys.exit(1)
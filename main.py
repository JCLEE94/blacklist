#!/usr/bin/env python3
"""
통합 블랙리스트 관리 시스템 - 통합 서비스 엔트리 포인트
모든 기능을 하나의 서비스로 통합
"""
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    # .env 파일 로드
    load_dotenv()
except ImportError:
    # dotenv가 없는 환경에서는 환경 변수만 사용
    print("Warning: python-dotenv not available, using environment variables only")

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# 🔴 보안 초기화 및 검사
def check_security_configuration():
    """보안 설정 확인 및 경고 출력"""
    force_disable = os.getenv("FORCE_DISABLE_COLLECTION", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    collection_enabled = os.getenv("COLLECTION_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    restart_protection = os.getenv("RESTART_PROTECTION", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )

    print("\n" + "=" * 80)
    print("🛡️  BLACKLIST 보안 상태 확인")
    print("=" * 80)

    if force_disable:
        print("✅ FORCE_DISABLE_COLLECTION=true - 모든 외부 수집 강제 차단")
        print("✅ 외부 인증 시도 없음 - 서버 안전 모드")
    else:
        print("⚠️  FORCE_DISABLE_COLLECTION=false - 수집 기능 활성화 가능")
        if collection_enabled:
            print("🚨 COLLECTION_ENABLED=true - 외부 인증 시도 발생 가능")
            print("🚨 REGTECH/SECUDIUM 서버 접속 시도 예상")
        else:
            print("✅ COLLECTION_ENABLED=false - 수집 기능 비활성화")

    if restart_protection:
        print("✅ RESTART_PROTECTION=true - 무한 재시작 보호 활성화")
    else:
        print("⚠️  RESTART_PROTECTION=false - 재시작 보호 비활성화")

    print("=" * 80)

    # 중요한 보안 경고
    if not force_disable and collection_enabled:
        print("🚨🚨🚨 중요 보안 경고 🚨🚨🚨")
        print("외부 서버 인증 시도가 활성화되어 있습니다!")
        print("무한 재시작 시 외부 서버에서 차단될 수 있습니다!")
        print("안전한 운영을 위해 FORCE_DISABLE_COLLECTION=true 권장")
        print("=" * 80)

        # 5초 대기로 관리자가 확인할 수 있도록
        import time

        for i in range(5, 0, -1):
            print(f"🚨 외부 인증 시도 시작까지 {i}초...")
            time.sleep(1)
        print("🔓 외부 인증 시도 활성화됨")
    else:
        print("✅ 안전 모드로 시작됨 - 외부 인증 시도 없음")

    print("=" * 80 + "\n")


# 데이터베이스 스키마 자동 수정
def ensure_database_schema():
    """데이터베이스 스키마 확인 및 수정"""
    import sqlite3

    # DATABASE_URL 환경변수에서 경로 추출 (컨테이너 환경 우선)
    database_url = os.getenv("DATABASE_URL", "sqlite:////app/instance/blacklist.db")
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
    else:
        # fallback to settings
        from src.config.settings import settings
        db_path = str(settings.instance_dir / "blacklist.db")
    
    # instance 디렉토리는 db_path에서 추출
    instance_dir = os.path.dirname(db_path)

    # instance 디렉토리 생성
    try:
        os.makedirs(instance_dir, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to create instance directory: {e}")

    # 데이터베이스가 없으면 init_database 실행
    if not os.path.exists(db_path):
        logger.info(f"데이터베이스가 없습니다. 새로 생성합니다: {db_path}")
        try:
            # 보안상 os.system() 대신 직접 import해서 호출
            sys.path.append(current_dir)
            from init_database import init_database_enhanced

            if init_database_enhanced():
                logger.info("✅ 데이터베이스 초기화 성공")
            else:
                logger.error("❌ 데이터베이스 초기화 실패")
                raise Exception("Database initialization failed")
        except ImportError as e:
            logger.error(f"❌ init_database 모듈 import 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 중 오류: {e}")
            raise
        return

    logger.info(f"데이터베이스 스키마 확인 중: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 기본 테이블 생성 (없는 경우)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                source VARCHAR(50) NOT NULL,
                detection_date TIMESTAMP,
                reason TEXT,
                threat_level VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """
        )

        # 인덱스 생성
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ip_address ON blacklist_ip(ip_address)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON blacklist_ip(source)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_is_active ON blacklist_ip(is_active)"
        )

        conn.commit()
        logger.info("✅ 데이터베이스 스키마 확인 완료")

    except Exception as e:
        logger.error(f"데이터베이스 초기화 오류: {e}")
        if "conn" in locals():
            conn.rollback()
    finally:
        if "conn" in locals():
            conn.close()


# 권한 문제 해결을 위한 디렉토리 생성 및 권한 설정
def ensure_directories_with_permissions():
    """필요한 디렉토리 생성 및 권한 설정"""
    from src.config.settings import settings

    # 설정에서 디렉토리 경로 가져오기
    directories = [
        settings.instance_dir,
        settings.data_dir,
        settings.logs_dir,
        settings.data_dir / "by_detection_month",
    ]

    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            # 디렉토리가 이미 존재하더라도 권한 재설정 시도
            try:
                os.chmod(str(directory), 0o755)  # 보안상 777 대신 755 사용
            except Exception as e:
                logger.warning(f"Failed to set permissions for {directory}: {e}")
        except Exception as e:
            logger.warning(f"Failed to create directory {directory}: {e}")


# 권한 설정 먼저 실행
ensure_directories_with_permissions()

# 🔴 보안 설정 확인 (애플리케이션 시작 전)
check_security_configuration()

# 애플리케이션 시작 전 스키마 확인
ensure_database_schema()

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

if __name__ == "__main__":
    import argparse

    from src.config.settings import settings

    parser = argparse.ArgumentParser(description="Blacklist Management System")
    parser.add_argument(
        "--port", type=int, default=settings.port, help="Port to run on"
    )
    parser.add_argument("--host", default=settings.host, help="Host to bind to")
    parser.add_argument(
        "--debug", action="store_true", default=settings.debug, help="Enable debug mode"
    )

    args = parser.parse_args()

    # 설정 검증
    validation = settings.validate()
    if not validation["valid"]:
        logger.error(f"Configuration errors: {validation['errors']}")
        sys.exit(1)

    if validation["warnings"]:
        for warning in validation["warnings"]:
            logger.warning(f"Configuration warning: {warning}")

    print(
        f"Starting {settings.app_name} v{settings.app_version} on {args.host}:{args.port}"
    )
    print(f"Environment: {settings.environment}, Debug: {args.debug}")

    application.run(host=args.host, port=args.port, debug=args.debug)

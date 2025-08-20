#!/usr/bin/env python3
"""
로그 정리 및 최적화 스크립트
"""
import os
import logging
from pathlib import Path

def setup_production_logging():
    """프로덕션 환경 로그 설정"""
    
    # 루트 로거 레벨을 WARNING으로 설정 (INFO 로그 줄이기)
    logging.getLogger().setLevel(logging.WARNING)
    
    # 특정 모듈들의 로그 레벨 조정
    noisy_loggers = [
        'werkzeug',
        'urllib3',
        'requests',
        'sqlalchemy.engine',
        'sqlalchemy.pool',
        'src.core.app.middleware',
        'src.utils.structured_logging',
        'src.core.blacklist_unified.statistics_service'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    # 중요한 모듈만 INFO 레벨 유지
    important_loggers = [
        'src.core.app_compact',
        'src.core.app.blueprints',
        'src.api.cicd_monitoring_routes'
    ]
    
    for logger_name in important_loggers:
        logging.getLogger(logger_name).setLevel(logging.INFO)
    
    print("✅ 로그 레벨 최적화 완료")

def cleanup_old_logs():
    """오래된 로그 파일 정리"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return
    
    # 7일 이상 된 로그 파일 삭제
    import time
    current_time = time.time()
    week_in_seconds = 7 * 24 * 60 * 60
    
    deleted_count = 0
    for log_file in logs_dir.glob("*.log*"):
        if log_file.stat().st_mtime < (current_time - week_in_seconds):
            log_file.unlink()
            deleted_count += 1
    
    print(f"✅ {deleted_count}개의 오래된 로그 파일 삭제")

if __name__ == "__main__":
    setup_production_logging()
    cleanup_old_logs()
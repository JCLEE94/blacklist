"""
수집 관리 라우트 - 통합 모듈
분리된 수집 관련 모듈들을 하나로 통합
"""

import logging
from flask import Blueprint

from .collection_status_routes import collection_status_bp
from .collection_trigger_routes import collection_trigger_bp
from .collection_logs_routes import collection_logs_bp

logger = logging.getLogger(__name__)

# 메인 수집 라우트 블루프린트
collection_routes_bp = Blueprint("collection_routes", __name__)

# 서브 블루프린트들 등록
collection_routes_bp.register_blueprint(collection_status_bp)
collection_routes_bp.register_blueprint(collection_trigger_bp)
collection_routes_bp.register_blueprint(collection_logs_bp)

# Export
__all__ = ['collection_routes_bp']

logger.info("Collection routes initialized with modular structure")
logger.info(f"Registered blueprints: collection_status, collection_trigger, collection_logs")

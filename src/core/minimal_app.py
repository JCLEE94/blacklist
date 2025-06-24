#!/usr/bin/env python3
"""
최소한의 Flask 앱 - 기본 API 기능만 제공
"""
import os
import logging
from flask import Flask
from flask_cors import CORS

from .simple_api import register_simple_api
from .collection_routes import register_collection_routes

logger = logging.getLogger(__name__)

def create_minimal_app() -> Flask:
    """최소한의 Flask 애플리케이션 생성"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, '..', '..')
    project_root = os.path.abspath(project_root)
    
    template_folder = os.path.join(project_root, 'templates')
    static_folder = os.path.join(project_root, 'static')
    
    app = Flask(__name__, 
               template_folder=template_folder,
               static_folder=static_folder)
    
    # 기본 설정
    app.config.update({
        'SECRET_KEY': 'dev-secret-key-change-in-production',
        'DEBUG': False,
        'TESTING': False
    })
    
    # CORS 활성화
    CORS(app)
    
    # 간단한 API 라우트 등록
    register_simple_api(app)
    
    # 컬렉션 라우트 등록
    try:
        register_collection_routes(app)
        logger.info("Collection routes registered")
    except Exception as e:
        logger.error(f"Failed to register collection routes: {e}")
    
    # 웹 UI 라우트 등록
    try:
        from src.web.routes import web_bp
        app.register_blueprint(web_bp)
        logger.info("Web UI routes registered")
    except Exception as e:
        logger.error(f"Failed to register web routes: {e}")
    
    # Add global template context for build time
    @app.context_processor
    def inject_build_info():
        from pathlib import Path
        try:
            build_info_path = Path('.build_info')
            if build_info_path.exists():
                with open(build_info_path, 'r') as f:
                    for line in f:
                        if line.startswith('BUILD_TIME='):
                            build_time = line.split('=', 1)[1].strip("'\"")
                            return {'build_time': build_time}
            return {'build_time': '2025-06-18 18:55:33 KST'}
        except:
            return {'build_time': '2025-06-18 18:55:33 KST'}
    
    logger.info("Minimal app created successfully")
    return app
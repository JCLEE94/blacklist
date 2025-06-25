#!/usr/bin/env python3
"""
Simple API routes for minimal Flask app
"""
import os
import json
import logging
from flask import Flask, jsonify, render_template
from datetime import datetime

logger = logging.getLogger(__name__)

def register_simple_api(app: Flask):
    """Register simple API routes"""
    
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        # Get build time from environment variable
        build_time = os.environ.get('BUILD_TIME', 'Unknown')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'blacklist-api',
            'version': '1.0.0',
            'build_time': build_time
        })
    
    @app.route('/api/stats')
    def stats():
        """Simple stats endpoint"""
        try:
            # 데이터베이스 파일 확인
            db_path = os.path.join(app.instance_path, 'blacklist.db')
            db_exists = os.path.exists(db_path)
            
            return jsonify({
                'status': 'ok',
                'database': 'available' if db_exists else 'not_found',
                'total_ips': 0,
                'active_sources': 0,
                'last_update': None
            })
        except Exception as e:
            logger.error(f"Error in stats endpoint: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/blacklist/active')
    def blacklist_active():
        """Return empty blacklist for now"""
        return '', 200, {'Content-Type': 'text/plain'}
    
    @app.route('/api/fortigate')
    def fortigate():
        """FortiGate External Connector format"""
        return jsonify({
            'status': 'success',
            'data': []
        })
    
    logger.info("Simple API routes registered")
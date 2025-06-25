#!/usr/bin/env python3
"""
Collection routes for Flask app with full functionality
"""
import logging
from flask import Flask, jsonify, request
from datetime import datetime

logger = logging.getLogger(__name__)

def register_collection_routes(app: Flask):
    """Register collection management routes"""
    
    # Import service here to avoid circular imports
    from .collection_service import get_collection_service
    
    @app.route('/api/collection/status')
    def collection_status():
        """Collection status endpoint"""
        service = get_collection_service()
        return jsonify(service.get_status())
    
    @app.route('/api/collection/enable', methods=['POST'])
    def enable_collection():
        """Enable collection"""
        service = get_collection_service()
        return jsonify(service.enable_collection())
    
    @app.route('/api/collection/disable', methods=['POST'])
    def disable_collection():
        """Disable collection"""
        service = get_collection_service()
        return jsonify(service.disable_collection())
    
    @app.route('/api/collection/regtech/trigger', methods=['POST'])
    def trigger_regtech():
        """Trigger REGTECH collection"""
        service = get_collection_service()
        data = request.get_json() or {}
        result = service.trigger_regtech(data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/api/collection/secudium/trigger', methods=['POST'])
    def trigger_secudium():
        """Trigger SECUDIUM collection"""
        service = get_collection_service()
        data = request.get_json() or {}
        result = service.trigger_secudium(data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    logger.info("Collection routes registered with full functionality")
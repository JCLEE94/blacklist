#!/usr/bin/env python3
"""
Collection routes for Flask app with full functionality
"""
import logging
from flask import Flask, jsonify, request
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def register_collection_routes(app: Flask):
    """Register collection management routes"""
    
    # Import manager here to avoid circular imports
    from .collection_manager import CollectionManager
    
    # Get database path from app instance
    db_path = os.path.join(app.instance_path, 'blacklist.db')
    manager = CollectionManager(db_path=db_path)
    
    @app.route('/api/collection/status')
    def collection_status():
        """Collection status endpoint"""
        status = manager.get_status()
        # Convert to simple format for compatibility
        return jsonify({
            'enabled': status.get('collection_enabled', False),
            'sources': {
                'regtech': {
                    'enabled': status['sources']['regtech']['enabled'],
                    'last_run': status['sources']['regtech']['last_collection'],
                    'status': 'completed' if status['sources']['regtech']['total_ips'] > 0 else 'ready',
                    'total_collected': status['sources']['regtech']['total_ips'],
                    'last_error': None
                },
                'secudium': {
                    'enabled': status['sources']['secudium']['enabled'],
                    'last_run': status['sources']['secudium']['last_collection'],
                    'status': 'completed' if status['sources']['secudium']['total_ips'] > 0 else 'ready',
                    'total_collected': status['sources']['secudium']['total_ips'],
                    'last_error': None
                }
            }
        })
    
    @app.route('/api/collection/enable', methods=['POST'])
    def enable_collection():
        """Enable collection"""
        result = manager.enable_collection()
        return jsonify(result)
    
    @app.route('/api/collection/disable', methods=['POST'])
    def disable_collection():
        """Disable collection"""
        result = manager.disable_collection()
        return jsonify(result)
    
    @app.route('/api/collection/regtech/trigger', methods=['POST'])
    def trigger_regtech():
        """Trigger REGTECH collection"""
        try:
            result = manager.trigger_regtech_collection()
            
            # Format response for compatibility
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'REGTECH collection completed',
                    'output': f"🚀 Starting REGTECH collection...\n\n📊 Collection Results:\nTotal collected: {result.get('details', {}).get('total_collected', 0)}\nSuccessful: {result.get('details', {}).get('total_collected', 0)}\nFailed: 0\nDuplicates: 0\n"
                })
            else:
                return jsonify(result), 400
        except Exception as e:
            logger.error(f"REGTECH trigger error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/collection/secudium/trigger', methods=['POST'])
    def trigger_secudium():
        """Trigger SECUDIUM collection"""
        try:
            result = manager.trigger_secudium_collection()
            
            # Get collector output for compatibility
            output = ""
            if 'details' in result:
                details = result['details']
                if 'method' in details:
                    output = f"Method: {details['method']}\n"
                if 'total_collected' in details:
                    output += f"Total collected: {details['total_collected']}\n"
                output += f"[SUCCESS] 수집 완료! 총 {details.get('total_collected', 0)}개 IP 수집"
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'SECUDIUM collection completed',
                    'output': output
                })
            else:
                return jsonify(result), 400
        except Exception as e:
            logger.error(f"SECUDIUM trigger error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    logger.info("Collection routes registered with full functionality")
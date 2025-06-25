#!/usr/bin/env python3
"""
Collection routes for minimal Flask app
"""
import logging
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

def register_collection_routes(app: Flask):
    """Register collection management routes"""
    
    @app.route('/api/collection/status')
    def collection_status():
        """Collection status endpoint"""
        return jsonify({
            'enabled': False,
            'sources': {
                'regtech': {'enabled': False, 'last_run': None},
                'secudium': {'enabled': False, 'last_run': None}
            }
        })
    
    @app.route('/api/collection/enable', methods=['POST'])
    def enable_collection():
        """Enable collection (placeholder)"""
        return jsonify({'status': 'disabled', 'message': 'Collection not available in minimal mode'})
    
    @app.route('/api/collection/disable', methods=['POST'])
    def disable_collection():
        """Disable collection (placeholder)"""
        return jsonify({'status': 'disabled', 'message': 'Already disabled'})
    
    logger.info("Collection routes registered")
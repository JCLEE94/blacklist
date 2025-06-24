"""
Collection Management Control Routes
Provides endpoints for managing and triggering data collection from REGTECH and SECUDIUM
"""
from flask import Blueprint, jsonify, request, g
from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CollectionControlRoutes:
    """Collection management control routes for enabling/disabling and triggering collections"""
    
    def __init__(self, collection_manager):
        self.collection_manager = collection_manager
        logger.info("CollectionControlRoutes initialized")
    
    def register_routes(self, app):
        """Register collection control routes with the Flask app"""
        
        # Create blueprint here to avoid duplicate registration
        collection_bp = Blueprint('collection', __name__, url_prefix='/api/collection')
        
        @collection_bp.route('/status', methods=['GET'])
        def get_collection_status():
            """Get collection service status and configuration"""
            try:
                status = {
                    'collection_enabled': self.collection_manager.collection_enabled if self.collection_manager else False,
                    'sources': {
                        'regtech': {
                            'enabled': True,
                            'credentials_configured': bool(os.environ.get('REGTECH_USERNAME')),
                            'last_collection': None
                        },
                        'secudium': {
                            'enabled': True,
                            'credentials_configured': bool(os.environ.get('SECUDIUM_USERNAME')),
                            'last_collection': None
                        }
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                # Check for recent collection files
                if self.collection_manager:
                    regtech_files = list(Path('data/regtech').glob('regtech_*.json'))
                    if regtech_files:
                        latest_regtech = max(regtech_files, key=lambda f: f.stat().st_mtime)
                        status['sources']['regtech']['last_collection'] = datetime.fromtimestamp(
                            latest_regtech.stat().st_mtime
                        ).isoformat()
                    
                    secudium_files = list(Path('data/secudium').glob('secudium_*.json'))
                    if secudium_files:
                        latest_secudium = max(secudium_files, key=lambda f: f.stat().st_mtime)
                        status['sources']['secudium']['last_collection'] = datetime.fromtimestamp(
                            latest_secudium.stat().st_mtime
                        ).isoformat()
                
                return jsonify(status)
                
            except Exception as e:
                logger.error(f"Error getting collection status: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @collection_bp.route('/enable', methods=['POST'])
        def enable_collection():
            """Enable collection service (clears existing data)"""
            try:
                if not self.collection_manager:
                    return jsonify({
                        'error': 'Collection manager not available',
                        'timestamp': datetime.now().isoformat()
                    }), 503
                
                result = self.collection_manager.enable_collection()
                
                return jsonify({
                    'message': 'Collection enabled',
                    'cleared_data': result.get('cleared_data', {}),
                    'collection_enabled': True,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error enabling collection: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @collection_bp.route('/disable', methods=['POST'])
        def disable_collection():
            """Disable collection service"""
            try:
                if not self.collection_manager:
                    return jsonify({
                        'error': 'Collection manager not available',
                        'timestamp': datetime.now().isoformat()
                    }), 503
                
                self.collection_manager.disable_collection()
                
                return jsonify({
                    'message': 'Collection disabled',
                    'collection_enabled': False,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error disabling collection: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @collection_bp.route('/regtech/trigger', methods=['POST'])
        def trigger_regtech_collection():
            """Trigger manual REGTECH collection"""
            try:
                if not self.collection_manager:
                    return jsonify({
                        'error': 'Collection manager not available',
                        'timestamp': datetime.now().isoformat()
                    }), 503
                
                # Get parameters from request
                data = request.get_json() or {}
                start_date = data.get('start_date')
                end_date = data.get('end_date')
                
                # Check if collection is enabled
                if not self.collection_manager.collection_enabled:
                    return jsonify({
                        'error': 'Collection is disabled. Enable it first via /api/collection/enable',
                        'timestamp': datetime.now().isoformat()
                    }), 400
                
                # Trigger collection
                result = self.collection_manager.trigger_regtech_collection()
                
                return jsonify({
                    'message': 'REGTECH collection triggered',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error triggering REGTECH collection: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        @collection_bp.route('/secudium/trigger', methods=['POST'])
        def trigger_secudium_collection():
            """Trigger manual SECUDIUM collection"""
            try:
                if not self.collection_manager:
                    return jsonify({
                        'error': 'Collection manager not available',
                        'timestamp': datetime.now().isoformat()
                    }), 503
                
                # Check if collection is enabled
                if not self.collection_manager.collection_enabled:
                    return jsonify({
                        'error': 'Collection is disabled. Enable it first via /api/collection/enable',
                        'timestamp': datetime.now().isoformat()
                    }), 400
                
                # Trigger collection
                result = self.collection_manager.trigger_secudium_collection()
                
                return jsonify({
                    'message': 'SECUDIUM collection triggered',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error triggering SECUDIUM collection: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        # Register blueprint
        app.register_blueprint(collection_bp)
        logger.info("Collection control routes registered")

def register_collection_control_routes(app):
    """Register collection control routes with the Flask app (function-level registration)"""
    try:
        # Get collection manager from container
        from .container import get_container
        container = get_container()
        try:
            collection_manager = container.resolve('collection_manager')
        except:
            logger.warning("Collection manager not available in container")
            collection_manager = None
        
        # Create routes instance and register
        routes = CollectionControlRoutes(collection_manager)
        routes.register_routes(app)
        logger.info("Collection control routes registered via function")
    except Exception as e:
        logger.error(f"Failed to register collection control routes: {e}")
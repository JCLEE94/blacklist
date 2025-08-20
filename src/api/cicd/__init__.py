#!/usr/bin/env python3
"""
CI/CD Monitoring Module
Provides a unified interface for all CI/CD monitoring functionality

This module consolidates build monitoring, health checks, deployment operations,
and reporting into a single, easy-to-use interface while maintaining modularity.
"""

from .build_routes import build_monitoring_bp, check_github_actions_status, check_registry_status
from .health_routes import health_monitoring_bp, generate_verification_recommendations, determine_overall_status
from .deployment_routes import deployment_bp, check_argocd_status, generate_next_steps
from .reporting_routes import reporting_bp, generate_recommendations

# For backward compatibility - create a combined blueprint
from flask import Blueprint

# Main CI/CD monitoring blueprint that combines all sub-modules
cicd_monitoring_bp = Blueprint("cicd_monitoring", __name__, url_prefix="/cicd")

# Register all sub-blueprints with the main blueprint
def register_cicd_blueprints(app):
    """Register all CI/CD monitoring blueprints with the Flask app"""
    app.register_blueprint(build_monitoring_bp)
    app.register_blueprint(health_monitoring_bp)
    app.register_blueprint(deployment_bp)
    app.register_blueprint(reporting_bp)


# Export all important functions for easy access
__all__ = [
    'cicd_monitoring_bp',
    'build_monitoring_bp',
    'health_monitoring_bp', 
    'deployment_bp',
    'reporting_bp',
    'register_cicd_blueprints',
    'check_github_actions_status',
    'check_registry_status',
    'check_argocd_status',
    'generate_verification_recommendations',
    'determine_overall_status',
    'generate_next_steps',
    'generate_recommendations'
]

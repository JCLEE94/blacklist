import logging

from flask import Blueprint, Flask, jsonify, redirect, render_template, request, url_for

logger = logging.getLogger(__name__)

"""Flask integration for error handling"""

from werkzeug.exceptions import HTTPException

from .core_handler import ErrorHandler
from .custom_errors import BaseError


def register_error_handlers(app, error_handler: ErrorHandler = None):
    """랩스크 앱에 에러 핸들러 등록"""
    if error_handler is None:
        error_handler = ErrorHandler()

    @app.errorhandler(BaseError)
    def handle_base_error(error):
        error_handler.log_error(error)
        response, status_code = error_handler.format_error_response(error)
        return jsonify(response), status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        error_handler.log_error(error)
        response, status_code = error_handler.format_error_response(error)
        return jsonify(response), status_code

    @app.errorhandler(Exception)
    def handle_exception(error):
        error_handler.log_error(error)
        response, status_code = error_handler.format_error_response(error)
        return jsonify(response), status_code

    # 에러 통계 엔드포인트 추가
    @app.route("/api/errors/stats", methods=["GET"])
    def get_error_stats():
        """에러 통계 조회"""
        return jsonify(error_handler.get_error_stats())

    return error_handler

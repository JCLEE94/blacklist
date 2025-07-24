"""
Response Builder Service

Provides standardized response formatting for API endpoints.
Creates consistent JSON responses with proper HTTP status codes.
"""
from flask import Response, jsonify
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """
    Utility class for building standardized API responses
    """

    @staticmethod
    def success(
        data: Any = None, message: str = None, metadata: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        Create a successful response

        Args:
            data: Response data
            message: Success message
            metadata: Additional metadata

        Returns:
            Flask Response object with 200 status
        """
        response_data = {"success": True, "timestamp": datetime.now().isoformat()}

        if data is not None:
            response_data["data"] = data

        if message:
            response_data["message"] = message

        if metadata:
            response_data["metadata"] = metadata

        return jsonify(response_data), 200

    @staticmethod
    def error(
        message: str,
        status_code: int = 500,
        error_code: str = None,
        details: Any = None,
    ) -> Response:
        """
        Create an error response

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application-specific error code
            details: Additional error details

        Returns:
            Flask Response object with specified status code
        """
        response_data = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat(),
        }

        if error_code:
            response_data["error_code"] = error_code

        if details:
            response_data["details"] = details

        return jsonify(response_data), status_code

    @staticmethod
    def server_error(
        message: str = "Internal server error", error_id: str = None
    ) -> Response:
        """
        Create a 500 server error response

        Args:
            message: Error message
            error_id: Unique error identifier for tracking

        Returns:
            Flask Response object with 500 status
        """
        response_data = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat(),
        }

        if error_id:
            response_data["error_id"] = error_id

        return jsonify(response_data), 500

    @staticmethod
    def validation_error(message: Union[str, Dict], details: Any = None) -> Response:
        """
        Create a 400 validation error response

        Args:
            message: Validation error message or dict
            details: Additional validation details

        Returns:
            Flask Response object with 400 status
        """
        response_data = {"success": False, "timestamp": datetime.now().isoformat()}

        if isinstance(message, dict):
            response_data["error"] = message.get("message", "Validation failed")
            response_data["validation_errors"] = message
        else:
            response_data["error"] = message

        if details:
            response_data["details"] = details

        return jsonify(response_data), 400

    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> Response:
        """
        Create a 401 unauthorized response

        Args:
            message: Unauthorized message

        Returns:
            Flask Response object with 401 status
        """
        response_data = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(response_data), 401

    @staticmethod
    def not_found(resource: str = "Resource") -> Response:
        """
        Create a 404 not found response

        Args:
            resource: Name of the resource that was not found

        Returns:
            Flask Response object with 404 status
        """
        response_data = {
            "success": False,
            "error": f"{resource} not found",
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(response_data), 404

    @staticmethod
    def rate_limit_exceeded(retry_after: int = None) -> Response:
        """
        Create a 429 rate limit exceeded response

        Args:
            retry_after: Seconds to wait before retrying

        Returns:
            Flask Response object with 429 status
        """
        response_data = {
            "success": False,
            "error": "Rate limit exceeded",
            "timestamp": datetime.now().isoformat(),
        }

        if retry_after:
            response_data["retry_after"] = retry_after

        response = jsonify(response_data)
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)

        return response, 429

    @staticmethod
    def fortigate(
        ips: List[str], category: str = "Blacklist", metadata: Optional[Dict] = None
    ) -> Response:
        """
        Create FortiGate External Connector format response

        Args:
            ips: List of IP addresses
            category: Category name for FortiGate
            metadata: Additional metadata

        Returns:
            Flask Response object with FortiGate JSON format
        """
        entries = []
        for ip in ips:
            entries.append(
                {
                    "ip": ip,
                    "type": "ip",
                    "threat_level": "high",
                    "category": "malicious",
                }
            )

        response_data = {
            "category": category,
            "entries": entries,
            "metadata": {
                "total_count": len(ips),
                "generated_at": datetime.now().isoformat(),
                "format": "fortigate_external_connector",
                **(metadata or {}),
            },
        }

        return jsonify(response_data), 200

    @staticmethod
    def batch_result(
        results: List[Dict],
        success_count: int,
        failure_count: int,
        metadata: Optional[Dict] = None,
    ) -> Response:
        """
        Create batch operation result response

        Args:
            results: List of batch operation results
            success_count: Number of successful operations
            failure_count: Number of failed operations
            metadata: Additional metadata

        Returns:
            Flask Response object with batch results
        """
        response_data = {
            "success": True,
            "batch_results": {
                "results": results,
                "summary": {
                    "total": len(results),
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_rate": round((success_count / len(results)) * 100, 2)
                    if results
                    else 0,
                },
            },
            "timestamp": datetime.now().isoformat(),
        }

        if metadata:
            response_data["metadata"] = metadata

        return jsonify(response_data), 200

    @staticmethod
    def export(data: Any, format_type: str = "json") -> Response:
        """
        Create export data response

        Args:
            data: Data to export
            format_type: Export format (json, txt, csv, etc.)

        Returns:
            Flask Response object with export data
        """
        if format_type.lower() == "json":
            response_data = {
                "success": True,
                "export_data": data,
                "format": format_type,
                "exported_at": datetime.now().isoformat(),
            }
            return jsonify(response_data), 200

        elif format_type.lower() == "txt":
            # For text format, return plain text response
            if isinstance(data, list):
                content = "\n".join(str(item) for item in data)
            else:
                content = str(data)

            return (
                Response(
                    content,
                    mimetype="text/plain",
                    headers={
                        "Content-Disposition": f'attachment; filename=export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                    },
                ),
                200,
            )

        else:
            # Default to JSON for unsupported formats
            response_data = {
                "success": True,
                "export_data": data,
                "format": format_type,
                "exported_at": datetime.now().isoformat(),
                "note": f"Format {format_type} not specifically supported, returned as JSON",
            }
            return jsonify(response_data), 200

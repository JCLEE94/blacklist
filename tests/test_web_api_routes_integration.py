#!/usr/bin/env python3
"""
Integration tests for web API routes

Tests complex API endpoint interactions and edge cases.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.api_routes import (
    api_bp,
    api_stats_simple,
    download_daily_ips,
    export_data,
    get_daily_ips,
    get_month_details,
)


class TestGetMonthDetails:
    """Test the get_month_details endpoint"""

    def test_get_month_details_success(self):
        """Test successful month details retrieval"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-01")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["month"] == "2024-01"
            assert data["data"]["total_ips"] == 1500
            assert "daily_breakdown" in data["data"]

    def test_get_month_details_daily_breakdown(self):
        """Test month details daily breakdown structure"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-02")

            data = response.get_json()
            daily_breakdown = data["data"]["daily_breakdown"]

            assert len(daily_breakdown) == 28  # Simplified to 28 days
            assert all("date" in day for day in daily_breakdown)
            assert all("count" in day for day in daily_breakdown)

    @patch("datetime.datetime.strptime", side_effect=ValueError("Invalid date"))
    def test_get_month_details_invalid_date(self, mock_strptime):
        """Test month details with invalid date format"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/invalid-date")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False


class TestGetDailyIps:
    """Test the get_daily_ips endpoint"""

    def test_get_daily_ips_success(self):
        """Test successful daily IPs retrieval"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-01/daily/2024-01-15")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["date"] == "2024-01-15"
            assert data["count"] == 50
            assert len(data["ips"]) == 50

    def test_get_daily_ips_structure(self):
        """Test daily IPs data structure"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-01/daily/2024-01-01")

            data = response.get_json()
            ips = data["ips"]

            # Check structure of first IP entry
            first_ip = ips[0]
            assert "ip" in first_ip
            assert "source" in first_ip
            assert "country" in first_ip
            assert "attack_type" in first_ip
            assert "detection_date" in first_ip

            # Check variety in sources and attack types
            sources = set(ip["source"] for ip in ips)
            assert "REGTECH" in sources or "SECUDIUM" in sources


class TestDownloadDailyIps:
    """Test the download_daily_ips endpoint"""

    @patch("src.web.api_routes.get_daily_ips")
    def test_download_daily_ips_success(self, mock_get_daily):
        """Test successful daily IPs download"""
        # Mock get_daily_ips response
        mock_response = Mock()
        mock_response.get_json.return_value = {
            "success": True,
            "ips": [
                {"ip": "192.168.1.1", "source": "REGTECH", "attack_type": "Malware"},
                {"ip": "192.168.1.2", "source": "SECUDIUM", "attack_type": "Phishing"},
            ],
        }
        mock_get_daily.return_value = mock_response

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-01/daily/2024-01-01/download")

            assert response.status_code == 200
            assert response.mimetype == "text/plain"
            assert "attachment" in response.headers["Content-Disposition"]

    @patch("src.web.api_routes.get_daily_ips")
    def test_download_daily_ips_get_data_failure(self, mock_get_daily):
        """Test download when getting daily data fails"""
        # Mock failed get_daily_ips response
        mock_response = Mock()
        mock_response.get_json.return_value = {"success": False}
        mock_get_daily.return_value = mock_response

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-01/daily/2024-01-01/download")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False

    @patch("src.web.api_routes.get_daily_ips", side_effect=Exception("Download error"))
    def test_download_daily_ips_exception(self, mock_get_daily):
        """Test download when exception occurs"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/month/2024-01/daily/2024-01-01/download")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False


class TestExportData:
    """Test the export_data endpoint"""

    @patch("src.web.api_routes.get_stats")
    def test_export_data_json(self, mock_get_stats):
        """Test JSON export"""
        mock_stats = {"total_ips": 1000, "sources": {"REGTECH": 600, "SECUDIUM": 400}}
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/export/json")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"] == mock_stats

    @patch("src.web.api_routes.get_stats")
    def test_export_data_csv(self, mock_get_stats):
        """Test CSV export"""
        mock_stats = {"total_ips": 1000, "sources": {"REGTECH": 600, "SECUDIUM": 400}}
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/export/csv")

            assert response.status_code == 200
            assert response.mimetype == "text/csv"
            assert "attachment" in response.headers["Content-Disposition"]

            # Check CSV content structure
            content = response.get_data(as_text=True)
            lines = content.strip().split("\n")
            assert "Source,Count,Percentage" in lines[0]

    @patch("src.web.api_routes.get_stats")
    def test_export_data_csv_zero_total(self, mock_get_stats):
        """Test CSV export with zero total IPs"""
        mock_stats = {"total_ips": 0, "sources": {"REGTECH": 0, "SECUDIUM": 0}}
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/export/csv")

            assert response.status_code == 200
            content = response.get_data(as_text=True)
            # Should handle division by zero gracefully
            assert "0%" in content

    def test_export_data_unsupported_format(self):
        """Test export with unsupported format"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/export/xml")

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "Unsupported format" in data["error"]

    @patch("src.web.api_routes.get_stats", side_effect=Exception("Export error"))
    def test_export_data_exception(self, mock_get_stats):
        """Test export when exception occurs"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/export/json")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False


class TestApiStatsSimple:
    """Test the api_stats_simple endpoint"""

    @patch("src.web.api_routes.get_stats")
    def test_api_stats_simple_success(self, mock_get_stats):
        """Test successful simple stats retrieval"""
        mock_stats = {
            "total_ips": 1500,
            "active_ips": 800,
            "sources": {"REGTECH": 600, "SECUDIUM": 400, "OTHER": 300},
            "last_updated": "2024-01-01T12:00:00",
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/stats-simple")

            assert response.status_code == 200
            data = response.get_json()

            assert data["total"] == 1500
            assert data["active"] == 800
            assert data["sources"] == 3  # Number of sources
            assert data["last_update"] == "2024-01-01T12:00:00"

    @patch("src.web.api_routes.get_stats")
    def test_api_stats_simple_empty_stats(self, mock_get_stats):
        """Test simple stats with empty data"""
        mock_stats = {
            "total_ips": 0,
            "active_ips": 0,
            "sources": {},
            "last_updated": None,
        }
        mock_get_stats.return_value = mock_stats

        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/stats-simple")

            assert response.status_code == 200
            data = response.get_json()

            assert data["total"] == 0
            assert data["active"] == 0
            assert data["sources"] == 0

    @patch("src.web.api_routes.get_stats", side_effect=Exception("Stats error"))
    def test_api_stats_simple_exception(self, mock_get_stats):
        """Test simple stats when exception occurs"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.get("/api/stats-simple")

            assert response.status_code == 500
            data = response.get_json()

            assert data["total"] == 0
            assert data["active"] == 0
            assert data["sources"] == 0
            assert "error" in data


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_malformed_json_request(self):
        """Test handling of malformed JSON requests"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post(
                "/api/search", data='{"invalid": json}', content_type="application/json"
            )

            # Should handle malformed JSON gracefully
            assert response.status_code in [400, 500]

    def test_very_long_ip_address(self):
        """Test handling of very long IP address strings"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        long_ip = "x" * 1000  # Very long string

        with app.test_client() as client:
            response = client.post("/api/search", json={"ip": long_ip})

            # Should handle gracefully without crashing
            assert response.status_code in [200, 400]

    def test_unicode_in_search(self):
        """Test handling of unicode characters in search"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post("/api/search", json={"ip": "🚀192.168.1.1🚀"})

            # Should handle unicode gracefully
            assert response.status_code in [200, 400]


if __name__ == "__main__":
    pytest.main([__file__])

#!/usr/bin/env python3
"""
Unit tests for analytics route endpoints
Tests V2 analytics API endpoints and statistical analysis routes.
"""

import json
import unittest.mock as mock
from datetime import datetime, timedelta

import pytest
from flask import Flask

from src.core.routes.analytics_routes import analytics_routes_bp
from src.core.v2_routes.analytics_routes import analytics_v2_bp


class TestAnalyticsRoutes:
    """Test cases for analytics route endpoints"""

    @pytest.fixture
    def app(self):
        """Create Flask test application"""
        app = Flask(__name__)
        app.config["TESTING"] = True

        # Register blueprints
        app.register_blueprint(analytics_routes_bp)
        app.register_blueprint(analytics_v2_bp, url_prefix="/api/v2")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_service(self):
        """Mock unified service"""
        service = mock.Mock()
        service.get_system_health.return_value = {
            "total_ips": 100,
            "active_ips": 90,
            "regtech_count": 60,
            "secudium_count": 30,
            "public_count": 10,
        }
        return service

    @pytest.fixture
    def mock_v2_service(self):
        """Mock V2 API service"""
        service = mock.Mock()
        service.get_analytics_summary.return_value = {
            "success": True,
            "summary": {"total_ips": 100, "active_ips": 90, "period_days": 30},
        }
        service.get_threat_level_analysis.return_value = {
            "threat_levels": {"high": 10, "medium": 50, "low": 40}
        }
        service.blacklist_manager = mock.Mock()
        service.blacklist_manager.get_daily_trend_data.return_value = [
            {"date": "2023-01-01", "unique_ips": 10},
            {"date": "2023-01-02", "unique_ips": 15},
            {"date": "2023-01-03", "unique_ips": 12},
        ]
        service.blacklist_manager.get_stats_for_period.return_value = {
            "total_ips": 100,
            "sources": [
                {"source": "regtech", "count": 60},
                {"source": "secudium", "count": 40},
            ],
        }
        service.blacklist_manager.get_country_statistics.return_value = [
            {"country": "CN", "ip_count": 30, "avg_confidence": 0.8},
            {"country": "US", "ip_count": 25, "avg_confidence": 0.7},
            {"country": "RU", "ip_count": 20, "avg_confidence": 0.9},
        ]
        return service

    def test_get_system_stats_success(self, client, mock_service):
        """Test successful system statistics retrieval"""
        with mock.patch("src.core.routes.analytics_routes.service", mock_service):
            response = client.get("/api/stats")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["total_ips"] == 100
            assert data["active_ips"] == 90

    def test_get_system_stats_exception(self, client, mock_service):
        """Test system statistics with exception"""
        mock_service.get_system_health.side_effect = Exception("Health error")

        with mock.patch("src.core.routes.analytics_routes.service", mock_service):
            with mock.patch(
                "src.core.routes.analytics_routes.create_error_response",
                return_value={"error": "Health error"},
            ):
                response = client.get("/api/stats")

                assert response.status_code == 500

    def test_get_blacklist_with_metadata_success(self, client):
        """Test successful blacklist metadata retrieval"""
        mock_cursor = mock.Mock()
        mock_cursor.fetchone.side_effect = [
            [100],  # total_ips
            [90],  # active_ips
            [10],  # expired_ips
            [5],  # expiring_soon
            [2],  # expiring_warning
        ]

        mock_conn = mock.Mock()
        mock_conn.cursor.return_value = mock_cursor

        with mock.patch("sqlite3.connect", return_value=mock_conn):
            response = client.get("/api/blacklist/metadata")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "expiry_stats" in data
            assert data["expiry_stats"]["total"] == 100
            assert data["expiry_stats"]["active"] == 90
            assert "pagination" in data

    def test_get_blacklist_with_metadata_with_pagination(self, client):
        """Test blacklist metadata with pagination parameters"""
        mock_cursor = mock.Mock()
        mock_cursor.fetchone.side_effect = [[100], [90], [10], [5], [2]]
        mock_conn = mock.Mock()
        mock_conn.cursor.return_value = mock_cursor

        with mock.patch("sqlite3.connect", return_value=mock_conn):
            response = client.get("/api/blacklist/metadata?page=2&per_page=20")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["pagination"]["page"] == 2
            assert data["pagination"]["per_page"] == 20

    def test_get_blacklist_with_metadata_exception(self, client):
        """Test blacklist metadata with database exception"""
        with mock.patch("sqlite3.connect", side_effect=Exception("DB error")):
            with mock.patch(
                "src.core.routes.analytics_routes.create_error_response",
                return_value={"error": "DB error"},
            ):
                response = client.get("/api/blacklist/metadata")

                assert response.status_code == 500

    def test_api_monthly_data_success(self, client, mock_service):
        """Test successful monthly data retrieval"""
        with mock.patch("src.core.routes.analytics_routes.service", mock_service):
            response = client.get("/api/stats/monthly")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "data" in data
            assert isinstance(data["data"], list)

    def test_api_monthly_data_alternative_route(self, client, mock_service):
        """Test monthly data retrieval via alternative route"""
        with mock.patch("src.core.routes.analytics_routes.service", mock_service):
            response = client.get("/api/stats/monthly-data")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_api_monthly_data_exception(self, client, mock_service):
        """Test monthly data with exception"""
        mock_service.get_system_health.side_effect = Exception("Monthly error")

        with mock.patch("src.core.routes.analytics_routes.service", mock_service):
            response = client.get("/api/stats/monthly")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False

    # V2 Analytics API Tests

    def test_v2_get_analytics_summary_success(self, client, mock_v2_service):
        """Test V2 analytics summary success"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/summary")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_v2_get_analytics_summary_with_period(self, client, mock_v2_service):
        """Test V2 analytics summary with custom period"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/summary?period=60")

            assert response.status_code == 200
            mock_v2_service.get_analytics_summary.assert_called_with(60)

    def test_v2_get_analytics_summary_exception(self, client, mock_v2_service):
        """Test V2 analytics summary with exception"""
        mock_v2_service.get_analytics_summary.side_effect = Exception("V2 error")

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/summary")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data

    def test_v2_get_analytics_trends_success(self, client):
        """Test V2 analytics trends success"""
        response = client.get("/api/v2/analytics/trends")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["trend_type"] == "time_series"
        assert "data" in data
        assert "analysis" in data

    def test_v2_get_analytics_trends_with_period(self, client):
        """Test V2 analytics trends with custom period"""
        response = client.get("/api/v2/analytics/trends?period=60")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["trend_period"] == 60

    def test_v2_get_analytics_by_period_week(self, client, mock_v2_service):
        """Test V2 analytics by period - week"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/week")

            assert response.status_code == 200
            mock_v2_service.get_analytics_summary.assert_called_with(7)

    def test_v2_get_analytics_by_period_month(self, client, mock_v2_service):
        """Test V2 analytics by period - month"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/month")

            assert response.status_code == 200
            mock_v2_service.get_analytics_summary.assert_called_with(30)

    def test_v2_get_analytics_by_period_invalid(self, client, mock_v2_service):
        """Test V2 analytics by period - invalid period defaults to 30"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/invalid")

            assert response.status_code == 200
            mock_v2_service.get_analytics_summary.assert_called_with(30)

    def test_v2_get_threat_levels_success(self, client, mock_v2_service):
        """Test V2 threat levels analysis success"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/threat-levels")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "threat_levels" in data

    def test_v2_get_threat_levels_exception(self, client, mock_v2_service):
        """Test V2 threat levels with exception"""
        mock_v2_service.get_threat_level_analysis.side_effect = Exception(
            "Threat error"
        )

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/threat-levels")

            assert response.status_code == 500

    def test_v2_get_trend_analysis_success(self, client, mock_v2_service):
        """Test V2 detailed trend analysis success"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/trends/detailed")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "trend_analysis" in data
            assert "daily_data" in data
            assert data["trend_analysis"]["direction"] in [
                "increasing",
                "decreasing",
                "stable",
                "insufficient_data",
            ]

    def test_v2_get_trend_analysis_with_days(self, client, mock_v2_service):
        """Test V2 trend analysis with custom days parameter"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/trends/detailed?days=60")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["period_days"] == 60
            mock_v2_service.blacklist_manager.get_daily_trend_data.assert_called_with(
                60
            )

    def test_v2_get_trend_analysis_insufficient_data(self, client, mock_v2_service):
        """Test V2 trend analysis with insufficient data"""
        mock_v2_service.blacklist_manager.get_daily_trend_data.return_value = []

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/trends/detailed")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["trend_analysis"]["direction"] == "insufficient_data"

    def test_v2_get_trend_analysis_exception(self, client, mock_v2_service):
        """Test V2 trend analysis with exception"""
        mock_v2_service.blacklist_manager.get_daily_trend_data.side_effect = Exception(
            "Trend error"
        )

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/trends/detailed")

            assert response.status_code == 500

    def test_v2_get_source_analysis_success(self, client, mock_v2_service):
        """Test V2 source analysis success"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/sources")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "source_analysis" in data
            assert "sources" in data
            assert "period" in data

            # Check that sources are sorted by IP count
            sources = data["sources"]
            if len(sources) > 1:
                assert sources[0]["ip_count"] >= sources[1]["ip_count"]

    def test_v2_get_source_analysis_with_days(self, client, mock_v2_service):
        """Test V2 source analysis with custom days parameter"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/sources?days=60")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["period"]["days"] == 60

    def test_v2_get_source_analysis_exception(self, client, mock_v2_service):
        """Test V2 source analysis with exception"""
        mock_v2_service.blacklist_manager.get_stats_for_period.side_effect = Exception(
            "Source error"
        )

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/sources")

            assert response.status_code == 500

    def test_v2_get_geo_analysis_success(self, client, mock_v2_service):
        """Test V2 geographic analysis success"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/geo")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "geographic_analysis" in data
            assert "continental_distribution" in data
            assert "detailed_countries" in data

            # Check that percentages are calculated
            countries = data["detailed_countries"]
            for country in countries:
                assert "percentage" in country
                assert country["percentage"] >= 0

    def test_v2_get_geo_analysis_with_limit(self, client, mock_v2_service):
        """Test V2 geographic analysis with custom limit"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/geo?limit=10")

            assert response.status_code == 200
            mock_v2_service.blacklist_manager.get_country_statistics.assert_called_with(
                10
            )

    def test_v2_get_geo_analysis_continental_distribution(
        self, client, mock_v2_service
    ):
        """Test V2 geographic analysis continental distribution"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/geo")

            assert response.status_code == 200
            data = json.loads(response.data)

            continental_dist = data["continental_distribution"]
            assert "Asia" in continental_dist  # CN is mapped to Asia
            assert "North America" in continental_dist  # US is mapped to North America

    def test_v2_get_geo_analysis_exception(self, client, mock_v2_service):
        """Test V2 geographic analysis with exception"""
        mock_v2_service.blacklist_manager.get_country_statistics.side_effect = (
            Exception("Geo error")
        )

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            response = client.get("/api/v2/analytics/geo")

            assert response.status_code == 500

    def test_v2_service_initialization(self, mock_v2_service):
        """Test V2 service initialization"""
        from src.core.v2_routes.analytics_routes import init_service

        init_service(mock_v2_service)

        # Import the service variable to check if it was set
        from src.core.v2_routes.analytics_routes import service

        assert service is mock_v2_service

    def test_caching_decorators(self, client, mock_v2_service):
        """Test that caching decorators are applied correctly"""
        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            # The unified_cache decorator should be applied to certain endpoints
            # We can't directly test caching behavior in unit tests, but we can
            # verify the endpoints work

            response1 = client.get("/api/v2/analytics/summary")
            response2 = client.get("/api/v2/analytics/threat-levels")
            response3 = client.get("/api/v2/analytics/week")

            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response3.status_code == 200

    def test_error_handling_consistency(self, client, mock_v2_service):
        """Test consistent error handling across V2 endpoints"""
        mock_v2_service.get_analytics_summary.side_effect = Exception("Test error")
        mock_v2_service.get_threat_level_analysis.side_effect = Exception("Test error")

        with mock.patch("src.core.v2_routes.analytics_routes.service", mock_v2_service):
            endpoints = [
                "/api/v2/analytics/summary",
                "/api/v2/analytics/threat-levels",
                "/api/v2/analytics/week",
            ]

            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 500
                data = json.loads(response.data)
                assert "error" in data
                assert data["error"] == "Test error"


if __name__ == "__main__":
    pytest.main([__file__])

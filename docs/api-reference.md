---
layout: default
title: API Reference
description: Complete API documentation for Blacklist Management System
---

# API Reference

Complete API documentation for Blacklist Management System v1.0.34.

## 🚀 Overview

The Blacklist Management System provides a comprehensive REST API for threat intelligence management, data collection, and system monitoring.

### Base URL
- **Docker**: `http://localhost:32542`
- **Local Development**: `http://localhost:8541`

### API Version
- **Current Version**: v2
- **Legacy Support**: v1 (deprecated)

## 🔐 Authentication

### JWT Token Authentication
Most endpoints require JWT authentication.

```bash
# Login to get JWT token
curl -X POST http://localhost:32542/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 900
}

# Use token in subsequent requests
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:32542/api/blacklist/active
```

## 📋 Health & Status Endpoints

### GET /health
Basic health check endpoint.

```bash
curl http://localhost:32542/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-13T12:00:00Z",
  "version": "1.0.34"
}
```

### GET /api/health
Detailed health check with component status.

```bash
curl http://localhost:32542/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-13T12:00:00Z",
  "version": "1.0.34",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 2.5,
      "schema_version": "2.0.0"
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1.2,
      "memory_usage": "156MB"
    },
    "credentials": {
      "status": "healthy",
      "regtech": "valid",
      "secudium": "valid"
    }
  },
  "metrics": {
    "active_ips": 45678,
    "last_collection": "2025-08-13T11:30:00Z",
    "api_requests_total": 12345
  }
}
```

### GET /ready
Kubernetes readiness probe endpoint.

```bash
curl http://localhost:32542/ready
```

### GET /metrics
Prometheus metrics endpoint.

```bash
curl http://localhost:32542/metrics
```

## 🛡️ Blacklist API Endpoints

### GET /api/blacklist/active
Get active threat IP addresses in text format.

```bash
curl http://localhost:32542/api/blacklist/active
```

**Response (text/plain):**
```
192.168.1.100
10.0.0.50
203.0.113.1
...
```

**Query Parameters:**
- `format`: Response format (`text`, `json`) - default: `text`
- `source`: Filter by source (`regtech`, `secudium`, `all`) - default: `all`
- `limit`: Maximum number of IPs to return - default: no limit

### GET /api/v2/blacklist/enhanced
Get IP addresses with metadata.

```bash
curl http://localhost:32542/api/v2/blacklist/enhanced
```

**Response:**
```json
{
  "data": [
    {
      "ip_address": "192.168.1.100",
      "source": "regtech",
      "detection_date": "2025-08-13",
      "threat_type": "malware",
      "confidence": "high",
      "country": "US",
      "asn": "AS15169",
      "last_seen": "2025-08-13T11:30:00Z"
    }
  ],
  "metadata": {
    "total_count": 45678,
    "filtered_count": 45678,
    "last_updated": "2025-08-13T11:30:00Z"
  }
}
```

### GET /api/fortigate
FortiGate External Connector format.

```bash
curl http://localhost:32542/api/fortigate
```

**Response:**
```json
{
  "results": [
    {
      "ip": "192.168.1.100",
      "type": "malicious"
    }
  ],
  "metadata": {
    "total": 45678,
    "timestamp": "2025-08-13T12:00:00Z"
  }
}
```

## 🔄 Collection Management

### GET /api/collection/status
Get current collection status.

```bash
curl http://localhost:32542/api/collection/status
```

**Response:**
```json
{
  "collection_enabled": true,
  "last_collection": {
    "regtech": "2025-08-13T11:30:00Z",
    "secudium": "2025-08-13T11:25:00Z"
  },
  "next_scheduled": {
    "regtech": "2025-08-13T12:30:00Z",
    "secudium": "2025-08-13T12:25:00Z"
  },
  "statistics": {
    "total_ips": 45678,
    "regtech_ips": 23456,
    "secudium_ips": 22222,
    "success_rate": 98.5
  }
}
```

### POST /api/collection/enable
Enable data collection.

```bash
curl -X POST http://localhost:32542/api/collection/enable \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "message": "Collection enabled successfully",
  "status": "enabled",
  "cleared_data": true
}
```

### POST /api/collection/disable
Disable data collection.

```bash
curl -X POST http://localhost:32542/api/collection/disable \
  -H "Authorization: Bearer <token>"
```

### POST /api/collection/regtech/trigger
Manually trigger REGTECH collection.

```bash
curl -X POST http://localhost:32542/api/collection/regtech/trigger \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-08-01", "end_date": "2025-08-13"}'
```

**Response:**
```json
{
  "message": "REGTECH collection triggered",
  "task_id": "regtech-20250813-120000",
  "status": "started",
  "estimated_duration": "5-10 minutes"
}
```

### POST /api/collection/secudium/trigger
Manually trigger SECUDIUM collection.

```bash
curl -X POST http://localhost:32542/api/collection/secudium/trigger \
  -H "Authorization: Bearer <token>"
```

## 📊 Analytics & Monitoring

### GET /api/v2/analytics/trends
Get threat trend analysis.

```bash
curl http://localhost:32542/api/v2/analytics/trends?days=7
```

**Response:**
```json
{
  "trends": {
    "daily_counts": [
      {"date": "2025-08-07", "count": 1234, "new_ips": 123},
      {"date": "2025-08-08", "count": 1456, "new_ips": 234}
    ],
    "source_breakdown": {
      "regtech": 23456,
      "secudium": 22222
    },
    "threat_types": {
      "malware": 15678,
      "phishing": 12345,
      "botnet": 8901,
      "scanner": 8754
    }
  },
  "summary": {
    "total_ips": 45678,
    "growth_rate": 2.3,
    "avg_daily_new": 178
  }
}
```

### GET /api/v2/sources/status
Get source-specific status.

```bash
curl http://localhost:32542/api/v2/sources/status
```

**Response:**
```json
{
  "sources": {
    "regtech": {
      "status": "active",
      "last_collection": "2025-08-13T11:30:00Z",
      "success_rate": 99.2,
      "total_ips": 23456,
      "avg_response_time": 1250
    },
    "secudium": {
      "status": "active", 
      "last_collection": "2025-08-13T11:25:00Z",
      "success_rate": 97.8,
      "total_ips": 22222,
      "avg_response_time": 1890
    }
  }
}
```

### GET /monitoring/dashboard
Real-time health dashboard (HTML).

```bash
curl http://localhost:32542/monitoring/dashboard
```

Returns HTML dashboard with real-time metrics, charts, and system status.

## 🔧 Administrative Endpoints

### GET /api/admin/stats
System statistics (admin only).

```bash
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:32542/api/admin/stats
```

### POST /api/admin/maintenance
System maintenance operations.

```bash
curl -X POST http://localhost:32542/api/admin/maintenance \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"operation": "cleanup_logs", "days": 30}'
```

## 📈 Prometheus Metrics

### Available Metrics
- `blacklist_api_requests_total` - Total API requests
- `blacklist_response_time_seconds` - API response times
- `blacklist_active_ips_total` - Number of active IPs
- `blacklist_collection_success_total` - Successful collections
- `blacklist_collection_duration_seconds` - Collection duration
- `blacklist_database_connections` - Database connection pool
- `blacklist_redis_operations_total` - Redis operations
- `blacklist_auth_attempts_total` - Authentication attempts

### Sample Metrics Query
```bash
curl http://localhost:32542/metrics | grep "blacklist_"
```

## 🚨 Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": "Missing required parameter: start_date",
    "timestamp": "2025-08-13T12:00:00Z"
  }
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

## 🔒 Rate Limiting

### Limits
- **Anonymous**: 100 requests per 15 minutes
- **Authenticated**: 1000 requests per 15 minutes
- **Admin**: 5000 requests per 15 minutes

### Rate Limit Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1692345600
```

## 📝 API Changelog

### v1.0.34 (Current)
- Added enhanced blacklist endpoint with metadata
- New Prometheus metrics integration
- Improved error handling and validation
- Added credential management endpoints
- Enhanced health check with component status

### v1.0.33
- Added real-time monitoring dashboard
- Improved collection status reporting
- Enhanced analytics endpoints

### v1.0.32
- Initial v2 API endpoints
- JWT authentication implementation
- FortiGate connector improvements

---

**API Documentation Version**: v1.0.34  
**Last Updated**: 2025-08-13  
**OpenAPI Specification**: Available at `/api/docs` (when enabled)
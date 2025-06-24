# Blacklist Management System Overview

## Project Purpose
Enterprise threat intelligence platform with multi-source data collection, automated processing, and FortiGate External Connector integration for IP blacklist management.

## Tech Stack
- **Backend**: Flask 2.3.3 with dependency injection architecture
- **Database**: SQLite (development) / PostgreSQL (optional production)
- **Cache**: Redis 4.6.0 with memory fallback
- **Server**: Gunicorn 21.2.0 (production WSGI)
- **Container**: Docker/Podman support
- **Data Processing**: pandas, BeautifulSoup4 for web scraping
- **Performance**: orjson for fast JSON, Flask-Compress for compression
- **Security**: Flask-Limiter, PyJWT, cryptography
- **Monitoring**: psutil, APScheduler for background tasks

## Key Features
- Multi-source IP collection (REGTECH, SECUDIUM)
- FortiGate External Connector API compliance
- Real-time data processing and caching
- 3-month data retention policy
- RESTful API with rate limiting
- Containerized deployment with CI/CD

## Architecture
- Entry point: `main.py` → `src/core/app_compact.py` → fallback chain
- Dependency injection via `src/core/container.py`
- Plugin-based IP sources in `src/core/ip_sources/`
- Unified service layer with comprehensive error handling
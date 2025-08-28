# 🚀 Deployment Guide - Live System

> **Current Status**: Production system operational at https://blacklist.jclee.me/

Complete deployment documentation for the Blacklist Management System enterprise threat intelligence platform.

---

## 🌐 Live System Information

### Production System Status
- **🌐 Live URL**: https://blacklist.jclee.me/ 
- **📊 Status**: **FULLY OPERATIONAL**
- **⚡ Performance**: 50-65ms response times (excellent)
- **🔒 Security**: JWT + API Key authentication validated
- **📊 Version**: v1.0.37
- **🗄️ Database**: PostgreSQL with connection pooling
- **⚡ Cache**: Redis with memory fallback
- **🐳 Platform**: Docker Compose on production server

### Live System Endpoints
```bash
# Core System Health
curl https://blacklist.jclee.me/health | jq

# Active IP Blacklist
curl https://blacklist.jclee.me/api/blacklist/active

# FortiGate Integration
curl https://blacklist.jclee.me/api/fortigate

# Collection Status
curl https://blacklist.jclee.me/api/collection/status | jq

# Web Dashboards
open https://blacklist.jclee.me/dashboard     # Collection Dashboard
open https://blacklist.jclee.me/statistics   # Statistics Dashboard
```

---

## 🏗️ Architecture Overview

### Production Stack
```
┌─ Load Balancer/Reverse Proxy ─┐
│                                │
├─ Docker Compose Deployment ────┤
│  ├─ blacklist:latest (App)     │
│  ├─ postgresql:15 (Database)   │
│  └─ redis:7 (Cache)            │
│                                │
├─ Persistent Storage ───────────┤
│  ├─ PostgreSQL Data            │
│  ├─ Application Logs           │
│  └─ Redis Persistence          │
│                                │
└─ Health Monitoring ────────────┘
   ├─ Application Health Checks
   ├─ Database Connection Monitoring
   └─ Cache Availability Checks
```

### Network Configuration
- **External Port**: 32542 (mapped to internal 2542)
- **Database**: Internal network (postgresql:5432)
- **Cache**: Internal network (redis:6379)
- **Health Checks**: Every 30 seconds with 3 retry attempts

---

## 🐳 Docker Compose Configuration

### Production docker-compose.yml
```yaml
# Current production configuration
version: '3.9'

services:
  blacklist:
    image: registry.jclee.me/blacklist:latest
    container_name: blacklist
    restart: unless-stopped
    ports:
      - "32542:2542"
    environment:
      FLASK_ENV: production
      PORT: 2542
      DATABASE_URL: "postgresql://blacklist_user:blacklist_password_change_me@postgresql:5432/blacklist"
      REDIS_URL: redis://redis:6379/0
      COLLECTION_ENABLED: "true"
      FORCE_DISABLE_COLLECTION: "false"
      GUNICORN_WORKERS: 4
      GUNICORN_THREADS: 2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2542/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      - postgresql
      - redis

  postgresql:
    image: postgres:15
    environment:
      POSTGRES_DB: blacklist
      POSTGRES_USER: blacklist_user
      POSTGRES_PASSWORD: blacklist_password_change_me
    volumes:
      - postgresql-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U blacklist_user -d blacklist"]
      interval: 10s
      timeout: 5s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  postgresql-data:
  redis-data:
```

### Deployment Commands
```bash
# Pull latest images and restart
docker-compose pull && docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f blacklist

# Health verification
curl http://localhost:32542/health | jq
```

---

## 🔧 GitOps Pipeline

### Current CI/CD Status
- **GitOps Maturity**: 8.5/10 (Production-ready)
- **CI/CD Platform**: GitHub Actions
- **Container Registry**: registry.jclee.me (private)
- **Deployment**: Automated on push to main branch
- **Security Scanning**: Trivy + Bandit integrated

### Deployment Workflow
```
Code Push → GitHub Actions → Build & Test → Security Scan → 
Registry Push → Production Update → Health Verification
```

### GitHub Actions Pipeline
```yaml
# Automated deployment on push to main
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
      - name: Build Docker image
      - name: Security scan (Trivy)
      - name: Push to registry.jclee.me
      - name: Deploy to production
      - name: Health verification
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoints
```bash
# Basic health check
curl https://blacklist.jclee.me/health
# Response: {"status": "healthy", "version": "1.0.37"}

# Detailed health check
curl https://blacklist.jclee.me/api/health
# Response: Detailed component status

# Collection system status
curl https://blacklist.jclee.me/api/collection/status
```

### Performance Monitoring
- **Response Time**: 50-65ms (excellent performance)
- **Concurrent Users**: 100+ supported
- **Database Connections**: Pooled and optimized
- **Cache Hit Rate**: Redis with memory fallback
- **Error Rate**: Minimal with automatic error recovery

### Monitoring Dashboards
- **Collection Dashboard**: https://blacklist.jclee.me/dashboard
- **Statistics Dashboard**: https://blacklist.jclee.me/statistics
- **System Health**: Real-time health checks every 30 seconds

---

## 🔒 Security & Authentication

### Current Security Implementation
- **Authentication**: JWT + API Key dual system
- **Database**: PostgreSQL with secure credentials
- **Network**: Internal Docker network isolation
- **TLS**: HTTPS/TLS termination at load balancer
- **Access Control**: Role-based access control (RBAC)

### Security Validation
```bash
# Test authentication endpoints
curl https://blacklist.jclee.me/api/keys/verify
curl -X POST https://blacklist.jclee.me/api/auth/login

# Security headers verification
curl -I https://blacklist.jclee.me/
```

---

## 🛠️ Local Development Setup

### Development Environment
```bash
# Clone repository
git clone https://github.com/JCLEE94/blacklist.git
cd blacklist

# Environment setup
make init
python3 scripts/setup-credentials.py

# Run local development server
docker-compose up -d

# Access local instance
curl http://localhost:32542/health | jq
open http://localhost:32542/dashboard
```

### Testing
```bash
# Run test suite (improving from 19% to 95% coverage)
pytest -v

# API testing
pytest -m api

# Collection system testing
pytest -m collection

# Performance benchmarking
python3 tests/integration/performance_benchmark.py
```

---

## 🚨 Troubleshooting

### Common Issues & Solutions

#### 1. Container Not Starting
```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs blacklist

# Restart services
docker-compose restart
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose logs postgresql

# Test database connectivity
docker-compose exec blacklist python3 -c "from src.core.database import test_connection; test_connection()"
```

#### 3. Performance Issues
```bash
# Monitor resource usage
docker stats

# Check response times
curl -w "Time: %{time_total}s\n" https://blacklist.jclee.me/health

# Review application logs
docker-compose logs -f blacklist
```

#### 4. Authentication Problems
```bash
# Test JWT authentication
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  https://blacklist.jclee.me/api/auth/login

# Verify API key functionality
curl -H "X-API-Key: your-api-key" \
  https://blacklist.jclee.me/api/keys/verify
```

---

## 📈 Performance Optimization

### Current Performance Metrics
- **API Response Time**: 50-65ms (excellent)
- **Database Query Time**: Optimized with connection pooling
- **Cache Performance**: Redis with 256MB limit + memory fallback
- **Concurrent Request Handling**: 100+ requests supported

### Optimization Features
- **Gunicorn Workers**: 4 workers with 2 threads each
- **Database Connection Pooling**: Optimized PostgreSQL connections
- **Redis Caching**: Automatic fallback to memory cache
- **Response Compression**: Gzip compression enabled
- **Static Asset Optimization**: Minified CSS/JS

---

## 🔄 Backup & Recovery

### Backup Strategy
```bash
# Database backup
docker-compose exec postgresql pg_dump -U blacklist_user blacklist > backup.sql

# Application data backup
docker-compose exec blacklist tar -czf /tmp/app-data.tar.gz /app/instance

# Configuration backup
cp docker-compose.yml .env config-backup/
```

### Recovery Procedures
```bash
# Database restore
cat backup.sql | docker-compose exec -T postgresql psql -U blacklist_user blacklist

# Application data restore
docker-compose exec blacklist tar -xzf /tmp/app-data.tar.gz -C /

# Service restart
docker-compose restart
```

---

## 📞 Support & Maintenance

### System Maintenance
- **Regular Updates**: Automated via GitOps pipeline
- **Security Patches**: Applied through base image updates
- **Database Maintenance**: Automated cleanup and optimization
- **Log Rotation**: Automatic log management

### Support Contacts
- **Live System**: https://blacklist.jclee.me/
- **Portfolio/Demo**: https://qws941.github.io/blacklist/
- **Repository**: https://github.com/JCLEE94/blacklist
- **Container Registry**: registry.jclee.me

---

**Last Updated**: 2025-08-20  
**System Version**: v1.0.37  
**Deployment Status**: Production-ready, fully operational
# 🚀 Deployment Guide v1.0.35

> **Updated for GitHub Container Registry, V2 API, and Portfolio Integration**

Complete deployment guide for Blacklist Management System with modern GitOps pipeline.

---

## 🌟 What's New in v1.0.35

### 🐳 GitHub Container Registry Migration
- **New Registry**: `ghcr.io/jclee94/blacklist` 
- **Enhanced Security**: Automatic vulnerability scanning
- **Better Integration**: Native GitHub Actions support

### 🎨 GitHub Pages Portfolio
- **Live Site**: https://jclee94.github.io/blacklist/
- **Auto-deployment**: Updates on every push
- **Modern Design**: Dark theme with performance metrics

### 🔐 Complete Security System
- **JWT Authentication**: Dual-token system
- **API Keys**: Automated generation and management
- **Security Tables**: Complete user management

### ✅ V2 API Complete
- **Analytics API**: 6 comprehensive endpoints
- **Sources API**: Real-time monitoring
- **Enhanced Caching**: Performance optimizations

---

## 📋 Prerequisites

### Required Tools
```bash
# Essential tools
docker --version          # Docker 20.0+
git --version            # Git 2.30+
curl --version           # curl 7.0+
jq --version             # jq 1.6+

# Optional tools
kubectl version --client # Kubernetes CLI
helm version            # Helm 3.0+
```

### Required Access
- GitHub Account with Actions enabled
- GitHub Container Registry access
- Repository push permissions

---

## 🚀 Quick Deployment

### 1. GitHub Container Registry (Recommended)
```bash
# Pull latest version
docker pull ghcr.io/jclee94/blacklist:latest

# Run with Docker Compose
git clone https://github.com/JCLEE94/blacklist
cd blacklist
docker-compose up -d

# Verify deployment
curl http://localhost:32542/health | jq
```

### 2. Local Development Setup
```bash
# Clone repository
git clone https://github.com/JCLEE94/blacklist
cd blacklist

# Initialize environment
make init

# Setup security system
python3 scripts/init_security.py

# Start development server
python3 app/main.py --debug  # Port 8541
```

---

## 🔄 GitOps Deployment Pipeline

### Automated Deployment Flow
```
Code Push → GitHub Actions (ubuntu-latest) → Security Scan → 
Docker Build → ghcr.io Push → GitHub Pages Deploy → Health Check
```

### GitHub Actions Configuration
The `.github/workflows/main-deploy.yml` handles:
- **Security Scanning**: Trivy + Bandit
- **Docker Building**: Multi-stage builds
- **Registry Push**: GitHub Container Registry
- **Portfolio Deploy**: Automatic GitHub Pages update

### Triggering Deployments
```bash
# Automatic deployment on push
git add .
git commit -m "feat: new feature implementation"
git push origin main

# Manual workflow trigger
gh workflow run "Main Deploy" --ref main
```

---

## 🐳 Docker Deployment

### Production Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  blacklist:
    image: ghcr.io/jclee94/blacklist:latest
    ports:
      - "32542:2541"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:////app/instance/blacklist.db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - API_KEY_ENABLED=true
    volumes:
      - blacklist_data:/app/instance
      - blacklist_logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  blacklist_data:
  blacklist_logs:
  redis_data:
```

### Environment Configuration
```bash
# .env file (create from example)
cp config/.env.example .env
nano .env

# Essential variables
PORT=32542
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Security System (v1.0.35 New)
API_KEY_ENABLED=true
JWT_ENABLED=true
DEFAULT_API_KEY=blk_generated-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=auto-generated-password

# Collection Credentials
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
SECUDIUM_USERNAME=your-username
SECUDIUM_PASSWORD=your-password

# Container Registry
REGISTRY_URL=ghcr.io
REGISTRY_USERNAME=jclee94
```

---

## 🔐 Security System Setup

### 1. Initialize Security System
```bash
# Run security initialization
python3 scripts/init_security.py

# Generated components:
# - API keys with expiration
# - JWT secret keys
# - Admin user account
# - Security configuration
```

### 2. API Key Management
```bash
# Verify API key
curl -H "X-API-Key: blk_your-key" \
  http://localhost:32542/api/keys/verify

# List API keys (admin required)
curl -H "Authorization: Bearer <admin-token>" \
  http://localhost:32542/api/keys/list
```

### 3. JWT Authentication
```bash
# Login to get tokens
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  http://localhost:32542/api/auth/login

# Use access token
curl -H "Authorization: Bearer <access-token>" \
  http://localhost:32542/api/blacklist/active

# Refresh token when expired
curl -X POST -H "Content-Type: application/json" \
  -d '{"refresh_token":"your-refresh-token"}' \
  http://localhost:32542/api/auth/refresh
```

---

## 📊 Health Monitoring

### Health Check Endpoints
```bash
# Basic health check
curl http://localhost:32542/health

# Detailed component status
curl http://localhost:32542/api/health | jq

# Prometheus metrics
curl http://localhost:32542/metrics

# Real-time dashboard
open http://localhost:32542/monitoring/dashboard
```

### V2 API Monitoring
```bash
# Analytics trends
curl http://localhost:32542/api/v2/analytics/trends | jq

# Source status
curl http://localhost:32542/api/v2/sources/status | jq

# System summary
curl http://localhost:32542/api/v2/analytics/summary | jq
```

---

## 🔧 Configuration Management

### Database Initialization
```bash
# Initialize with new schema v2.0
python3 app/init_database.py

# Force reinitialize (clears data)
python3 app/init_database.py --force

# Verify database
sqlite3 instance/blacklist.db ".tables"
```

### Collection System
```bash
# Enable collection
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:32542/api/collection/enable

# Trigger manual collection
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:32542/api/collection/regtech/trigger

# Check collection status
curl http://localhost:32542/api/collection/status | jq
```

---

## 🌐 GitHub Pages Portfolio

### Automatic Deployment
The portfolio automatically deploys on every push to main branch:
- **Build**: GitHub Actions processes the docs/index.html
- **Deploy**: Updates https://jclee94.github.io/blacklist/
- **Verify**: Site is immediately accessible

### Manual Portfolio Update
```bash
# Edit portfolio content
nano docs/index.html

# Commit and push
git add docs/index.html
git commit -m "docs: update portfolio content"
git push origin main

# Site updates automatically within 1-2 minutes
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Container Registry Authentication
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u jclee94 --password-stdin

# Pull image with authentication
docker pull ghcr.io/jclee94/blacklist:latest
```

#### 2. Port Conflicts
```bash
# Check port usage
lsof -i :32542  # Docker port
lsof -i :8541   # Local dev port

# Kill conflicting processes
sudo kill -9 <PID>
```

#### 3. Database Issues
```bash
# Reset database
python3 app/init_database.py --force

# Check database permissions
ls -la instance/
chmod 664 instance/blacklist.db
```

#### 4. Security System Issues
```bash
# Reinitialize security
rm config/security.json
python3 scripts/init_security.py

# Verify API key
curl -H "X-API-Key: <key>" http://localhost:32542/api/keys/verify
```

#### 5. GitHub Actions Failures
```bash
# Check workflow status
gh run list

# View detailed logs
gh run view <run-id>

# Re-run failed workflow
gh run rerun <run-id>
```

---

## 📈 Performance Optimization

### Production Settings
```bash
# Environment optimizations
FLASK_ENV=production
GUNICORN_WORKERS=4
REDIS_MAX_MEMORY=256mb
DATABASE_POOL_SIZE=20

# Enable compression
COMPRESS_RESPONSES=true
CACHE_TYPE=redis
CACHE_DEFAULT_TIMEOUT=300
```

### Monitoring Setup
```bash
# Performance testing
python3 tests/integration/performance_benchmark.py

# Load testing
curl -w "Total time: %{time_total}s\n" \
  http://localhost:32542/api/blacklist/active
```

---

## 🔒 Security Best Practices

### Production Checklist
- [ ] Change default passwords
- [ ] Generate new JWT secrets
- [ ] Enable API key authentication
- [ ] Configure rate limiting
- [ ] Set up HTTPS termination
- [ ] Enable security headers
- [ ] Regular security scans

### Backup Strategy
```bash
# Database backup
cp instance/blacklist.db backups/blacklist-$(date +%Y%m%d).db

# Configuration backup
tar -czf backups/config-$(date +%Y%m%d).tar.gz .env config/ instance/

# Automated backup (add to crontab)
0 2 * * * /path/to/backup-script.sh
```

---

## 📚 Additional Resources

### Documentation Links
- **Portfolio Site**: https://jclee94.github.io/blacklist/
- **API Documentation**: [docs/api-reference.md](api-reference.md)
- **Container Registry**: https://ghcr.io/jclee94/blacklist
- **Source Code**: https://github.com/JCLEE94/blacklist

### Support Commands
```bash
# Get system info
curl http://localhost:32542/api/health | jq '.components'

# View logs
docker-compose logs -f blacklist

# Check GitHub Actions
gh workflow list
gh run list --limit 5
```

---

**Deployment Guide Version**: v1.0.35  
**Last Updated**: 2025-08-14  
**Status**: Production Ready ✅
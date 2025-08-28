---
layout: default
title: Installation Guide
description: Complete installation guide for all environments
---

# Installation Guide

Complete installation guide for Blacklist Management System v1.0.37.

## 🎯 Installation Options

Choose the installation method that best fits your environment:

1. **[Quick Start](#quick-start)** - For development and testing
2. **[Docker Deployment](#docker-deployment)** - Recommended for production
3. **[Offline Deployment](offline-deployment.md)** - For air-gapped environments
4. **[Kubernetes Deployment](#kubernetes-deployment)** - For scalable production

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Git
- 4GB RAM (minimum)
- 10GB free disk space

### Steps
```bash
# 1. Clone repository
git clone https://github.com/JCLEE94/blacklist.git
cd blacklist

# 2. Initialize environment
make init

# 3. Configure credentials
cp .env.example .env
nano .env  # Edit with your credentials

# 4. Start services
make start

# 5. Verify installation
curl http://localhost:32542/health | jq
```

## 🐳 Docker Deployment

### Prerequisites
- Docker 20.0+
- Docker Compose 2.0+
- 4GB RAM (minimum)
- 20GB free disk space

### Production Deployment
```bash
# 1. Clone and configure
git clone https://github.com/JCLEE94/blacklist.git
cd blacklist
cp .env.example .env

# 2. Configure production settings
nano .env
# Set:
# FLASK_ENV=production
# COLLECTION_ENABLED=true
# REGTECH_USERNAME=your-username
# REGTECH_PASSWORD=your-password
# SECUDIUM_USERNAME=your-username
# SECUDIUM_PASSWORD=your-password

# 3. Start production services
docker-compose up -d

# 4. Verify deployment
docker-compose ps
curl http://localhost:32542/health
```

### Docker Configuration
The system includes optimized Docker configuration:
- Multi-stage builds for minimal image size
- Health checks for container monitoring
- Automatic restart policies
- Volume mounts for persistent data

## ☸️ Kubernetes Deployment

### Prerequisites
- Kubernetes 1.20+
- kubectl configured
- ArgoCD (optional, for GitOps)
- 8GB RAM per node
- 50GB storage

### Helm Deployment
```bash
# 1. Add Helm repository
helm repo add blacklist https://charts.jclee.me
helm repo update

# 2. Create namespace
kubectl create namespace blacklist

# 3. Install with Helm
helm install blacklist blacklist/blacklist \
  --namespace blacklist \
  --set image.tag=latest \
  --set persistence.enabled=true \
  --set ingress.enabled=true \
  --set monitoring.enabled=true

# 4. Verify deployment
kubectl get pods -n blacklist
kubectl get services -n blacklist
```

### ArgoCD GitOps (Recommended)
```bash
# 1. Set up ArgoCD application
kubectl apply -f argocd/application.yaml

# 2. Sync application
argocd app sync blacklist

# 3. Monitor deployment
argocd app get blacklist
kubectl get pods -n blacklist -w
```

## 🔐 Security Configuration

### Credential Management
```bash
# Set up enterprise-grade credentials
python3 scripts/setup-credentials.py

# Options:
# - Interactive mode (default)
# - Batch mode: --batch
# - Verification: --check
# - Rotation: --rotate
```

### Security Hardening
```bash
# 1. Configure firewall
sudo ufw allow 32542/tcp  # Application
sudo ufw allow 22/tcp     # SSH
sudo ufw --force enable

# 2. Set up SSL/TLS (production)
# Copy SSL certificates to config/ssl/
# Update nginx configuration

# 3. Configure monitoring
# Prometheus metrics available at /metrics
# Health dashboard at /monitoring/dashboard
```

## 📊 Post-Installation

### Verification Checklist
- [ ] Application responds at health endpoint
- [ ] Database initialized and accessible
- [ ] Redis cache functioning
- [ ] Prometheus metrics available
- [ ] Credentials configured and validated
- [ ] Collection system operational

### Performance Tuning
```bash
# 1. Database optimization
python3 -c "from src.core.database_schema import DatabaseSchema; DatabaseSchema().optimize_indexes()"

# 2. Cache configuration
# Adjust Redis memory limit in docker-compose.yml
# Monitor cache hit rates in metrics

# 3. Resource allocation
# Monitor CPU/memory usage
# Adjust container limits as needed
```

### Monitoring Setup
```bash
# 1. Enable Prometheus metrics collection
curl http://localhost:32542/metrics

# 2. Configure alerts (optional)
# Copy monitoring/alert_rules.yml to Prometheus
# Set up AlertManager for notifications

# 3. Access monitoring dashboard
curl http://localhost:32542/monitoring/dashboard
```

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using port 32542
sudo lsof -i :32542
sudo netstat -tulpn | grep 32542

# Stop conflicting service or change port
```

#### Database Connection Errors
```bash
# Check database status
python3 -c "from src.core.database import get_db; print('DB OK' if get_db() else 'DB Error')"

# Reinitialize database
python3 init_database.py --force
```

#### Collection Not Working
```bash
# Check credentials
python3 scripts/setup-credentials.py --check

# Verify collection status
curl http://localhost:32542/api/collection/status | jq

# Manual test collection
curl -X POST http://localhost:32542/api/collection/regtech/trigger
```

#### Performance Issues
```bash
# Check system resources
htop
df -h
free -h

# Monitor application metrics
curl http://localhost:32542/metrics | grep response_time

# Check logs for errors
tail -f logs/blacklist.log
```

### Getting Help

If you encounter issues:

1. **Check logs**: `tail -f logs/blacklist.log`
2. **Verify configuration**: Review `.env` file
3. **Run health check**: `curl http://localhost:32542/api/health | jq`
4. **Check system resources**: Ensure adequate CPU/memory
5. **Consult documentation**: Review relevant guides
6. **GitHub Issues**: [Report bugs](https://github.com/JCLEE94/blacklist/issues)

## 📋 System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 18.04+, CentOS 7+)
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB
- **Network**: Internet access for initial setup

### Recommended Requirements
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+)
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: High-speed internet for data collection

### Production Requirements
- **OS**: Linux (Latest LTS)
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Network**: Redundant connections
- **Monitoring**: Prometheus + Grafana
- **Backup**: Automated backup solution

---

**Installation Guide Version**: v1.0.37  
**Last Updated**: 2025-08-13  
**Support**: [GitHub Issues](https://github.com/JCLEE94/blacklist/issues)
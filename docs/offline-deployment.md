---
layout: default
title: Offline Deployment Guide
description: Complete guide for air-gapped environment deployment
---

# Offline Deployment Guide

Complete guide for deploying Blacklist Management System in air-gapped environments.

## 🎯 Overview

The Blacklist Management System v1.0.34 supports complete offline deployment for air-gapped environments, providing enterprise-grade security and zero external dependencies.

### Key Features
- **Complete Self-Contained**: No internet connection required after package creation
- **Automated Installation**: One-click deployment script (15-30 minutes)
- **Enterprise Security**: Encrypted credential management
- **Full Verification**: Automated health checks and validation

## 📋 Prerequisites

### Online Environment (Package Creation)
- Python 3.9+
- Docker and Docker Compose
- Git access to repository
- Internet connection for dependency download

### Offline Environment (Target Deployment)
- Linux x86_64 (Ubuntu 18.04+, CentOS 7+, RHEL 7+)
- 4GB RAM minimum, 8GB recommended
- 20GB free disk space
- sudo/root access

## 🔧 Step 1: Create Offline Package (Online Environment)

### 1.1 Clone Repository
```bash
git clone https://github.com/JCLEE94/blacklist.git
cd blacklist
```

### 1.2 Generate Offline Package
```bash
# Run the offline package creator
python3 scripts/create-offline-package.py

# Package will be created as: blacklist-offline-package.tar.gz
# Size: approximately 1-2GB
# Contains: Python wheels, Docker images, scripts, documentation
```

### 1.3 Package Contents
The offline package includes:
- **Python Dependencies**: All wheels for offline pip installation
- **Docker Images**: Exported TAR files for all required images
- **Application Code**: Complete source code and configuration
- **Installation Scripts**: Automated setup and verification tools
- **Documentation**: Complete offline documentation

## 📦 Step 2: Transfer to Offline Environment

### 2.1 Transfer Package
```bash
# Transfer the package to target environment
scp blacklist-offline-package.tar.gz user@target-server:/home/user/
# OR use physical media, USB drives, etc.
```

### 2.2 Verify Transfer
```bash
# On target server
ls -lh blacklist-offline-package.tar.gz
# Should show ~1-2GB file size
```

## 🚀 Step 3: Install in Offline Environment

### 3.1 Extract Package
```bash
# Extract the offline package
tar -xzf blacklist-offline-package.tar.gz
cd blacklist-offline-package
```

### 3.2 Run Automated Installation
```bash
# Standard installation
sudo ./install-offline.sh

# With debug output
sudo ./install-offline.sh --debug

# Custom installation directory
sudo ./install-offline.sh --install-dir /opt/blacklist
```

### 3.3 Installation Process
The installer performs:
1. **System Requirements Check**: Verifies OS, resources, dependencies
2. **Docker Installation**: Installs Docker if not present
3. **Python Environment**: Sets up Python 3.9+ with virtual environment
4. **Dependency Installation**: Installs all Python packages offline
5. **Docker Image Loading**: Loads all required Docker images
6. **Application Setup**: Configures application and database
7. **Service Configuration**: Sets up systemd services
8. **Security Setup**: Configures firewall and access controls

## 🔐 Step 4: Configure Security and Credentials

### 4.1 Set Up Credentials
```bash
# Interactive credential setup
python3 scripts/setup-credentials.py

# Batch mode (for automated deployment)
python3 scripts/setup-credentials.py --batch \
  --regtech-user "your-username" \
  --regtech-pass "your-password" \
  --secudium-user "your-username" \
  --secudium-pass "your-password"
```

### 4.2 Configure Environment
```bash
# Edit configuration file
nano /opt/blacklist/.env

# Required settings for offline environment
FORCE_DISABLE_COLLECTION=false
COLLECTION_ENABLED=true
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:////opt/blacklist/data/blacklist.db
```

## ✅ Step 5: Verify Installation

### 5.1 Run Verification Script
```bash
# Comprehensive verification
./verify-installation.sh

# Detailed verification with logs
./verify-installation.sh --verbose
```

### 5.2 Manual Health Checks
```bash
# Check system status
systemctl status blacklist
systemctl status redis

# Check application health
curl http://localhost:32542/health | jq
curl http://localhost:32542/api/health | jq

# Check monitoring endpoints
curl http://localhost:32542/metrics | head -20
curl http://localhost:32542/monitoring/dashboard
```

### 5.3 Performance Validation
```bash
# Run performance benchmark
python3 tests/integration/performance_benchmark.py

# Expected results:
# - API response time: <50ms
# - Health check: 200 OK
# - Database connectivity: SUCCESS
# - Redis connectivity: SUCCESS
```

## 🔧 Step 6: Post-Installation Configuration

### 6.1 Service Management
```bash
# Start services
systemctl start blacklist
systemctl start redis

# Enable auto-start
systemctl enable blacklist
systemctl enable redis

# Check status
systemctl status blacklist
```

### 6.2 Configure Monitoring
```bash
# Set up log rotation
sudo cp config/logrotate.d/blacklist /etc/logrotate.d/

# Configure system monitoring
sudo cp config/systemd/blacklist-health.service /etc/systemd/system/
sudo systemctl enable blacklist-health
```

### 6.3 Security Hardening
```bash
# Configure firewall
sudo ufw allow 32542/tcp  # Application port
sudo ufw allow 22/tcp     # SSH
sudo ufw --force enable

# Set up SSL/TLS (optional)
sudo cp config/nginx/blacklist.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/blacklist.conf /etc/nginx/sites-enabled/
```

## 📊 Monitoring and Maintenance

### Real-time Monitoring
```bash
# Application logs
tail -f /var/log/blacklist/app.log

# System metrics
curl http://localhost:32542/metrics | grep "blacklist_"

# Health dashboard
curl http://localhost:32542/monitoring/dashboard
```

### Maintenance Tasks
```bash
# Database backup
python3 scripts/backup-database.py

# Log cleanup
sudo logrotate -f /etc/logrotate.d/blacklist

# Update credentials
python3 scripts/setup-credentials.py --rotate
```

## 🚨 Troubleshooting

### Common Issues

#### Installation Fails
```bash
# Check system requirements
./verify-system-requirements.sh

# Check installation logs
tail -f /var/log/blacklist-install.log

# Retry with debug
sudo ./install-offline.sh --debug
```

#### Service Won't Start
```bash
# Check service status
systemctl status blacklist

# Check logs
journalctl -u blacklist -f

# Manual start for debugging
cd /opt/blacklist && python3 main.py --debug
```

#### Performance Issues
```bash
# Check system resources
htop
df -h
free -h

# Check application metrics
curl http://localhost:32542/metrics | grep -E "(cpu|memory|response)"
```

#### Database Issues
```bash
# Check database integrity
python3 -c "from src.core.database_schema import DatabaseSchema; print(DatabaseSchema().verify_schema())"

# Reinitialize database
python3 init_database.py --force
```

### Support and Documentation

For additional support:
- Check logs in `/var/log/blacklist/`
- Review configuration in `/opt/blacklist/.env`
- Consult main documentation at `/opt/blacklist/docs/`
- Run verification script: `./verify-installation.sh --verbose`

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] System requirements verified
- [ ] Offline package created and transferred
- [ ] Network access confirmed (internal only)
- [ ] Backup strategy planned

### During Deployment
- [ ] Package extracted successfully
- [ ] Installation script completed without errors
- [ ] All services started successfully
- [ ] Health checks passed

### Post-Deployment
- [ ] Credentials configured securely
- [ ] Monitoring dashboard accessible
- [ ] Performance benchmark completed
- [ ] Backup system configured
- [ ] Documentation reviewed with operations team

---

**Deployment Guide Version**: v1.0.34  
**Last Updated**: 2025-08-13  
**Estimated Installation Time**: 15-30 minutes
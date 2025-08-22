# GitHub Actions Workflows - Optimized for Self-hosted Runners

This directory contains a comprehensive set of GitHub Actions workflows optimized specifically for self-hosted runners, providing enterprise-grade CI/CD, security, and monitoring capabilities for the Blacklist Management System.

## 📋 Table of Contents

- [Workflow Overview](#workflow-overview)
- [Self-hosted Runner Optimizations](#self-hosted-runner-optimizations)
- [Security Features](#security-features)
- [Performance Optimizations](#performance-optimizations)
- [Monitoring & Alerting](#monitoring--alerting)
- [Setup Instructions](#setup-instructions)
- [Troubleshooting](#troubleshooting)

## 🚀 Workflow Overview

### Core Workflows (Optimized for Stability)

| Workflow | Purpose | Trigger | Duration | Status |
|----------|---------|---------|----------|--------|
| **Main Deploy** | Primary deployment pipeline | Push to main | 15-25 min | ✅ Active |
| **Matrix Builds** | Multi-platform testing | Push to main/Tags | 20-35 min | ✅ Optimized |
| **Cache Management** | Cache optimization | Every 3 days | 5-10 min | ✅ Reduced |
| **Monitoring & Alerts** | Health monitoring | 4 times daily | 3-5 min | ✅ Reduced |
| **Security Hardening** | Security compliance | Weekly | 10-20 min | ✅ Reduced |
| **GitHub Pages** | Portfolio deployment | Push to main | 2-3 min | ✅ GitHub-hosted |

### Disabled/Optimized Workflows

| Workflow | Status | Reason |
|----------|--------|--------|
| `enhanced-pipeline.yml` | 🚫 Disabled | Redundant with main-deploy.yml |
| `optimized-pipeline.yml` | 🚫 Disabled | Superseded by main-deploy.yml |
| `github-pages.yml` | ✅ Active | Moved to ubuntu-latest runner |
| `offline-package.yml` | ✅ Active | Air-gap deployment support |

## 🎯 Self-hosted Runner Optimizations

### Intelligent Resource Management

```yaml
# Example: Dynamic resource allocation
strategy:
  matrix:
    include:
      - environment: production
        resources: high
        parallel_jobs: 4
      - environment: development  
        resources: low
        parallel_jobs: 2
```

### Advanced Caching Strategy

1. **Multi-layer Cache System**
   - Docker BuildKit cache
   - Registry cache with fallback
   - Local filesystem cache
   - Dependency cache with version pinning

2. **Cache Warming & Optimization**
   - Automatic cache pre-population
   - Intelligent cache invalidation
   - Size-based cleanup policies
   - Performance trend analysis

3. **Cache Management Features**
   - Daily optimization schedules
   - Disk space monitoring
   - Cache health assessment
   - Automated cleanup with retention policies

### Build Performance Enhancements

- **Parallel Job Execution**: Matrix builds with intelligent job distribution
- **Change Detection**: Skip unnecessary builds based on file changes
- **Incremental Builds**: Layer-based Docker builds with optimal caching
- **Resource Monitoring**: Real-time CPU, memory, and disk usage tracking

## 🔒 Security Features

### Multi-layered Security Scanning

```yaml
# Security scan matrix
strategy:
  matrix:
    scan-type: [code, dependencies, secrets, infrastructure]
```

1. **Code Security**
   - Bandit static analysis
   - Semgrep pattern matching
   - Custom security rules
   - License compliance checking

2. **Infrastructure Security**
   - Trivy vulnerability scanning
   - Docker security benchmarks
   - System hardening assessment
   - Network security validation

3. **Compliance Frameworks**
   - CIS Controls
   - NIST Cybersecurity Framework
   - SOC 2 Type II
   - ISO 27001 controls

### Automated Security Remediation

- **Safe Mode**: Conservative fixes (file permissions, cleanup)
- **Aggressive Mode**: System updates, service hardening
- **Verification**: Post-remediation security assessment
- **Rollback**: Automated rollback on critical failures

## ⚡ Performance Optimizations

### Build Time Improvements

| Optimization | Before | After | Improvement |
|--------------|--------|-------|-------------|
| Docker Build | 8-12 min | 3-6 min | 50-60% |
| Test Execution | 15-20 min | 8-12 min | 40-45% |
| Cache Operations | 2-3 min | 30-60 sec | 60-75% |
| Registry Push | 3-5 min | 1-2 min | 65-70% |

### Resource Utilization

```yaml
# Intelligent resource allocation
resources:
  cpu: 
    request: "2"
    limit: "4"
  memory:
    request: "4Gi" 
    limit: "8Gi"
  storage:
    cache: "20Gi"
    build: "10Gi"
```

### Network Optimization

- **Registry Connectivity**: Automatic retry with exponential backoff
- **Parallel Downloads**: Concurrent image pulls and pushes
- **Compression**: Optimized layer compression for faster transfers
- **Local Registry Cache**: Minimize external registry calls

## 📊 Monitoring & Alerting

### Real-time Metrics

1. **Infrastructure Health**
   - CPU/Memory/Disk usage
   - Docker daemon status
   - Network connectivity
   - Service availability

2. **Pipeline Performance**
   - Build success rates
   - Average build times
   - Cache hit ratios
   - Error patterns

3. **Security Posture**
   - Vulnerability counts
   - Compliance scores
   - Security baseline metrics
   - Remediation status

### Alert Configuration

```yaml
# Alert thresholds
env:
  ALERT_THRESHOLD_CPU: 80      # CPU usage %
  ALERT_THRESHOLD_MEMORY: 80   # Memory usage %
  ALERT_THRESHOLD_DISK: 85     # Disk usage %
  COMPLIANCE_SCORE_TARGET: 85  # Compliance %
```

### Notification Channels

- **GitHub Issues**: Automatic issue creation for critical alerts
- **Workflow Summaries**: Detailed reports in workflow artifacts
- **Metrics Storage**: Historical data for trend analysis
- **Dashboard Integration**: JSON exports for external dashboards

## 🔧 Setup Instructions

### Prerequisites

1. **Self-hosted Runner Requirements**
   ```bash
   # System requirements
   CPU: 4+ cores
   Memory: 8GB+ RAM
   Storage: 100GB+ SSD
   OS: Ubuntu 20.04+ / RHEL 8+
   
   # Software requirements
   Docker: 20.10+
   Docker Compose: 2.0+
   Git: 2.30+
   ```

2. **Required Secrets**
   ```yaml
   # GitHub repository secrets
   REGISTRY_USERNAME: registry.jclee.me username
   REGISTRY_PASSWORD: registry.jclee.me password
   GITHUB_TOKEN: GitHub personal access token
   ```

### Installation Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/JCLEE94/blacklist.git
   cd blacklist
   ```

2. **Configure Runner**
   ```bash
   # Download and configure GitHub Actions runner
   mkdir actions-runner && cd actions-runner
   curl -o actions-runner-linux-x64-2.311.0.tar.gz \
     -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
   tar xzf actions-runner-linux-x64-2.311.0.tar.gz
   
   # Configure with your repository
   ./config.sh --url https://github.com/JCLEE94/blacklist --token YOUR_TOKEN
   ```

3. **Install as Service**
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

4. **Verify Setup**
   ```bash
   # Check runner status
   sudo ./svc.sh status
   
   # Test workflow execution
   gh workflow run enhanced-pipeline.yml
   ```

### Environment Configuration

1. **Docker Optimization**
   ```bash
   # Configure Docker for optimal performance
   sudo tee /etc/docker/daemon.json << EOF
   {
     "storage-driver": "overlay2",
     "log-driver": "json-file",
     "log-opts": {
       "max-size": "10m",
       "max-file": "3"
     },
     "default-address-pools": [
       {
         "base": "172.17.0.0/16",
         "size": 24
       }
     ]
   }
   EOF
   
   sudo systemctl restart docker
   ```

2. **System Optimization**
   ```bash
   # Increase file descriptor limits
   echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
   echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
   
   # Optimize disk I/O for builds
   echo 'none /tmp tmpfs defaults,size=4G 0 0' | sudo tee -a /etc/fstab
   ```

## 🛠️ Troubleshooting

### Common Issues

1. **Cache Issues**
   ```bash
   # Clear all caches
   rm -rf /tmp/.buildx-cache*
   docker buildx prune -af
   
   # Rebuild cache
   gh workflow run cache-management.yml -f cache_operation=rebuild
   ```

2. **Registry Connectivity**
   ```bash
   # Test registry connection
   docker login registry.jclee.me
   curl -v https://registry.jclee.me/v2/
   
   # Check DNS resolution
   nslookup registry.jclee.me
   ```

3. **Performance Issues**
   ```bash
   # Monitor system resources
   htop
   iotop
   df -h
   
   # Check Docker performance
   docker system df
   docker system events
   ```

4. **Security Scan Failures**
   ```bash
   # Update security tools
   curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
   
   # Manual security scan
   trivy fs --severity HIGH,CRITICAL /
   ```

### Debug Commands

```bash
# Workflow debugging
gh run list --limit 10
gh run view --log-failed

# Runner debugging
sudo journalctl -u actions.runner.* -f

# Cache analysis
find /tmp -name "*cache*" -type d -exec du -sh {} \;

# Performance monitoring
iostat -x 1
vmstat 1
```

### Log Locations

```bash
# Runner logs
~/.local/share/GitHub Actions Runner/_diag/Runner_*.log

# Workflow logs
GitHub Actions UI → Actions tab → Workflow run

# System logs
/var/log/syslog
journalctl -u docker
```

## 🔄 Workflow Customization

### Environment-specific Configuration

```yaml
# .github/workflows/custom-environment.yml
strategy:
  matrix:
    environment: [development, staging, production]
    include:
      - environment: production
        timeout: 60
        retry: 3
      - environment: staging
        timeout: 45
        retry: 2
      - environment: development
        timeout: 30
        retry: 1
```

### Custom Security Policies

```yaml
# Custom security scanning
- name: Custom Security Scan
  run: |
    # Add organization-specific security rules
    bandit -r src/ -c custom-bandit.yaml
    # Custom compliance checks
    ./scripts/custom-compliance-check.sh
```

### Performance Tuning

```yaml
# Workflow-specific optimizations
env:
  DOCKER_BUILDKIT: 1
  BUILDX_NO_DEFAULT_ATTESTATIONS: 1
  COMPOSE_DOCKER_CLI_BUILD: 1
  
  # Custom cache settings
  CACHE_SIZE_LIMIT: 20GB
  MAX_CACHE_AGE_DAYS: 14
```

## 📈 Metrics & Analytics

### Key Performance Indicators

- **Build Success Rate**: Target >95%
- **Average Build Time**: Target <15 minutes
- **Cache Hit Rate**: Target >80%
- **Security Compliance**: Target >90%
- **Resource Utilization**: Target 60-80%

### Monitoring Dashboards

The workflows generate JSON metrics suitable for:
- Grafana dashboards
- Prometheus monitoring
- Custom analytics platforms
- Trend analysis tools

### Continuous Improvement

Regular review and optimization based on:
- Performance metrics analysis
- Security assessment results
- Resource utilization patterns
- Developer feedback

---

## 📞 Support & Contributing

For issues, questions, or contributions:
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Update this README for improvements
- **Security Issues**: Follow responsible disclosure practices

**Last Updated**: 2025-01-28
**Version**: 2.0.0
**Maintainer**: jclee94@gmail.com
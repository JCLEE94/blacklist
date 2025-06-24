# Advanced CI/CD Pipeline

## 🚀 Overview

This repository uses an advanced CI/CD pipeline with multiple workflows for comprehensive deployment automation, security scanning, and monitoring.

## 📋 Workflows

### 1. Build and Deploy (`.github/workflows/build-deploy.yml`)
**Primary deployment pipeline with advanced features:**

- **Multi-stage testing**: Code quality, security scanning, unit tests with coverage
- **Multi-platform builds**: AMD64 and ARM64 support
- **Blue-green deployment**: Zero-downtime deployments with automatic rollback
- **Staging environment**: Automatic deployment to staging for develop branch
- **Performance testing**: Automated load testing with k6
- **Security scanning**: Container vulnerability scanning with Trivy
- **Comprehensive monitoring**: Health checks, smoke tests, integration tests
- **Slack notifications**: Real-time deployment status updates
- **Rollback capability**: One-click rollback via workflow dispatch

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`
- Manual workflow dispatch with environment selection

### 2. Security Scanning (`.github/workflows/security-scan.yml`)
**Comprehensive security analysis:**

- **Dependency scanning**: Safety, pip-audit for Python vulnerabilities
- **Static code analysis**: Bandit for security issues, Semgrep for patterns
- **Container scanning**: Trivy and Grype for image vulnerabilities
- **SAST**: GitHub CodeQL for advanced static analysis
- **License compliance**: Automated license compatibility checking

**Triggers:**
- Daily at 2 AM
- Changes to dependencies or Dockerfile
- Manual trigger

### 3. Performance Testing (`.github/workflows/performance-test.yml`)
**Automated performance validation:**

- **Load testing**: k6 performance tests with realistic user scenarios
- **Stress testing**: High-load testing to find breaking points
- **Spike testing**: Sudden traffic spike simulation
- **Threshold monitoring**: Automated failure on performance regression
- **PR feedback**: Performance results commented on pull requests

**Triggers:**
- Daily at 4 AM
- Pull requests with code changes
- Manual trigger

### 4. Dependency Updates (`.github/workflows/dependency-update.yml`)
**Automated dependency management:**

- **Weekly scanning**: Automatic dependency updates every Monday
- **Compatibility testing**: Validates updates work with existing code
- **Automated PRs**: Creates pull requests with dependency changes
- **Security-first**: Prioritizes security updates

**Triggers:**
- Weekly on Monday at 3 AM
- Manual trigger

## 🔧 Setup Requirements

### GitHub Secrets

Configure these secrets in GitHub repository settings:

```bash
# Registry Authentication
REGISTRY_USERNAME=qws941
REGISTRY_PASSWORD=your-registry-password

# SSH Deployment
DEPLOY_SSH_KEY=your-ssh-private-key

# Optional: Slack Notifications
SLACK_WEBHOOK=https://hooks.slack.com/services/...
```

### Setup Commands

```bash
# Set secrets via GitHub CLI
gh secret set REGISTRY_USERNAME -b "qws941"
gh secret set REGISTRY_PASSWORD -b "your-password"
gh secret set DEPLOY_SSH_KEY < ~/.ssh/deploy_key
gh secret set SLACK_WEBHOOK -b "your-slack-webhook-url"
```

## 🌊 Blue-Green Deployment

### Architecture
- **Nginx Load Balancer**: Routes traffic between blue/green environments
- **Health Checks**: Automated health validation before traffic switching
- **Rollback**: Instant rollback capability with previous version tracking
- **Canary Support**: Gradual traffic shifting for safer deployments

### Manual Blue-Green Deployment

```bash
# Deploy to blue environment
./scripts/blue-green-deploy.sh deploy blue v1.2.3

# Check deployment status
./scripts/blue-green-deploy.sh status

# Rollback if needed
./scripts/blue-green-deploy.sh rollback

# Cleanup environments
./scripts/blue-green-deploy.sh cleanup
```

### Direct Environment Access

```bash
# Test blue environment directly
curl http://localhost:2541/blue/health

# Test green environment directly  
curl http://localhost:2541/green/health

# Check load balancer
curl http://localhost:2541/health
```

## 📊 Performance Testing

### Local Testing

```bash
# Install k6
sudo apt-get install k6

# Run performance test
k6 run -e BASE_URL=http://localhost:2541 k6-tests/performance-test.js

# Run stress test
k6 run -e BASE_URL=http://localhost:2541 k6-tests/stress-test.js

# Run spike test
k6 run -e BASE_URL=http://localhost:2541 k6-tests/spike-test.js
```

### Thresholds

- **P95 Response Time**: < 500ms
- **P99 Response Time**: < 1000ms  
- **Error Rate**: < 10%
- **Availability**: > 99.5%

## 🔒 Security Scanning

### Automated Scans

1. **Daily Security Scan**: Runs comprehensive security analysis
2. **PR Security Check**: Validates security on code changes
3. **Container Scanning**: Checks for vulnerabilities in Docker images
4. **License Compliance**: Ensures compatible open-source licenses

### Manual Security Testing

```bash
# Run Bandit security scan
bandit -r src/ -f json -o bandit-report.json

# Check dependencies
safety check --json --output safety-report.json

# Scan Docker image
trivy image registry.jclee.me/blacklist:latest
```

## 🔄 Environment Strategy

### Environments

1. **Development**: Local development environment
2. **Staging**: `registry.jclee.me:2542` - Automatic deployment from `develop`
3. **Production**: `registry.jclee.me:2541` - Deployment from `main` with blue-green

### Branch Strategy

- **`main`**: Production-ready code, triggers production deployment
- **`develop`**: Integration branch, triggers staging deployment  
- **`feature/*`**: Feature branches, triggers tests only
- **Pull Requests**: Trigger full test suite and staging deployment

## 📈 Monitoring & Alerting

### Health Checks
- Application health endpoint monitoring
- Database connectivity validation
- Redis cache availability
- Response time monitoring

### Alerts
- Slack notifications for deployment status
- Email alerts for security vulnerabilities
- Performance degradation warnings
- Deployment failure notifications

### Metrics Collection
- Response time percentiles (P50, P95, P99)
- Error rates and status codes
- Throughput (requests per second)
- Resource utilization (CPU, memory)

## 🚨 Troubleshooting

### Common Issues

1. **Deployment Failures**
   ```bash
   # Check deployment logs
   kubectl logs -l app=blacklist
   
   # Verify health checks
   curl http://registry.jclee.me:2541/health
   ```

2. **Performance Issues**
   ```bash
   # Run quick performance test
   k6 run --duration 30s --vus 10 k6-tests/performance-test.js
   
   # Check resource usage
   docker stats
   ```

3. **Security Scan Failures**
   ```bash
   # Re-run security scan
   gh workflow run security-scan.yml
   
   # Check vulnerability details
   trivy image registry.jclee.me/blacklist:latest
   ```

### Rollback Procedures

1. **Automatic Rollback**: Failed deployments automatically rollback
2. **Manual Rollback**: Use workflow dispatch with rollback option
3. **Blue-Green Rollback**: Switch traffic back to previous environment

```bash
# Manual rollback via workflow
gh workflow run build-deploy.yml -f rollback=true

# Blue-green rollback
./scripts/blue-green-deploy.sh rollback
```

## 📚 Best Practices

1. **Security First**: All code changes go through security scanning
2. **Performance Validation**: Every deployment includes performance testing
3. **Zero Downtime**: Blue-green deployments ensure no service interruption
4. **Automated Testing**: Comprehensive test coverage before deployment
5. **Monitoring**: Continuous monitoring with alerting
6. **Documentation**: Keep deployment documentation updated

## 🔄 Continuous Improvement

The CI/CD pipeline is continuously improved with:

- **Performance Optimization**: Regular performance threshold updates
- **Security Enhancement**: New scanning tools and checks
- **Process Automation**: Reducing manual intervention
- **Monitoring Expansion**: More comprehensive observability
- **Feedback Integration**: Team feedback incorporated into improvements
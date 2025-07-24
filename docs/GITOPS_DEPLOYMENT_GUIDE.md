# GitOps Deployment Guide

This guide explains how to use the GitOps CI/CD template for deploying the Blacklist application.

## Overview

The GitOps template provides a complete CI/CD pipeline that:
- Runs parallel quality checks (linting, security scanning, tests)
- Builds and pushes Docker images to private registry
- Packages and uploads Helm charts
- Deploys via ArgoCD with automatic sync
- Generates offline deployment packages
- Provides health checks and rollback capabilities

## Quick Start

### 1. Initial Setup

```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Initialize ArgoCD and GitHub integration
./scripts/setup/argocd-complete-setup.sh
```

### 2. Deploy Application

```bash
# Deploy using GitOps
git add .
git commit -m "feat: deploy application"
git push origin main

# The pipeline will automatically:
# 1. Run tests and quality checks
# 2. Build and push Docker image
# 3. Package Helm chart
# 4. Deploy via ArgoCD
```

### 3. Monitor Deployment

```bash
# Check pipeline status
# Go to GitHub Actions tab in your repository

# Check ArgoCD status
argocd app get blacklist --grpc-web

# Check application health
curl http://192.168.50.110:32452/health
```

## Pipeline Stages

### Stage 1: Pre-flight Checks
- Validates deployment conditions
- Checks for documentation-only changes
- Determines target environment

### Stage 2: Quality Assurance (Parallel)
- **Linting**: Python code style checks (flake8, black, isort)
- **Security**: Vulnerability scanning (bandit, safety, semgrep)
- **Unit Tests**: Fast unit tests with coverage
- **Integration Tests**: API endpoint validation

### Stage 3: Build and Push
- Multi-stage Docker build with caching
- Multiple image tags for versioning
- Push to private registry

### Stage 4: Helm Packaging
- Updates Chart version and image tags
- Packages Helm chart
- Uploads to ChartMuseum

### Stage 5: ArgoCD Deployment
- Creates/updates ArgoCD application
- Enables auto-sync with self-healing
- Progressive rollout with health checks

### Stage 6: Post-Deployment
- Health check validation
- Smoke tests for critical endpoints
- Performance benchmarking
- Rollback on failure

### Stage 7: Offline Package
- Creates self-contained deployment bundle
- Includes Docker image, Helm charts, scripts
- For air-gapped environments

## Configuration

### Required Secrets

Set these in GitHub Settings → Secrets:

```bash
# Registry Authentication
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=bingogo1

# ChartMuseum Authentication
CHARTMUSEUM_USERNAME=admin
CHARTMUSEUM_PASSWORD=bingogo1

# ArgoCD Authentication
ARGOCD_AUTH_TOKEN=<your-token>

# Optional
DEPLOYMENT_WEBHOOK_URL=<slack-webhook>
```

### Environment Variables

Configure in `.env` or GitHub Variables:

```bash
# Application
APP_NAME=blacklist
APP_NAMESPACE=blacklist

# Registry
REGISTRY_URL=registry.jclee.me

# ChartMuseum
CHARTS_URL=https://charts.jclee.me

# ArgoCD
ARGOCD_SERVER=argo.jclee.me
```

## Advanced Usage

### Emergency Deployment

Skip tests for critical fixes:

```bash
# Via workflow dispatch
# Go to Actions → GitOps Template → Run workflow
# Check "Skip tests for emergency deployment"
```

### Manual Environment Selection

```yaml
# In workflow dispatch, select target environment:
- development
- staging  
- production
```

### Multi-Cluster Deployment

The template supports deploying to multiple clusters:

```bash
# Deploy to all clusters
./scripts/all-clusters-deploy.sh

# Deploy to specific cluster
kubectl config use-context production
./scripts/k8s-management.sh deploy
```

### Rollback Procedure

```bash
# Via ArgoCD
argocd app rollback blacklist --grpc-web

# Via Helm
helm rollback blacklist -n blacklist

# Via kubectl
kubectl rollout undo deployment/blacklist -n blacklist
```

## Troubleshooting

### Pipeline Failures

1. **Build Failures**
   ```bash
   # Check logs in GitHub Actions
   # Common issues:
   - Registry authentication
   - Network connectivity
   - Docker daemon issues
   ```

2. **Test Failures**
   ```bash
   # Run tests locally
   pytest tests/ -v
   
   # Check specific test
   pytest tests/test_blacklist_unified.py::test_function_name -v
   ```

3. **Deployment Failures**
   ```bash
   # Check ArgoCD sync status
   argocd app get blacklist --grpc-web
   
   # Check pod status
   kubectl get pods -n blacklist
   kubectl describe pod <pod-name> -n blacklist
   ```

### Health Check Failures

```bash
# Direct health check
curl http://192.168.50.110:32452/health

# Check logs
kubectl logs -f deployment/blacklist -n blacklist

# Check service endpoints
kubectl get endpoints -n blacklist
```

## Best Practices

### 1. Version Tagging
```bash
# Semantic versioning for releases
git tag v1.2.3
git push origin v1.2.3
```

### 2. Branch Strategy
- `main`: Production deployments
- `develop`: Development environment
- `feature/*`: Feature branches (no auto-deploy)

### 3. Commit Messages
```bash
# Use conventional commits
feat: add new IP source
fix: resolve authentication issue
docs: update deployment guide
chore: update dependencies
```

### 4. Security
- Never commit secrets to repository
- Use GitHub Secrets for sensitive data
- Rotate credentials regularly
- Enable branch protection rules

## Monitoring

### Application Metrics
```bash
# View metrics
curl http://192.168.50.110:32452/api/stats

# Collection status
curl http://192.168.50.110:32452/api/collection/status
```

### ArgoCD Dashboard
- URL: https://argo.jclee.me
- Monitor sync status
- View application health
- Check resource usage

### Logs
```bash
# Application logs
kubectl logs -f deployment/blacklist -n blacklist

# ArgoCD logs
argocd app logs blacklist --grpc-web

# Pipeline logs
# Check GitHub Actions tab
```

## Offline Deployment

For air-gapped environments:

1. **Download Package**
   - Go to GitHub Actions
   - Find successful pipeline run
   - Download `blacklist-offline-*.tar.gz`

2. **Extract and Deploy**
   ```bash
   tar -xzf blacklist-offline-*.tar.gz
   cd blacklist-offline-*/
   
   # Load Docker image
   docker load < blacklist-image.tar.gz
   
   # Deploy with Helm
   helm install blacklist blacklist-*.tgz -n blacklist
   ```

## Support

- **Documentation**: See `/docs` directory
- **Issues**: GitHub Issues
- **Logs**: Check pipeline and application logs
- **Health**: Monitor `/health` endpoint

## Summary

The GitOps template provides:
- ✅ Automated CI/CD pipeline
- ✅ Quality assurance checks
- ✅ Multi-environment support
- ✅ Automatic rollback
- ✅ Offline deployment
- ✅ Comprehensive monitoring

Follow this guide to deploy and manage your Blacklist application using GitOps best practices.
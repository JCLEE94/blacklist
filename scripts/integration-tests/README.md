# Integration Tests and Monitoring

This directory contains comprehensive integration tests and monitoring tools for the Blacklist Management System.

## Scripts Overview

### 1. Pre-Deployment Check (`pre-deployment-check.sh`)
Validates all components before deployment to prevent common failures.

**What it checks:**
- Registry connectivity and image availability
- ChartMuseum accessibility and chart existence
- Kubernetes resources and port availability
- ArgoCD configuration and authentication
- Configuration files and settings
- External access and dependencies

**Usage:**
```bash
./scripts/integration-tests/pre-deployment-check.sh
```

**Required Environment Variables:**
```bash
export REGISTRY_USERNAME=admin
export REGISTRY_PASSWORD=bingogo1
export ARGOCD_AUTH_TOKEN=your-token
```

### 2. Full Integration Test (`full-integration-test.sh`)
Comprehensive testing of all deployment components after deployment.

**What it tests:**
- All API endpoints (health, collection, data retrieval)
- Kubernetes resources (pods, services, deployments)
- ArgoCD sync status
- Performance metrics (response time, concurrent requests)
- Data integrity and persistence
- Security (SQL injection, invalid endpoints)

**Usage:**
```bash
./scripts/integration-tests/full-integration-test.sh
```

**Output:**
- Console summary with pass/fail counts
- Detailed log file in `/tmp/integration-test-*.log`

### 3. Continuous Monitoring (`continuous-monitoring.sh`)
Real-time monitoring of deployment health with alerting.

**Features:**
- Health check every 60 seconds
- Pod status monitoring
- Restart loop detection
- Performance metrics (response time, CPU, memory)
- Automatic alerts on failures
- Diagnostic collection on critical issues

**Usage:**
```bash
# Default monitoring (60s interval)
./scripts/integration-tests/continuous-monitoring.sh

# Custom interval (30s)
CHECK_INTERVAL=30 ./scripts/integration-tests/continuous-monitoring.sh
```

## Test Scenarios Covered

### 1. Configuration Issues
- Wrong repository type in ArgoCD
- Incorrect image paths
- Missing namespaces or secrets
- Port conflicts

### 2. Deployment Failures
- Image pull errors
- Resource conflicts
- Memory/CPU constraints
- Health check failures

### 3. External Dependencies
- Registry availability
- ChartMuseum access
- External domain routing
- Reverse proxy issues

### 4. Data Collection
- REGTECH authentication
- SECUDIUM collection
- Data persistence
- Cache functionality

## Prevention Measures Implemented

### 1. Pre-Deployment Validation
Always run pre-deployment checks before any deployment:
```bash
# In CI/CD pipeline
./scripts/integration-tests/pre-deployment-check.sh || exit 1
```

### 2. Post-Deployment Verification
Automatically verify deployment success:
```bash
# After ArgoCD sync
./scripts/integration-tests/full-integration-test.sh
```

### 3. Continuous Monitoring
Keep monitoring running in production:
```bash
# Run in background
nohup ./scripts/integration-tests/continuous-monitoring.sh > monitoring.log 2>&1 &
```

## Integration with CI/CD

### GitHub Actions Integration
Add to `.github/workflows/gitops-template.yml`:

```yaml
- name: Pre-deployment validation
  run: |
    ./scripts/integration-tests/pre-deployment-check.sh

- name: Post-deployment tests
  run: |
    ./scripts/integration-tests/full-integration-test.sh
```

### ArgoCD PostSync Hook
Create ArgoCD post-sync job:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: integration-tests
  annotations:
    argocd.argoproj.io/hook: PostSync
spec:
  template:
    spec:
      containers:
      - name: test
        image: curlimages/curl
        command: ["/bin/sh", "-c"]
        args:
          - |
            curl -f http://blacklist:8541/health || exit 1
            curl -f http://blacklist:8541/api/stats || exit 1
      restartPolicy: Never
```

## Troubleshooting Failed Tests

### Pre-deployment Check Failures

**Registry connectivity failed:**
```bash
# Check registry status
curl -v https://registry.jclee.me/v2/

# Test authentication
docker login registry.jclee.me
```

**ChartMuseum not accessible:**
```bash
# Check ChartMuseum
curl https://charts.jclee.me/index.yaml

# Update Helm repos
helm repo add charts https://charts.jclee.me
helm repo update
```

**Port already allocated:**
```bash
# Find service using port
kubectl get svc -A | grep 32452

# Delete if needed
kubectl delete svc <service-name> -n <namespace>
```

### Integration Test Failures

**API endpoints failing:**
```bash
# Check pod logs
kubectl logs -f deployment/blacklist -n blacklist

# Check service endpoints
kubectl get endpoints -n blacklist
```

**Performance issues:**
```bash
# Check resource usage
kubectl top pods -n blacklist

# Scale if needed
kubectl scale deployment blacklist --replicas=5 -n blacklist
```

### Monitoring Alerts

**System unhealthy:**
1. Check diagnostics file in `/tmp/blacklist-diagnostics-*.log`
2. Review recent pod events
3. Check application logs
4. Verify external dependencies

**High restart count:**
```bash
# Check why pods are restarting
kubectl describe pod <pod-name> -n blacklist

# Check container logs
kubectl logs <pod-name> -n blacklist --previous
```

## Best Practices

1. **Always validate before deployment**
   - Run pre-deployment checks
   - Verify configuration changes
   - Test in staging first

2. **Monitor continuously**
   - Keep monitoring script running
   - Set up proper alerting
   - Review logs regularly

3. **Document failures**
   - Save test logs
   - Create incident reports
   - Update prevention measures

4. **Automate everything**
   - Include tests in CI/CD
   - Use ArgoCD hooks
   - Implement auto-rollback

## Summary

These integration tests and monitoring tools provide comprehensive coverage for preventing and detecting deployment issues. By following the prevention measures and using these tools consistently, you can achieve reliable, automated deployments with minimal risk of failure.
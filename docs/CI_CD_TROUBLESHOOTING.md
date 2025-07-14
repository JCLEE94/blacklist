# CI/CD Pipeline Troubleshooting Guide

## 🚨 Common Issues and Solutions

### 1. Registry Authentication Issues

#### Problem: Docker build fails with registry authentication
```
Error: failed to solve: failed to push registry.jclee.me/blacklist:latest: 
unauthorized: authentication required
```

**Solution:**
1. Verify registry configuration in buildx:
```yaml
config-inline: |
  [registry."registry.jclee.me"]
    http = true
    insecure = true
```

2. Check that the registry doesn't require authentication
3. Ensure `network=host` is set in buildx configuration

#### Problem: ArgoCD Image Updater not detecting new images
```
ArgoCD app shows "OutOfSync" but no new deployment triggered
```

**Solution:**
1. Verify ArgoCD Image Updater annotations match the registry:
```yaml
argocd-image-updater.argoproj.io/image-list: blacklist=registry.jclee.me/blacklist:latest
```

2. Check Image Updater logs:
```bash
kubectl logs -n argocd deployment/argocd-image-updater
```

3. Ensure registry is accessible from ArgoCD cluster:
```bash
kubectl run test-registry --image=registry.jclee.me/blacklist:latest --dry-run=client
```

### 2. Build Performance Issues

#### Problem: Docker builds taking too long (>20 minutes)
**Solution:**
1. Enable build cache:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

2. Use multi-stage builds efficiently
3. Clean up build environment before builds:
```bash
docker system prune -af --volumes
```

#### Problem: Self-hosted runner running out of disk space
**Solution:**
1. Implement disk cleanup in workflow:
```yaml
- name: Free disk space
  run: |
    docker system prune -af --volumes
    rm -rf ~/.cache/pip /tmp/*
```

2. Monitor disk usage:
```bash
df -h
docker system df
```

### 3. Test Failures

#### Problem: Tests fail due to missing dependencies
```
ModuleNotFoundError: No module named 'pytest'
```

**Solution:**
1. Ensure test dependencies are installed:
```bash
pip install pytest pytest-cov pytest-xdist pytest-timeout
```

2. Use requirements-test.txt for test-specific dependencies
3. Cache pip dependencies properly

#### Problem: Integration tests timeout
**Solution:**
1. Increase timeout in workflow:
```yaml
timeout-minutes: 10
```

2. Use pytest timeout markers:
```python
@pytest.mark.timeout(60)
def test_slow_operation():
    pass
```

3. Run tests with timeout option:
```bash
pytest --timeout=30
```

### 4. Deployment Issues

#### Problem: ArgoCD sync fails
```
ComparisonError: failed to compare desired state to live state
```

**Solution:**
1. Check for resource conflicts:
```bash
kubectl get events -n blacklist --sort-by='.lastTimestamp'
```

2. Force sync with ArgoCD:
```bash
argocd app sync blacklist --force --grpc-web
```

3. Check for outdated CRDs or API versions

#### Problem: Pod fails to start after deployment
```
ImagePullBackOff: Failed to pull image
```

**Solution:**
1. Verify image exists in registry:
```bash
docker pull registry.jclee.me/blacklist:latest
```

2. Check imagePullSecrets:
```bash
kubectl get secret regcred -n blacklist -o yaml
```

3. Verify deployment image reference:
```bash
kubectl get deployment blacklist -n blacklist -o yaml | grep image:
```

### 5. Security Scan Issues

#### Problem: Bandit security scan blocks deployment
```
High severity security issues found!
```

**Solution:**
1. Review bandit report:
```bash
bandit -r src/ -f txt
```

2. Fix legitimate security issues
3. Use bandit exclusions for false positives:
```python
# nosec B101
password = "test"  # This is a test password
```

4. Configure bandit severity level:
```bash
bandit -r src/ -ll  # Only report medium and high
```

#### Problem: Safety dependency scan fails
```
Safety: 5 vulnerabilities found
```

**Solution:**
1. Update vulnerable dependencies:
```bash
safety check
pip install --upgrade package-name
```

2. Use safety ignore for unavoidable issues:
```bash
safety check --ignore 12345
```

## 🔧 Debugging Commands

### CI/CD Pipeline Status
```bash
# Check workflow status
gh workflow list
gh run list --workflow=cicd.yml

# View specific run
gh run view RUN_ID

# Download artifacts
gh run download RUN_ID
```

### ArgoCD Operations
```bash
# Check application status
argocd app get blacklist --grpc-web

# View sync history
argocd app history blacklist --grpc-web

# Check Image Updater logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-image-updater

# Force sync
argocd app sync blacklist --force --grpc-web
```

### Kubernetes Debugging
```bash
# Check deployment status
kubectl get deployment blacklist -n blacklist -o wide

# View pod logs
kubectl logs -f deployment/blacklist -n blacklist

# Check events
kubectl get events -n blacklist --sort-by='.lastTimestamp'

# Debug pod startup
kubectl describe pod -l app=blacklist -n blacklist

# Check resource usage
kubectl top pods -n blacklist
```

### Registry Operations
```bash
# Test registry connectivity
curl -I http://registry.jclee.me/v2/

# List repository tags
curl http://registry.jclee.me/v2/blacklist/tags/list

# Check image manifest
curl http://registry.jclee.me/v2/blacklist/manifests/latest
```

## 📊 Monitoring and Alerts

### Health Check Endpoints
- **Application**: `https://blacklist.jclee.me/health`
- **Test**: `https://blacklist.jclee.me/test`
- **Stats**: `https://blacklist.jclee.me/api/stats`

### Performance Benchmarks
- **Response Time**: < 500ms (target: < 100ms)
- **Build Time**: < 10 minutes
- **Test Duration**: < 5 minutes
- **Deploy Time**: < 2 minutes

### Key Metrics to Monitor
1. **Build Success Rate**: > 95%
2. **Test Pass Rate**: > 98%
3. **Deployment Success Rate**: > 99%
4. **Application Uptime**: > 99.5%
5. **Security Scan Pass Rate**: > 90%

## 🚀 Performance Optimization

### Build Optimization
1. **Multi-stage Docker builds**
2. **Build cache utilization**
3. **Parallel job execution**
4. **Dependency caching**

### Test Optimization
1. **Parallel test execution**: `pytest -n auto`
2. **Test categorization**: Unit vs Integration
3. **Smart test selection**: Only run affected tests
4. **Mock external dependencies**

### Deployment Optimization
1. **GitOps automation**: ArgoCD Image Updater
2. **Rolling deployments**: Zero downtime
3. **Health checks**: Fast failure detection
4. **Automatic rollback**: On deployment failure

## 📝 Best Practices

### Security
- Scan all dependencies for vulnerabilities
- Use minimal base images (alpine, distroless)
- Never commit secrets to repository
- Implement security scanning in pipeline

### Quality
- Enforce code formatting (black, isort)
- Run type checking (mypy)
- Maintain test coverage > 80%
- Use linting tools (flake8, bandit)

### Reliability
- Implement proper error handling
- Use timeouts for all operations
- Enable automatic retries
- Monitor pipeline performance

### Maintenance
- Regular dependency updates
- Clean up old artifacts
- Monitor resource usage
- Update documentation

## 🆘 Emergency Procedures

### Pipeline Completely Broken
1. **Skip tests temporarily**:
```bash
git push -o ci.skip
```

2. **Manual deployment**:
```bash
./scripts/k8s-management.sh deploy
```

3. **Rollback to previous version**:
```bash
argocd app rollback blacklist --grpc-web
```

### Production Down
1. **Check application health**:
```bash
curl https://blacklist.jclee.me/health
```

2. **Check pod status**:
```bash
kubectl get pods -n blacklist
```

3. **View recent logs**:
```bash
kubectl logs --tail=100 deployment/blacklist -n blacklist
```

4. **Emergency rollback**:
```bash
kubectl rollout undo deployment/blacklist -n blacklist
```

### Registry Issues
1. **Use alternative registry**:
```bash
docker tag image:latest ghcr.io/jclee94/blacklist:latest
docker push ghcr.io/jclee94/blacklist:latest
```

2. **Update ArgoCD to use alternative**:
```yaml
argocd-image-updater.argoproj.io/image-list: blacklist=ghcr.io/jclee94/blacklist:latest
```

## 📞 Contact Information

- **Repository**: https://github.com/JCLEE94/blacklist
- **ArgoCD**: https://argo.jclee.me
- **Production**: https://blacklist.jclee.me
- **Registry**: registry.jclee.me
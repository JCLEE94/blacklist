# Deployment Checklist

## Pre-Deployment Checklist

### Code Preparation
- [ ] All changes committed and pushed
- [ ] Tests passing locally (`pytest tests/`)
- [ ] Linting passing (`flake8 src/`)
- [ ] No hardcoded secrets in code
- [ ] CHANGELOG.md updated
- [ ] Version bumped if needed

### Configuration
- [ ] Environment variables set in `.env`
- [ ] GitHub Secrets configured
- [ ] ArgoCD application exists
- [ ] Registry credentials valid

### Infrastructure
- [ ] Kubernetes cluster accessible
- [ ] ArgoCD server running
- [ ] Registry available
- [ ] Database backed up

## Deployment Steps

### 1. Regular Deployment
- [ ] Push to main branch
- [ ] Monitor GitHub Actions pipeline
- [ ] Check ArgoCD sync status
- [ ] Verify health endpoint

### 2. Release Deployment
- [ ] Create version tag
- [ ] Push tag to GitHub
- [ ] Verify release created
- [ ] Download offline package

### 3. Emergency Deployment
- [ ] Use workflow dispatch
- [ ] Skip tests if critical
- [ ] Monitor closely
- [ ] Document in incident report

## Post-Deployment Verification

### Application Health
- [ ] Health endpoint responding: `curl http://192.168.50.110:32452/health`
- [ ] All pods running: `kubectl get pods -n blacklist`
- [ ] No restart loops: `kubectl get pods -n blacklist -w`
- [ ] Logs clean: `kubectl logs -f deployment/blacklist -n blacklist`

### Functionality Tests
- [ ] Collection status: `curl http://192.168.50.110:32452/api/collection/status`
- [ ] Stats available: `curl http://192.168.50.110:32452/api/stats`
- [ ] Active IPs loading: `curl http://192.168.50.110:32452/api/blacklist/active`
- [ ] Web UI accessible: `http://192.168.50.110:32452`

### External Access
- [ ] Domain accessible: `https://blacklist.jclee.me`
- [ ] SSL certificate valid
- [ ] Response times normal
- [ ] No 502/503 errors

### Data Integrity
- [ ] IP counts match expected
- [ ] Collection sources active
- [ ] Database queries working
- [ ] Cache functioning

## Rollback Checklist

If issues detected:

### Immediate Actions
- [ ] Stop ArgoCD auto-sync: `argocd app set blacklist --sync-policy none`
- [ ] Rollback deployment: `argocd app rollback blacklist`
- [ ] Verify rollback successful
- [ ] Re-enable auto-sync after fix

### Investigation
- [ ] Collect error logs
- [ ] Check recent commits
- [ ] Review configuration changes
- [ ] Test locally with same config

### Communication
- [ ] Notify team of issues
- [ ] Update status page
- [ ] Document incident
- [ ] Schedule post-mortem

## Security Checklist

### Pre-Deploy
- [ ] No secrets in code
- [ ] Dependencies updated
- [ ] Security scan passed
- [ ] Permissions verified

### Post-Deploy
- [ ] Access logs reviewed
- [ ] Unauthorized access checked
- [ ] Rate limiting active
- [ ] SSL/TLS configured

## Performance Checklist

### Metrics to Monitor
- [ ] Response time < 50ms
- [ ] CPU usage < 80%
- [ ] Memory usage < 2GB
- [ ] No memory leaks
- [ ] Database queries optimized

### Load Testing
- [ ] Concurrent users tested
- [ ] API rate limits verified
- [ ] Cache hit rate > 80%
- [ ] No bottlenecks identified

## Documentation Updates

### After Deployment
- [ ] Update README if needed
- [ ] Update API documentation
- [ ] Update CLAUDE.md
- [ ] Notify users of changes

## Sign-off

- [ ] Development team approval
- [ ] QA verification complete
- [ ] Security review passed
- [ ] Production deployment authorized

---

**Deployment Date**: ________________  
**Version**: ________________  
**Deployed By**: ________________  
**Verified By**: ________________
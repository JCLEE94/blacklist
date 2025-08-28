# ArgoCD CI/CD Pipeline Documentation

## Overview

This document describes the ArgoCD-based CI/CD pipeline for the Blacklist Management System. The pipeline provides automated deployment with GitOps principles, ensuring consistency between the Git repository and the Kubernetes cluster.

## Architecture

```
GitHub → GitHub Actions → Docker Registry → ArgoCD → Kubernetes
                                               ↓
                                        Image Updater
```

## Components

### 1. GitHub Actions Workflow
- **File**: `.github/workflows/argocd-deploy.yml`
- **Triggers**: Push to main branch
- **Steps**:
  1. Run tests and linting
  2. Build Docker image
  3. Push to private registry
  4. Trigger ArgoCD sync

### 2. ArgoCD Application
- **Server**: `argo.jclee.me`
- **Application**: `blacklist`
- **Source**: GitHub repository
- **Path**: `k8s/`
- **Sync Policy**: Automated with self-heal

### 3. ArgoCD Image Updater
- Monitors `registry.jclee.me/blacklist` for new images
- Automatically updates deployment when new images are detected
- Updates Git repository with new image tags

## Setup Instructions

### Prerequisites
- ArgoCD installed and accessible at `argo.jclee.me`
- kubectl configured for your cluster
- Access to private Docker registry

### Initial Setup

1. **Run the setup script**:
   ```bash
   ./scripts/setup/argocd-setup.sh
   ```

2. **Generate ArgoCD auth token for GitHub Actions**:
   ```bash
   ./scripts/argocd-auth-token.sh
   ```

3. **Add secrets to GitHub repository**:
   - Go to Settings → Secrets and variables → Actions
   - Add:
     - `ARGOCD_AUTH_TOKEN`: Token from step 2
     - `REGISTRY_USERNAME`: Docker registry username
     - `REGISTRY_PASSWORD`: Docker registry password

### Manual ArgoCD Commands

```bash
# Login to ArgoCD
argocd login argo.jclee.me --username jclee --password bingogo1

# List applications
argocd app list

# Get application details
argocd app get blacklist

# Sync application manually
argocd app sync blacklist

# View application logs
argocd app logs blacklist

# Delete application (careful!)
argocd app delete blacklist
```

## Deployment Flow

### Automatic Deployment (Recommended)

1. **Code Push**:
   ```bash
   git add .
   git commit -m "feat: your changes"
   git push origin main
   ```

2. **GitHub Actions**:
   - Tests run automatically
   - Docker image built and pushed
   - ArgoCD notified

3. **ArgoCD**:
   - Detects changes in Git
   - Image Updater detects new images
   - Automatically deploys to cluster

### Manual Deployment

```bash
# Build and push image manually
docker build -f deployment/Dockerfile -t registry.jclee.me/blacklist:latest .
docker push registry.jclee.me/blacklist:latest

# Sync ArgoCD
argocd app sync blacklist
```

## Monitoring

### Check Deployment Status
```bash
# ArgoCD status
argocd app get blacklist

# Kubernetes pods
kubectl get pods -n blacklist

# Application health
curl https://blacklist.jclee.me/health
```

### View Logs
```bash
# ArgoCD logs
argocd app logs blacklist -f

# Kubernetes logs
kubectl logs -f deployment/blacklist -n blacklist

# Image updater logs
kubectl logs -f deployment/argocd-image-updater -n argocd
```

## Rollback

### Via ArgoCD
```bash
# View history
argocd app history blacklist

# Rollback to previous version
argocd app rollback blacklist <revision>
```

### Via Kubernetes
```bash
# Rollback deployment
kubectl rollout undo deployment/blacklist -n blacklist

# Check rollback status
kubectl rollout status deployment/blacklist -n blacklist
```

## Troubleshooting

### Common Issues

1. **Sync Failed**:
   ```bash
   # Check sync status
   argocd app get blacklist
   
   # Force sync
   argocd app sync blacklist --force
   ```

2. **Image Update Not Working**:
   ```bash
   # Check image updater logs
   kubectl logs -f deployment/argocd-image-updater -n argocd
   
   # Verify annotations
   kubectl get application blacklist -n argocd -o yaml | grep image-updater
   ```

3. **Authentication Issues**:
   ```bash
   # Recreate registry secret
   kubectl delete secret regcred -n blacklist
   kubectl create secret docker-registry regcred \
     --docker-server=registry.jclee.me \
     --docker-username=qws9411 \
     --docker-password=bingogo1 \
     -n blacklist
   ```

## Security Considerations

1. **Secrets Management**:
   - All credentials stored in Kubernetes secrets
   - GitHub Actions uses repository secrets
   - ArgoCD uses RBAC for access control

2. **Registry Security**:
   - Private registry with authentication
   - Image scanning recommended
   - Use specific tags, not just 'latest'

3. **Git Security**:
   - Use personal access tokens, not passwords
   - Limit token permissions
   - Rotate tokens regularly

## Best Practices

1. **GitOps Principles**:
   - Git as single source of truth
   - All changes via Git commits
   - No manual kubectl apply

2. **Image Management**:
   - Use semantic versioning
   - Tag images with git commit SHA
   - Keep image size minimal

3. **Monitoring**:
   - Set up alerts for sync failures
   - Monitor application health
   - Track deployment frequency

## Advanced Configuration

### Custom Sync Policies
```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
    allowEmpty: false
  syncOptions:
  - CreateNamespace=true
  - PrunePropagationPolicy=foreground
  - PruneLast=true
  retry:
    limit: 5
    backoff:
      duration: 5s
      factor: 2
      maxDuration: 3m
```

### Resource Hooks
```yaml
metadata:
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
```

### Health Checks
```yaml
spec:
  healthChecks:
  - name: blacklist-health
    url: https://blacklist.jclee.me/health
    interval: 30s
    timeout: 10s
```

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [GitHub Actions](https://docs.github.com/en/actions)
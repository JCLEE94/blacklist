# ArgoCD Automatic Image Update Configuration

## Overview
This document describes the ArgoCD configuration for automatic image updates of the Blacklist application.

## Configuration Components

### 1. ArgoCD Application (00-argocd-app.yaml)
- **Auto-sync**: Enabled with `prune: true` and `selfHeal: true`
- **Image Updater Annotations**: Configured to monitor `registry.jclee.me/blacklist:latest`
- **Update Strategy**: Always pull the latest image
- **Write-back Method**: Git-based updates to maintain GitOps principles

### 2. Deployment Configuration (06-deployment.yaml)
- **Image Pull Policy**: Set to `Always` to ensure latest image is pulled
- **Image**: `registry.jclee.me/blacklist:latest`
- **Registry Credentials**: Uses `registry-credentials` secret

### 3. Post-Sync Hook (10-restart-hook.yaml)
- **Purpose**: Forces deployment restart after ArgoCD sync
- **Trigger**: Runs after every successful sync
- **Action**: Executes `kubectl rollout restart` to ensure latest image

## How It Works

1. **GitHub Actions** builds and pushes new image to `registry.jclee.me/blacklist:latest`
2. **ArgoCD** detects changes through:
   - Periodic sync (every 3 minutes by default)
   - Image Updater monitoring the registry
   - Git webhook notifications
3. **Auto-sync** triggers automatically when changes detected
4. **Post-sync hook** forces pod restart to pull latest image
5. **Health checks** verify successful deployment

## ArgoCD Image Updater Annotations

```yaml
annotations:
  argocd-image-updater.argoproj.io/image-list: blacklist=registry.jclee.me/blacklist:latest
  argocd-image-updater.argoproj.io/blacklist.update-strategy: latest
  argocd-image-updater.argoproj.io/blacklist.pull-secret: pullsecret:blacklist/registry-credentials
  argocd-image-updater.argoproj.io/write-back-method: git
  argocd-image-updater.argoproj.io/git-branch: main
```

## Manual Operations (if needed)

### Force Sync
```bash
argocd app sync blacklist --force
```

### Check Application Status
```bash
argocd app get blacklist
```

### View Recent Sync History
```bash
argocd app history blacklist
```

### Rollback to Previous Version
```bash
argocd app rollback blacklist <revision>
```

## Troubleshooting

### Image Not Updating
1. Check ArgoCD sync status: `argocd app get blacklist`
2. Verify image pull policy: `kubectl get deployment blacklist -n blacklist -o yaml | grep imagePullPolicy`
3. Check pod events: `kubectl describe pod -n blacklist -l app.kubernetes.io/name=blacklist`
4. Force restart: `kubectl rollout restart deployment/blacklist -n blacklist`

### Sync Failures
1. Check ArgoCD logs: `kubectl logs -n argocd deployment/argocd-server`
2. Verify manifest syntax: `kubectl apply --dry-run=client -f k8s/manifests/`
3. Check resource quotas: `kubectl describe namespace blacklist`

### Registry Access Issues
1. Verify registry credentials: `kubectl get secret registry-credentials -n blacklist`
2. Test registry access: `docker pull registry.jclee.me/blacklist:latest`
3. Check network policies: `kubectl get networkpolicies -n blacklist`

## Best Practices

1. **Always use `:latest` tag** for continuous deployment
2. **Set imagePullPolicy to Always** for latest tag
3. **Use post-sync hooks** to ensure pod restarts
4. **Monitor ArgoCD metrics** for sync performance
5. **Set up alerts** for sync failures

## Related Files

- `/k8s/manifests/00-argocd-app.yaml` - ArgoCD Application definition
- `/k8s/manifests/06-deployment.yaml` - Kubernetes Deployment
- `/k8s/manifests/10-restart-hook.yaml` - Post-sync restart hook
- `/k8s/manifests/kustomization.yaml` - Kustomize configuration
- `/k8s/argocd-image-updater.yaml` - Image Updater configuration

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/)
- [Kustomize Documentation](https://kustomize.io/)
# DEPRECATION NOTICE

## Migration to Helm Chart

The Kustomize-based deployment in `k8s/base/` has been deprecated in favor of the Helm chart deployment.

### Reason for Migration
- Eliminate duplicate configurations
- Centralize deployment logic
- Better ArgoCD integration
- Simplified maintenance

### New Deployment Method
All deployments are now managed through:
- **Helm Chart**: `chart/blacklist/`
- **ArgoCD Application**: `argocd/blacklist-app.yaml`

### Migration Steps
1. ArgoCD now uses Helm chart at `chart/blacklist/`
2. Production values are in `chart/blacklist/values-production.yaml`
3. All secrets are managed through `blacklist-credentials` secret

### Deprecated Files
The following files in `k8s/base/` are deprecated:
- deployment.yaml
- service.yaml
- ingress.yaml
- pvc.yaml
- redis.yaml
- kustomization.yaml

These are now replaced by Helm templates in `chart/blacklist/templates/`.

### For Manual Deployment
If you need to deploy manually without ArgoCD:
```bash
helm install blacklist ./chart/blacklist \
  -f ./chart/blacklist/values.yaml \
  -f ./chart/blacklist/values-production.yaml \
  -n blacklist --create-namespace
```
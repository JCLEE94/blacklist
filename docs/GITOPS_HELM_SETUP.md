# GitOps with Helm Setup Guide

## Overview

This guide explains the complete GitOps setup for the Blacklist application using:
- **Docker Registry**: `registry.jclee.me` (for container images)
- **Helm Chart Repository**: `charts.jclee.me` (for Helm charts)
- **ArgoCD**: GitOps continuous deployment
- **GitHub Actions**: CI/CD pipeline

## Architecture

```
GitHub Push → GitHub Actions CI/CD
                    ↓
            ┌───────────────┐
            │ Build & Test  │
            └───────┬───────┘
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
┌─────────────────┐   ┌─────────────────┐
│ Docker Registry │   │ Helm Repository │
│registry.jclee.me│   │charts.jclee.me │
└────────┬────────┘   └────────┬────────┘
         ↓                     ↓
         └──────────┬──────────┘
                    ↓
            ┌───────────────┐
            │    ArgoCD     │
            └───────┬───────┘
                    ↓
            ┌───────────────┐
            │  Kubernetes   │
            └───────────────┘
```

## Quick Setup

Run the complete setup script:

```bash
./scripts/complete-gitops-setup.sh
```

This will:
1. Install and configure ArgoCD
2. Install ArgoCD Image Updater
3. Package and push Helm chart
4. Configure Helm repository in ArgoCD
5. Deploy the application

## Manual Setup Steps

### 1. ArgoCD Installation

```bash
# Install ArgoCD
./scripts/setup-gitops.sh

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### 2. ArgoCD Image Updater

```bash
# Install Image Updater for automatic deployments
./scripts/install-image-updater.sh
```

### 3. Helm Chart Management

```bash
# Package and push Helm chart to charts.jclee.me
./scripts/helm-package-push.sh

# Verify chart availability
helm repo add jclee-charts https://charts.jclee.me --username admin --password bingogo1
helm search repo jclee-charts/blacklist
```

### 4. Configure ArgoCD with Helm Repository

```bash
# Add Helm repository to ArgoCD and create application
./scripts/setup-helm-repo-argocd.sh
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/gitops-cicd.yml`) handles:

1. **Code Quality**: Linting, security scanning
2. **Testing**: Unit and integration tests
3. **Docker Build**: Build and push to `registry.jclee.me`
4. **Helm Package**: Package and push to `charts.jclee.me`
5. **GitOps Trigger**: ArgoCD detects changes and deploys

## Helm Chart Structure

```
helm/blacklist/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values
├── values-prod.yaml    # Production overrides
├── values-dev.yaml     # Development overrides
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    ├── secret.yaml
    ├── hpa.yaml
    └── pvc.yaml
```

## ArgoCD Applications

### Using Git Repository (Kustomize)
```yaml
# k8s-gitops/argocd/blacklist-app.yaml
source:
  repoURL: git@github.com:JCLEE94/blacklist.git
  path: k8s-gitops/overlays/prod
```

### Using Helm Repository
```yaml
# k8s-gitops/argocd/blacklist-app-chartrepo.yaml
source:
  repoURL: https://charts.jclee.me
  chart: blacklist
  targetRevision: "*"  # Latest version
```

## Deployment Commands

### Deploy specific version
```bash
# Using Helm directly
helm install blacklist jclee-charts/blacklist --version 1.0.0

# Using ArgoCD
argocd app set blacklist --helm-version 1.0.0
argocd app sync blacklist
```

### Check deployment status
```bash
# ArgoCD status
argocd app get blacklist

# Kubernetes resources
kubectl get all -n blacklist

# Application logs
kubectl logs -f deployment/blacklist -n blacklist
```

### Rollback
```bash
# Using ArgoCD
argocd app rollback blacklist

# Using Helm
helm rollback blacklist
```

## Monitoring

### ArgoCD Dashboard
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open https://localhost:8080
```

### Image Updater Logs
```bash
kubectl logs -f deployment/argocd-image-updater -n argocd
```

### Application Health
```bash
curl http://localhost:32452/health
```

## Troubleshooting

### Chart push fails
```bash
# Check ChartMuseum is running
curl https://charts.jclee.me/health

# Verify credentials
curl -u admin:bingogo1 https://charts.jclee.me/api/charts
```

### ArgoCD sync issues
```bash
# Check application details
argocd app get blacklist --refresh

# Force sync
argocd app sync blacklist --force

# Check events
kubectl get events -n blacklist --sort-by='.lastTimestamp'
```

### Image updater not working
```bash
# Check annotations
kubectl get application blacklist -n argocd -o yaml | grep -A5 annotations

# Check image updater logs
kubectl logs deployment/argocd-image-updater -n argocd | grep blacklist
```

## Security Notes

1. **Registry Authentication**: `registry.jclee.me` doesn't require auth
2. **Chart Repository**: Protected with basic auth (admin/bingogo1)
3. **Secrets Management**: Use external secret management in production
4. **RBAC**: Configure appropriate Kubernetes RBAC for ArgoCD

## Best Practices

1. **Version Tags**: Use semantic versioning for releases
2. **Environment Separation**: Use different values files for dev/staging/prod
3. **Resource Limits**: Always set resource requests and limits
4. **Health Checks**: Configure proper liveness and readiness probes
5. **Monitoring**: Set up alerts for deployment failures

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Helm Documentation](https://helm.sh/docs/)
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/)
- [ChartMuseum](https://chartmuseum.com/)
# Migration to Helm Complete

## Migration Date
$(date +"%Y-%m-%d %H:%M:%S")

## What Changed
- Migrated from Kustomize to Helm Chart
- Consolidated all K8s configurations
- Removed duplicate definitions
- Standardized image references

## New Structure
```
chart/blacklist/          # Helm chart (PRIMARY)
├── Chart.yaml
├── values.yaml          # Default values
├── values-production.yaml  # Production overrides
└── templates/           # K8s templates

argocd/
├── blacklist-app.yaml   # ArgoCD Application
└── production-config.yaml  # Production settings

k8s/base/               # Minimal configs
├── namespace.yaml      # Namespace definition
└── secrets.yaml        # Secret templates
```

## Deployment Commands

### Via ArgoCD (Recommended)
```bash
./scripts/register-argocd-app.sh
```

### Via Helm (Manual)
```bash
helm install blacklist ./chart/blacklist \
  -f ./chart/blacklist/values.yaml \
  -f ./chart/blacklist/values-production.yaml \
  -n blacklist --create-namespace
```

### Update Application
```bash
argocd app sync blacklist
```

## Archived Files
Old Kustomize files archived to: $ARCHIVE_DIR

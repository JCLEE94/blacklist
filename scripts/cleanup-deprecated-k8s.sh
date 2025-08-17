#!/bin/bash
# Cleanup script for deprecated Kustomize configurations
# This script safely archives old configurations before removal

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Cleanup Deprecated K8s Configurations ===${NC}"

# Create archive directory
ARCHIVE_DIR="k8s/archived_$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}Creating archive directory: $ARCHIVE_DIR${NC}"
mkdir -p "$ARCHIVE_DIR"

# Files to archive
DEPRECATED_FILES=(
    "k8s/base/deployment.yaml"
    "k8s/base/service.yaml"
    "k8s/base/ingress.yaml"
    "k8s/base/pvc.yaml"
    "k8s/base/redis.yaml"
    "k8s/base/kustomization.yaml"
    "k8s/current-deployment-status.yaml"
)

# Archive files
echo -e "${YELLOW}Archiving deprecated files...${NC}"
for file in "${DEPRECATED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  Archiving: $file"
        cp "$file" "$ARCHIVE_DIR/" 2>/dev/null || true
    fi
done

# Keep only necessary files in k8s/base/
KEEP_FILES=(
    "k8s/base/namespace.yaml"
    "k8s/base/secrets.yaml"
)

echo -e "${GREEN}Files to keep:${NC}"
for file in "${KEEP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ✓ $file"
    fi
done

# Create migration documentation
cat > k8s/MIGRATION_COMPLETE.md << 'EOF'
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
EOF

echo -e "${GREEN}Migration documentation created: k8s/MIGRATION_COMPLETE.md${NC}"

# Summary
echo -e "${GREEN}=== Cleanup Complete ===${NC}"
echo -e "Deprecated files archived to: ${YELLOW}$ARCHIVE_DIR${NC}"
echo -e "Active deployment method: ${GREEN}Helm Chart via ArgoCD${NC}"
echo -e ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Review archived files in $ARCHIVE_DIR"
echo -e "2. Run ${GREEN}./scripts/register-argocd-app.sh${NC} to register with ArgoCD"
echo -e "3. Verify deployment at ${GREEN}https://blacklist.jclee.me${NC}"
echo -e ""
echo -e "${RED}Note:${NC} You can safely delete $ARCHIVE_DIR after confirming the migration works"
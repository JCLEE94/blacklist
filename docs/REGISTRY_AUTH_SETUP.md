# Docker Registry Authentication Setup

## Overview
Updated the blacklist application to use authenticated access to the private Docker registry at `registry.jclee.me`.

## Changes Made

### 1. Updated Kubernetes Registry Secret
**File:** `k8s/registry-secret.yaml`
- Updated from empty authentication to proper credentials
- Added base64-encoded dockerconfigjson with admin:bingogo1 credentials
- Used by deployment pods for image pulling via `imagePullSecrets`

### 2. Updated ArgoCD Image Updater Configuration  
**File:** `k8s/argocd-image-updater-config.yaml`
- Changed registry API URL from HTTP to HTTPS
- Updated `insecure: yes` to `insecure: no` for secure access
- Updated registry credentials secret with proper authentication
- ArgoCD Image Updater will use these credentials to check for new images

### 3. GitHub Actions Secrets Required
The GitOps pipeline requires these GitHub repository secrets:
- `REGISTRY_USERNAME`: `admin`
- `REGISTRY_PASSWORD`: `bingogo1`

These are already referenced in `.github/workflows/gitops-pipeline.yml` lines 119-120.

## Registry Details
- **URL:** `registry.jclee.me`
- **Username:** `admin`
- **Password:** `bingogo1`
- **Protocol:** HTTPS (secure)
- **Authentication:** Basic Auth

## Authentication Flow
1. **CI/CD Pipeline**: Uses GitHub Secrets to authenticate with registry during image push
2. **Kubernetes Deployment**: Uses `regcred` secret for image pulling
3. **ArgoCD Image Updater**: Uses `registry-credentials` secret in argocd namespace for monitoring

## Verification
Tested authentication locally:
```bash
echo "bingogo1" | docker login registry.jclee.me --username admin --password-stdin
# Login Succeeded
```

## Next Steps
1. Set the GitHub repository secrets (`REGISTRY_USERNAME`, `REGISTRY_PASSWORD`)
2. Deploy updated configurations when cluster is available
3. Verify GitOps pipeline can push images successfully
4. Confirm ArgoCD Image Updater can pull from authenticated registry

## Files Modified
- `k8s/registry-secret.yaml` - Updated pod image pull credentials
- `k8s/argocd-image-updater-config.yaml` - Updated ArgoCD monitoring credentials  
- `.github/workflows/gitops-pipeline.yml` - Already configured for authenticated access

The system is now ready for secure registry operations with proper authentication.
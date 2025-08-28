# Services Configuration

## Overview

This document contains configuration details for all services used in the Blacklist GitOps pipeline.

## Services and Credentials

### 1. Docker Registry
- **URL**: `registry.jclee.me`
- **Username**: `admin`
- **Password**: `bingogo1`
- **Usage**: Container image storage
- **Port**: 443 (HTTPS)

### 2. Helm Chart Repository
- **URL**: `charts.jclee.me`
- **Username**: `admin`
- **Password**: `bingogo1`
- **Usage**: Helm chart storage (ChartMuseum)
- **Port**: 443 (HTTPS)

### 3. ArgoCD Server
- **URL**: `argo.jclee.me`
- **Username**: `admin`
- **Password**: `bingogo1`
- **Usage**: GitOps continuous deployment
- **Port**: 443 (HTTPS)

## GitHub Actions Secrets

Configure these secrets in your GitHub repository:

```bash
# Required secrets
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=bingogo1
HELM_REPO_USERNAME=admin
HELM_REPO_PASSWORD=bingogo1
```

## Kubernetes Secrets

### Registry Authentication
```bash
# Create registry secret
kubectl create secret docker-registry regcred \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=bingogo1 \
  --docker-email=admin@jclee.me \
  -n blacklist
```

### ArgoCD Repository Secrets

#### Git Repository
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: github-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:JCLEE94/blacklist.git
  sshPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    <your-ssh-private-key>
    -----END RSA PRIVATE KEY-----
```

#### Helm Repository
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: charts-jclee-me
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  url: https://charts.jclee.me
  username: admin
  password: bingogo1
```

## ArgoCD CLI Commands

### Login to External ArgoCD
```bash
argocd login argo.jclee.me \
  --username admin \
  --password bingogo1 \
  --grpc-web
```

### Add Repositories
```bash
# Add Helm repository
argocd repo add https://charts.jclee.me \
  --type helm \
  --name jclee-charts \
  --username admin \
  --password bingogo1

# Add Git repository
argocd repo add git@github.com:JCLEE94/blacklist.git \
  --ssh-private-key-path ~/.ssh/id_rsa
```

## Docker Commands

### Login to Registry
```bash
docker login registry.jclee.me -u admin -p bingogo1
```

### Build and Push
```bash
docker build -t registry.jclee.me/blacklist:latest .
docker push registry.jclee.me/blacklist:latest
```

## Helm Commands

### Add Chart Repository
```bash
helm repo add jclee-charts https://charts.jclee.me \
  --username admin \
  --password bingogo1
helm repo update
```

### Push Chart to Repository
```bash
# Package chart
helm package helm/blacklist

# Push to ChartMuseum
curl --data-binary "@blacklist-1.0.0.tgz" \
  -u admin:bingogo1 \
  https://charts.jclee.me/api/charts
```

## Complete Setup Commands

### Using Local ArgoCD
```bash
./scripts/complete-gitops-setup.sh
```

### Using External ArgoCD
```bash
./scripts/complete-gitops-setup.sh --external
```

## Environment Variables

### CI/CD Pipeline
```bash
export REGISTRY=registry.jclee.me
export REGISTRY_USERNAME=admin
export REGISTRY_PASSWORD=bingogo1
export HELM_REPO_URL=https://charts.jclee.me
export HELM_REPO_USERNAME=admin
export HELM_REPO_PASSWORD=bingogo1
```

### Local Development
```bash
# Add to ~/.bashrc or ~/.zshrc
export DOCKER_REGISTRY=registry.jclee.me
export HELM_REPO=charts.jclee.me
export ARGOCD_SERVER=argo.jclee.me
```

## Security Notes

1. **Production Usage**: 
   - Change default passwords immediately
   - Use separate credentials for each service
   - Implement proper RBAC in Kubernetes
   - Use external secret management (Vault, Sealed Secrets)

2. **Network Security**:
   - All services use HTTPS/TLS
   - Consider implementing mutual TLS
   - Use private networks where possible

3. **Access Control**:
   - Limit registry access by IP
   - Enable ArgoCD SSO/OIDC
   - Implement audit logging

## Troubleshooting

### Registry Authentication Issues
```bash
# Test registry access
curl -u admin:bingogo1 https://registry.jclee.me/v2/_catalog

# Check Docker config
cat ~/.docker/config.json
```

### Helm Repository Issues
```bash
# Test ChartMuseum API
curl -u admin:bingogo1 https://charts.jclee.me/api/charts

# List available charts
curl -u admin:bingogo1 https://charts.jclee.me/index.yaml
```

### ArgoCD Connection Issues
```bash
# Check ArgoCD server status
curl https://argo.jclee.me/api/v1/session

# Test with argocd CLI
argocd account get-user-info
```
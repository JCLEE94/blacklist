# Kubernetes Deployment Guide

## Directory Structure

```
k8s/
├── base/                  # Base Kubernetes manifests
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── pvc.yaml
│   ├── redis.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/              # Development environment
│   ├── staging/          # Staging environment
│   └── prod/             # Production environment
```

## Deployment Options

### 1. Using kubectl with Kustomize

```bash
# Deploy to production
kubectl apply -k k8s/base/

# Deploy to specific environment
kubectl apply -k k8s/overlays/prod/
```

### 2. Using Helm Chart

```bash
# Add dependencies
helm dependency update helm/blacklist

# Install
helm install blacklist helm/blacklist \
  --namespace blacklist \
  --create-namespace \
  --values helm/blacklist/values.yaml

# Upgrade
helm upgrade blacklist helm/blacklist \
  --namespace blacklist \
  --values helm/blacklist/values.yaml
```

### 3. Using ArgoCD

```bash
# Apply ArgoCD application
kubectl apply -f argocd/application.yaml

# Sync manually (if auto-sync disabled)
argocd app sync blacklist
```

## Configuration

### Secrets Management

Before deploying, update the secrets in `k8s/base/secrets.yaml`:

```yaml
stringData:
  database-url: "your-database-url"
  secret-key: "your-secret-key"
  jwt-secret-key: "your-jwt-secret"
  regtech-username: "your-regtech-username"
  regtech-password: "your-regtech-password"
  secudium-username: "your-secudium-username"
  secudium-password: "your-secudium-password"
```

### Image Registry Authentication

Create GitHub Container Registry credentials:

```bash
kubectl create secret docker-registry ghcr-credentials \
  --docker-server=registry.jclee.me \
  --docker-username=jclee94 \
  --docker-password=<YOUR_GITHUB_TOKEN> \
  --namespace=blacklist
```

### Storage Configuration

The application uses PersistentVolumeClaims for data persistence:
- `blacklist-pvc`: 5Gi for application data
- `redis-pvc`: 1Gi for Redis cache

Adjust sizes in `k8s/base/pvc.yaml` as needed.

## Monitoring

The application exposes Prometheus metrics at `/metrics`. Configure your Prometheus instance to scrape:

```yaml
- job_name: 'blacklist'
  kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
      - blacklist
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    action: keep
    regex: true
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
    action: replace
    target_label: __metrics_path__
    regex: (.+)
  - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
    action: replace
    regex: ([^:]+)(?::\d+)?;(\d+)
    replacement: $1:$2
    target_label: __address__
```

## Health Checks

The application provides health check endpoints:
- `/health`: Basic health check
- `/ready`: Readiness probe
- `/api/health`: Detailed health status

## Scaling

### Manual Scaling
```bash
kubectl scale deployment blacklist --replicas=5 -n blacklist
```

### Auto-scaling
Enable HPA in Helm values:
```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n blacklist
kubectl describe pod <pod-name> -n blacklist
kubectl logs <pod-name> -n blacklist
```

### Check Service Endpoints
```bash
kubectl get svc -n blacklist
kubectl get endpoints -n blacklist
```

### Port Forwarding for Testing
```bash
kubectl port-forward svc/blacklist-service 8080:80 -n blacklist
```

### ArgoCD Sync Issues
```bash
argocd app get blacklist
argocd app sync blacklist --force
argocd app logs blacklist
```

## Security Notes

1. Always use secrets for sensitive data
2. Enable RBAC and network policies in production
3. Use TLS for ingress with cert-manager
4. Regularly update container images
5. Implement pod security policies
# GitOps Deployment Guide

## Overview

This guide documents the complete GitOps automation workflow for the Blacklist Management System using CNCF-compliant tools and jclee.me infrastructure.

## Infrastructure Components

### jclee.me Services
- **Docker Registry**: `registry.jclee.me` (private registry)
- **Kubernetes Cluster**: `k8s.jclee.me` (production cluster)
- **ArgoCD Dashboard**: `argo.jclee.me` (GitOps controller)
- **Application URL**: `blacklist.jclee.me` (production endpoint)

### Architecture Stack
- **Container Orchestration**: Kubernetes
- **GitOps**: ArgoCD
- **CI/CD**: GitHub Actions
- **Configuration Management**: Kustomize
- **Container Registry**: Private registry.jclee.me
- **Monitoring**: Prometheus + Grafana
- **Security**: Cosign for image signing

## Deployment Workflow

### 1. Development Workflow
```bash
# Local development
git checkout -b feature/new-feature
# Make changes...
git commit -m "feat: add new feature"
git push origin feature/new-feature

# Create PR
gh pr create --title "Add new feature"
```

### 2. CI/CD Pipeline Triggers

#### On Pull Request:
- Security scanning (Trivy)
- Unit tests with coverage
- Code quality checks

#### On Main Branch Push:
1. **Build Phase**
   - Build multi-arch Docker image
   - Sign with Cosign
   - Push to registry.jclee.me
   - Auto-increment version

2. **Deploy Phase**
   - Update Kustomize manifests
   - Commit GitOps changes
   - Trigger ArgoCD sync
   - Wait for deployment completion

3. **Verify Phase**
   - Health checks
   - Smoke tests
   - Monitoring alerts

### 3. ArgoCD GitOps Flow
```
GitHub Repository → ArgoCD → Kubernetes Cluster
     ↓                 ↓           ↓
  k8s/ manifests → Sync Engine → Live Resources
```

## Directory Structure

```
/
├── k8s/
│   ├── base/                    # Base Kustomize resources
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   └── ...
│   └── overlays/
│       └── production/          # Production-specific configs
│           ├── kustomization.yaml
│           ├── deployment-patch.yaml
│           └── ...
├── argocd/
│   ├── application.yaml         # ArgoCD Application
│   └── project.yaml            # ArgoCD Project
├── .github/workflows/
│   ├── gitops-cicd.yaml        # Main CI/CD pipeline
│   └── infrastructure-setup.yaml
└── docs/
    └── GITOPS_DEPLOYMENT_GUIDE.md
```

## Required GitHub Secrets

### Docker Registry
- `DOCKER_REGISTRY_USER`: Registry username
- `DOCKER_REGISTRY_PASS`: Registry password

### Kubernetes Access
- `KUBE_CONFIG`: Base64-encoded kubeconfig

### ArgoCD Access
- `ARGOCD_AUTH_TOKEN`: ArgoCD authentication token

### Application Secrets
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `REGTECH_USERNAME`: REGTECH API username
- `REGTECH_PASSWORD`: REGTECH API password
- `SECUDIUM_USERNAME`: SECUDIUM API username
- `SECUDIUM_PASSWORD`: SECUDIUM API password

## Deployment Commands

### Manual Deployment
```bash
# Trigger deployment
gh workflow run gitops-cicd.yaml

# Monitor deployment
argocd app sync blacklist-app --force
argocd app wait blacklist-app --timeout 600
```

### Infrastructure Setup
```bash
# Setup all infrastructure
gh workflow run infrastructure-setup.yaml --field setup_type=all

# Setup only secrets
gh workflow run infrastructure-setup.yaml --field setup_type=secrets
```

### Local Testing
```bash
# Test Kustomize build
kustomize build k8s/overlays/production

# Validate YAML
kubectl apply --dry-run=client -k k8s/overlays/production
```

## Monitoring and Observability

### Health Checks
- **Liveness Probe**: `/health` (every 30s)
- **Readiness Probe**: `/ready` (every 10s)
- **Startup Probe**: `/health` (initial 10s delay)

### Metrics
- **Prometheus Metrics**: `/metrics`
- **ServiceMonitor**: Auto-discovery enabled
- **Alerts**: CPU, Memory, Pod availability

### Logging
- **Structured Logging**: JSON format
- **Log Aggregation**: FluentD collection
- **Log Levels**: DEBUG, INFO, WARN, ERROR

## Security Features

### Container Security
- **Non-root User**: UID 1000
- **Read-only Filesystem**: Where possible
- **Security Context**: Restricted capabilities
- **Image Scanning**: Trivy vulnerability scanning
- **Image Signing**: Cosign signatures

### Network Security
- **Network Policies**: Restrict pod communication
- **Ingress Control**: NGINX with rate limiting
- **Service Mesh**: Istio-ready configuration

### Secrets Management
- **Kubernetes Secrets**: Encrypted at rest
- **External Secrets**: Future CSI integration
- **Secret Rotation**: Manual for now

## High Availability

### Deployment Strategy
- **Rolling Updates**: Zero-downtime deployments
- **Replica Count**: 3 pods minimum in production
- **Pod Anti-affinity**: Spread across nodes

### Auto-scaling
- **HPA**: CPU/Memory-based scaling
- **Min Replicas**: 3
- **Max Replicas**: 10
- **Scale Policy**: Conservative scaling

### Disaster Recovery
- **Multi-zone**: Pod distribution
- **PVC Backup**: Storage snapshots
- **Config Backup**: GitOps repository

## Troubleshooting

### Common Issues
```bash
# Check ArgoCD application status
argocd app get blacklist-app

# View pod logs
kubectl logs -n blacklist-system deployment/blacklist-deployment

# Check resource usage
kubectl top pods -n blacklist-system

# Describe deployment
kubectl describe deployment blacklist-deployment -n blacklist-system
```

### Rollback Procedures
```bash
# Rollback via ArgoCD
argocd app rollback blacklist-app

# Rollback via kubectl
kubectl rollout undo deployment/blacklist-deployment -n blacklist-system

# Check rollout status
kubectl rollout status deployment/blacklist-deployment -n blacklist-system
```

## Performance Optimization

### Resource Limits
- **CPU**: 2 cores limit, 0.5 cores request
- **Memory**: 2GB limit, 512MB request
- **Storage**: Fast SSD storage class

### Caching Strategy
- **Redis**: Dedicated Redis pod
- **Application Cache**: In-memory + Redis
- **Static Assets**: NGINX caching

### Database Optimization
- **SQLite**: Local file-based storage
- **Connection Pooling**: Application-level
- **Index Optimization**: Automated

## Compliance and Governance

### GitOps Principles
1. **Declarative**: All config in Git
2. **Versioned**: Full audit trail
3. **Automated**: Self-healing deployments
4. **Observable**: Comprehensive monitoring

### Security Compliance
- **RBAC**: Role-based access control
- **Pod Security Standards**: Restricted profile
- **Network Segmentation**: Namespace isolation
- **Audit Logging**: All K8s API calls logged

## Future Enhancements

### Planned Improvements
- **Service Mesh**: Istio integration
- **External Secrets**: CSI driver
- **Progressive Delivery**: Flagger for canary deployments
- **Chaos Engineering**: Litmus integration
- **Backup Automation**: Velero snapshots

### Monitoring Enhancements
- **Distributed Tracing**: Jaeger integration
- **Advanced Metrics**: Custom Prometheus metrics
- **SLI/SLO**: Service level indicators
- **Alerting**: PagerDuty integration

## Contact Information

- **Project Owner**: jclee94@jclee.me
- **ArgoCD Dashboard**: https://argo.jclee.me
- **Application**: https://blacklist.jclee.me
- **Documentation**: https://github.com/JCLEE94/blacklist
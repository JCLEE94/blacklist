# Deployment Pipeline Configurations

## Two Deployment Scenarios

### Scenario 1: Offline Production (Air-gapped)
**Flow**: Development → NAS Registry → Staging (ArgoCD) → Production (Offline K8s)

**Characteristics**:
- Production is air-gapped/offline environment
- Staging uses ArgoCD for GitOps deployment
- Requires offline package creation for production
- Manual transfer to production environment

### Scenario 2: Online Production
**Flow**: Development → NAS Registry → Production (ArgoCD)

**Characteristics**:
- Production uses ArgoCD for automated deployment
- Staging is optional offline test environment
- Continuous deployment to production possible
- No manual package transfer required

## Key Technologies
- **CI/CD**: GitHub Actions with self-hosted runners
- **Container Registry**: NAS private registry
- **Orchestration**: Kubernetes + ArgoCD
- **Packaging**: Docker save/load for offline environments
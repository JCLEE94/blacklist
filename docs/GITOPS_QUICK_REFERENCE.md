# GitOps Quick Reference

## 🚀 Deployment Commands

```bash
# Standard deployment (push to main)
git add . && git commit -m "feat: your changes"
git push origin main

# Emergency deployment (skip tests)
# Use GitHub Actions UI → Run workflow → Check "Skip tests"

# Manual deployment
./scripts/k8s-management.sh deploy

# Multi-cluster deployment
./scripts/multi-deploy.sh
```

## 🔍 Status Checks

```bash
# Pipeline status
# GitHub → Actions tab

# ArgoCD status
argocd app get blacklist --grpc-web

# Application health
curl http://192.168.50.110:32452/health

# Pod status
kubectl get pods -n blacklist
```

## 🛠️ Troubleshooting

```bash
# View logs
kubectl logs -f deployment/blacklist -n blacklist

# Sync ArgoCD
argocd app sync blacklist --force --grpc-web

# Rollback
argocd app rollback blacklist --grpc-web

# Restart pods
kubectl rollout restart deployment/blacklist -n blacklist
```

## 📊 Monitoring

```bash
# Stats
curl http://192.168.50.110:32452/api/stats

# Collection status
curl http://192.168.50.110:32452/api/collection/status

# Active IPs count
curl -s http://192.168.50.110:32452/api/blacklist/active | wc -l
```

## 🔐 Secrets Setup

```bash
# GitHub Settings → Secrets → Actions
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=bingogo1
ARGOCD_AUTH_TOKEN=<your-token>
```

## 📦 Offline Deployment

```bash
# Download from GitHub Actions artifacts
tar -xzf blacklist-offline-*.tar.gz
cd blacklist-offline-*/
docker load < blacklist-image.tar.gz
helm install blacklist blacklist-*.tgz
```

## 🏷️ Versioning

```bash
# Create release
git tag v1.2.3
git push origin v1.2.3
```

## 🌐 URLs

- **Application**: http://192.168.50.110:32452
- **External**: https://blacklist.jclee.me
- **ArgoCD**: https://argo.jclee.me
- **Registry**: https://registry.jclee.me

## ⚡ Common Issues

| Issue | Solution |
|-------|----------|
| ImagePullBackOff | Check registry auth: `kubectl get secret regcred -n blacklist -o yaml` |
| 502 Error | Check ingress: `kubectl get ingress -n blacklist` |
| Sync Failed | Manual sync: `argocd app sync blacklist --force` |
| Tests Failed | Run locally: `pytest tests/ -v` |

## 📈 Performance

- Build time: ~2-3 minutes
- Deployment: ~1 minute
- Rollback: ~30 seconds
- Health check: <1 second
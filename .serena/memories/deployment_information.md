# Deployment Information

## Production Infrastructure
- **Docker Registry**: `registry.jclee.me` (private)
- **Production Server**: `docker@192.168.50.215:1111`
- **Registry Port**: 1234
- **Application Ports**: 
  - Development: 8541
  - Production: 2541

## Deployment Process
```bash
# Full deployment command
./deployment/deploy.sh

# What it does:
1. Cleans cache files and __pycache__
2. Builds Docker image with --no-cache
3. Tags as latest and timestamp version
4. Pushes to registry.jclee.me
5. SSH to production server
6. Runs docker-compose with new image
7. Cleans up old images
```

## Container Configuration
- Base image: Python 3.9 Alpine
- Multi-stage build for size optimization
- Non-root user (blacklist:blacklist)
- Health check endpoint: /health
- Auto-restart: unless-stopped

## Environment Variables (Production)
```bash
# Required in docker-compose.yml
REGTECH_USERNAME=nextrade
REGTECH_PASSWORD=Sprtmxm1@3
SECUDIUM_USERNAME=nextrade
SECUDIUM_PASSWORD=Sprtmxm1@3
PORT=2541
SECRET_KEY=your-secret-key
REDIS_URL=redis://blacklist-redis:6379/0
```

## Monitoring
- Watchtower for automatic container updates
- Health checks every 30 seconds
- Logs persisted in Docker volumes
- Grafana/Prometheus ready (optional)

## CI/CD Pipeline
- GitLab CI/CD configured
- Automatic deployment on main branch push
- Build → Test → Deploy → Notify
- Docker layer caching for faster builds

## Backup Strategy
- SQLite database backed up before deployment
- 30-day retention for database backups
- Configuration files versioned in Git
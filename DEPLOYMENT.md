# Deployment Guide

## Environment-based Configuration

All configuration is managed through `.env` files to eliminate hardcoding.

### Available Environments

1. **Development** (`.env.development`)
   - Port: 8541
   - Pure Docker volumes (dev environment)
   - Debug mode enabled
   - Watchtower disabled

2. **Production** (`.env.production`)
   - Port: 2541
   - Docker volumes with Synology NAS bind mounts
   - Production optimized
   - Watchtower enabled

3. **Docker Volumes** (`.env.docker-volumes`)
   - Port: 2541
   - Pure Docker volumes (no host bind mounts)
   - Portable and isolated
   - Easy backup/restore

### Quick Deployment

```bash
# Production deployment (Synology NAS)
./deploy-env.sh production

# Development deployment (pure Docker volumes)
./deploy-env.sh development

# Docker volumes deployment (portable)
./deploy-env.sh docker-volumes

# Custom environment
./deploy-env.sh staging
```

### Docker Volume Management

```bash
# Create volumes
./manage-volumes.sh production create

# Check volume status
./manage-volumes.sh production status

# Backup volumes
./manage-volumes.sh production backup

# Restore from backup
./manage-volumes.sh production restore ./backups/20241226-123456

# Remove volumes (with confirmation)
./manage-volumes.sh production remove

# Inspect volume details
./manage-volumes.sh production inspect
```

### Manual Deployment

```bash
# 1. Copy environment template
cp .env.example .env.production

# 2. Edit configuration
nano .env.production

# 3. Deploy with environment
docker-compose -f docker-compose.single.yml --env-file .env.production up -d
```

### Environment Variables

 < /dev/null |  Variable | Description | Default |
|----------|-------------|---------|
| `DOCKER_REGISTRY` | Docker registry URL | `registry.jclee.me` |
| `IMAGE_NAME` | Container image name | `blacklist` |
| `IMAGE_TAG` | Image tag | `latest` |
| `HOST_PORT` | Host port mapping | `2541` |
| `VOLUME_INSTANCE_PATH` | SQLite database volume | `./instance` |
| `VOLUME_DATA_PATH` | Data files volume | `./data` |
| `VOLUME_LOGS_PATH` | Log files volume | `./logs` |
| `REGTECH_USERNAME` | REGTECH authentication | Required |
| `REGTECH_PASSWORD` | REGTECH authentication | Required |
| `SECUDIUM_USERNAME` | SECUDIUM authentication | Required |
| `SECUDIUM_PASSWORD` | SECUDIUM authentication | Required |

### Security Best Practices

1. **Never commit `.env` files** - they contain secrets
2. **Use strong secret keys** in production
3. **Restrict file permissions**: `chmod 600 .env.*`
4. **Rotate credentials** regularly

### Troubleshooting

```bash
# Check container logs
docker logs blacklist -f

# Check environment loading
docker-compose -f docker-compose.single.yml --env-file .env.production config

# Verify volumes
docker inspect blacklist | grep -A 10 Mounts
```

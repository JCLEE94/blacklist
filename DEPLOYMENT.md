# Deployment Guide

## Environment-based Configuration

All configuration is managed through `.env` files to eliminate hardcoding.

### Available Environments

1. **Development** (`.env.development`)
   - Port: 8541
   - Local volumes
   - Debug mode enabled
   - Watchtower disabled

2. **Production** (`.env.production`)
   - Port: 2541
   - Synology NAS volumes
   - Production optimized
   - Watchtower enabled

### Quick Deployment

```bash
# Production deployment
./deploy-env.sh production

# Development deployment  
./deploy-env.sh development

# Custom environment
./deploy-env.sh staging
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

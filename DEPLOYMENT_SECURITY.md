# Secure Deployment Guide

This guide covers secure deployment practices for the Blacklist Management System with proper secret management.

## 🔐 Security Overview

### Critical Security Requirements

1. **No Hardcoded Secrets**: All sensitive values must be injected at build/runtime
2. **Environment Isolation**: Separate configurations for development, staging, production
3. **Secret Rotation**: Regular rotation of all sensitive credentials
4. **Minimal Permissions**: Containers run with least required privileges

## 🚀 Quick Secure Deployment

### Step 1: Prepare Environment

Create `.env.production` file with your secrets:

```bash
# Copy template and edit
cp .env.production.template .env.production

# Edit with your secrets (never commit this file)
nano .env.production
```

### Step 2: Build Securely

```bash
# Build with secure script (recommended)
./scripts/secure-build.sh --env-file .env.production

# Or build with direct environment variables
SECRET_KEY="your-secret-key" \
JWT_SECRET_KEY="your-jwt-secret" \
DEFAULT_API_KEY="your-api-key" \
ADMIN_PASSWORD="your-admin-password" \
./scripts/secure-build.sh
```

### Step 3: Deploy

```bash
# Deploy with docker-compose (loads .env.production)
docker-compose up -d

# Check health
curl -f http://localhost:2541/health
```

## 📋 Environment Files

### `.env.production` (Required - DO NOT COMMIT)

```bash
# Application Secrets
SECRET_KEY=your-32-character-secret-key-here
JWT_SECRET_KEY=your-32-character-jwt-secret-here
DEFAULT_API_KEY=blk_your-api-key-here
ADMIN_PASSWORD=your-secure-admin-password

# Database
POSTGRES_PASSWORD=your-database-password
DATABASE_URL=postgresql://blacklist:${POSTGRES_PASSWORD}@postgres:5432/blacklist

# External Services
REGTECH_USERNAME=your-regtech-username
REGTECH_PASSWORD=your-regtech-password
SECUDIUM_USERNAME=your-secudium-username
SECUDIUM_PASSWORD=your-secudium-password

# Optional Configuration
PORT=2541
FLASK_ENV=production
LOG_LEVEL=INFO
COLLECTION_ENABLED=true
FORCE_DISABLE_COLLECTION=false
```

### `.env.production.template` (Safe to Commit)

```bash
# Template file - copy to .env.production and fill in values
SECRET_KEY=changeme-generate-32-char-secret
JWT_SECRET_KEY=changeme-generate-32-char-jwt-secret
DEFAULT_API_KEY=changeme-generate-api-key
ADMIN_PASSWORD=changeme-generate-secure-password
POSTGRES_PASSWORD=changeme-generate-db-password

# External Services (optional)
REGTECH_USERNAME=
REGTECH_PASSWORD=
SECUDIUM_USERNAME=  
SECUDIUM_PASSWORD=

# Configuration
PORT=2541
FLASK_ENV=production
LOG_LEVEL=INFO
```

## 🔧 Build Options

### Secure Build Script Usage

```bash
# Show help
./scripts/secure-build.sh --help

# Build with environment file
./scripts/secure-build.sh --env-file .env.production

# Build with custom image name/tag
./scripts/secure-build.sh --name myapp --tag v1.0 --env-file .env.production

# Build with environment variables
SECRET_KEY="xxx" JWT_SECRET_KEY="yyy" ./scripts/secure-build.sh
```

### Manual Docker Build (Not Recommended)

```bash
# Build with build args (secrets exposed in build history)
docker build \
  --build-arg SECRET_KEY="your-secret" \
  --build-arg JWT_SECRET_KEY="your-jwt-secret" \
  --build-arg DEFAULT_API_KEY="your-api-key" \
  --build-arg ADMIN_PASSWORD="your-password" \
  -t blacklist:latest .
```

## 🛡️ Security Best Practices

### Secret Generation

```bash
# Generate secure secrets
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DEFAULT_API_KEY="blk_$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")"
ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
```

### File Permissions

```bash
# Secure environment file permissions
chmod 600 .env.production
chown root:root .env.production  # If running as root

# Verify permissions
ls -la .env.production
# Should show: -rw------- 1 root root
```

### Secret Rotation

```bash
# 1. Generate new secrets
./scripts/generate-secrets.sh > .env.production.new

# 2. Test with new secrets
mv .env.production .env.production.old
mv .env.production.new .env.production
docker-compose up -d

# 3. Verify everything works
curl -f http://localhost:2541/health

# 4. Remove old file
rm .env.production.old
```

## 🔍 Security Validation

### Pre-deployment Checks

```bash
# 1. Check for hardcoded secrets in images
docker history --no-trunc blacklist:latest | grep -i secret

# 2. Security scan with Trivy
trivy image --severity HIGH,CRITICAL blacklist:latest

# 3. Check environment file permissions
ls -la .env.production

# 4. Validate secret strength
./scripts/validate-secrets.sh .env.production
```

### Runtime Security

```bash
# Check running container security
docker exec blacklist-app ps aux  # Should not show secrets
docker logs blacklist-app | grep -i secret  # Should be empty

# Network security
docker network ls
docker port blacklist-app  # Check exposed ports
```

## 🚨 Security Incidents

### If Secrets Are Compromised

1. **Immediate Actions**:
   ```bash
   # Stop services immediately
   docker-compose down
   
   # Generate new secrets
   ./scripts/generate-secrets.sh > .env.production
   
   # Rebuild with new secrets
   ./scripts/secure-build.sh --env-file .env.production
   
   # Redeploy
   docker-compose up -d
   ```

2. **Cleanup**:
   ```bash
   # Remove old images with embedded secrets
   docker image prune -a
   
   # Clear build cache
   docker builder prune -a
   
   # Check git history for accidentally committed secrets
   git log --all --grep="SECRET_KEY\|JWT_SECRET\|ADMIN_PASSWORD" -p
   ```

## 📊 Monitoring & Alerts

### Security Monitoring

```bash
# Set up log monitoring for security events
docker logs blacklist-app | grep -E "(WARN|ERROR|CRITICAL)"

# Monitor failed authentication attempts
docker logs blacklist-app | grep "authentication failed"

# Check for unusual API activity
docker logs blacklist-app | grep "rate limit exceeded"
```

### Health Monitoring

```bash
# Application health
curl -f http://localhost:2541/health

# Database health  
docker exec blacklist-db pg_isready -U blacklist

# Redis health
docker exec blacklist-redis redis-cli ping
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Secure Deployment

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build with secrets
        env:
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
          DEFAULT_API_KEY: ${{ secrets.DEFAULT_API_KEY }}
          ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}
        run: ./scripts/secure-build.sh
      
      - name: Security scan
        run: trivy image --severity HIGH,CRITICAL blacklist:latest
      
      - name: Deploy to production
        run: docker-compose up -d
```

## ❓ Troubleshooting

### Common Issues

1. **Build fails with "required build arg"**:
   - Ensure all required environment variables are set
   - Check `.env.production` file exists and has correct format

2. **Container fails to start**:
   - Check logs: `docker logs blacklist-app`
   - Verify database connectivity: `docker logs blacklist-db`

3. **Secrets visible in container**:
   - Don't use `docker exec` to check environment variables
   - Secrets should only be visible during build, not runtime

### Debug Commands

```bash
# Check container environment (should not show secrets)
docker exec blacklist-app env | grep -v SECRET

# Check build history (should not show secret values)
docker history --no-trunc blacklist:latest

# Verify file permissions
docker exec blacklist-app ls -la /app/instance/
```

---

## 📞 Support

For security issues or questions:
- Create an issue with tag `security`
- For sensitive security issues, contact maintainers directly
- Review security audit findings in `security-performance-report.md`
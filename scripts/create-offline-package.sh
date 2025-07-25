#!/bin/bash

# Offline Package Creator for Blacklist Management System
# Creates a complete offline deployment package with deployment scripts

set -e

PACKAGE_NAME="blacklist-offline-$(date +'%Y%m%d-%H%M%S')"
PACKAGE_DIR="/tmp/$PACKAGE_NAME"
REGISTRY="registry.jclee.me/jclee94/blacklist"
IMAGE_TAG="latest"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=========================================="
echo "Offline Package Creator"
echo "=========================================="

# Create package structure
mkdir -p "$PACKAGE_DIR"/{docker,source,k8s,helm,docs,scripts,tools}

# Build and export Docker image
log_info "Building and exporting Docker image..."
docker build -f deployment/Dockerfile -t "$REGISTRY:$IMAGE_TAG" .
docker save "$REGISTRY:$IMAGE_TAG" | gzip > "$PACKAGE_DIR/docker/blacklist-image.tar.gz"
docker inspect "$REGISTRY:$IMAGE_TAG" > "$PACKAGE_DIR/docker/image-info.json"

# Package source code
log_info "Packaging source code..."
tar --exclude-vcs --exclude='*.pyc' --exclude='__pycache__' --exclude='*.log' \
    --exclude='instance/*.db' --exclude='data/*' --exclude='logs/*' --exclude='.env' \
    --exclude='node_modules' --exclude='.git' --exclude='/tmp' \
    -czf "$PACKAGE_DIR/source/blacklist-source.tar.gz" \
    --transform 's,^,blacklist/,' * .[^.]* 2>/dev/null || true

# Copy K8s and Helm files
log_info "Copying Kubernetes and Helm files..."
[ -d "k8s" ] && cp -r k8s/* "$PACKAGE_DIR/k8s/" || true
[ -d "helm" ] && cp -r helm/* "$PACKAGE_DIR/helm/" || true
[ -d "charts" ] && cp -r charts/* "$PACKAGE_DIR/helm/" || true

# Package Helm chart
if command -v helm &> /dev/null && [ -d "helm/blacklist" ]; then
    cd helm && helm package blacklist -d "../$PACKAGE_DIR/helm/" && cd ..
fi

# Create deployment scripts
log_info "Creating deployment scripts..."

# Quick deployment script
cat > "$PACKAGE_DIR/scripts/quick-deploy.sh" << 'EOF'
#!/bin/bash

# Quick Deployment Script - Blacklist Management System

set -e

echo "=========================================="
echo "Blacklist - Quick Deployment"
echo "=========================================="

# Load Docker image
echo "Loading Docker image..."
docker load < docker/blacklist-image.tar.gz

echo "Select deployment method:"
echo "1) Docker Compose (Single server)"
echo "2) Kubernetes (Production)"
echo "3) Local Docker only"

read -p "Choice (1-3): " choice

case $choice in
    1)
        echo "Deploying with Docker Compose..."
        tar -xzf source/blacklist-source.tar.gz
        cd blacklist
        cp .env.example .env
        echo "Configure .env file before starting!"
        docker-compose -f deployment/docker-compose.yml up -d
        echo "Access: http://localhost:8541"
        ;;
    2)
        echo "Deploying to Kubernetes..."
        kubectl create namespace blacklist --dry-run=client -o yaml | kubectl apply -f -
        kubectl apply -k k8s/
        kubectl rollout status deployment/blacklist -n blacklist --timeout=300s
        echo "Access: http://localhost:32542"
        ;;
    3)
        echo "Starting local Docker container..."
        docker run -d --name blacklist -p 8541:8541 registry.jclee.me/jclee94/blacklist:latest
        echo "Access: http://localhost:8541"
        ;;
esac

echo "Deployment completed!"
EOF

# Production deployment script
cat > "$PACKAGE_DIR/scripts/production-deploy.sh" << 'EOF'
#!/bin/bash

# Production Deployment Script

NAMESPACE="blacklist"
REPLICAS=3

echo "=========================================="
echo "Production Deployment"
echo "=========================================="

# Load image
docker load < docker/blacklist-image.tar.gz

# Deploy to Kubernetes with production settings
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create production-specific configs
cat > /tmp/production-kustomization.yaml << EOL
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: $NAMESPACE

resources:
  - ../k8s

patchesStrategicMerge:
  - production-patch.yaml
EOL

cat > /tmp/production-patch.yaml << EOL
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blacklist
spec:
  replicas: $REPLICAS
  template:
    spec:
      containers:
      - name: blacklist
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
EOL

# Apply production configuration
kubectl apply -k /tmp/

# Wait for deployment
kubectl rollout status deployment/blacklist -n $NAMESPACE --timeout=600s

echo "Production deployment completed!"
echo "Pods: $(kubectl get pods -n $NAMESPACE --no-headers | wc -l)"
echo "Access via NodePort: http://localhost:32542"

# Cleanup temp files
rm -f /tmp/production-*.yaml
EOF

# Development setup script
cat > "$PACKAGE_DIR/scripts/dev-setup.sh" << 'EOF'
#!/bin/bash

# Development Environment Setup

echo "=========================================="
echo "Development Environment Setup"
echo "=========================================="

# Extract source code
tar -xzf source/blacklist-source.tar.gz
cd blacklist

# Setup Python environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup environment file
cp .env.example .env
echo "Please edit .env file with your configuration"

# Initialize database
python3 init_database.py

echo "Development setup completed!"
echo "To start development server:"
echo "  cd blacklist"
echo "  source venv/bin/activate" 
echo "  python3 main.py --debug"
EOF

# Monitoring script
cat > "$PACKAGE_DIR/scripts/monitor.sh" << 'EOF'
#!/bin/bash

# System Monitoring Script

echo "=========================================="
echo "Blacklist System Status"
echo "=========================================="

# Check Docker containers
echo "Docker Containers:"
docker ps | grep blacklist || echo "No blacklist containers running"

echo ""

# Check Kubernetes if available
if command -v kubectl &> /dev/null; then
    echo "Kubernetes Status:"
    kubectl get pods -n blacklist 2>/dev/null || echo "No Kubernetes deployment found"
    echo ""
fi

# Health check
echo "Application Health:"
for port in 8541 32542; do
    if curl -s "http://localhost:$port/health" &> /dev/null; then
        echo "✓ Health check passed on port $port"
        curl -s "http://localhost:$port/health" | jq . 2>/dev/null || echo "Health endpoint responsive"
    else
        echo "✗ No response on port $port"
    fi
done

echo ""
echo "System Resources:"
echo "Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
EOF

# Backup script
cat > "$PACKAGE_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash

# Backup Script

BACKUP_DIR="/tmp/blacklist-backup-$(date +'%Y%m%d-%H%M%S')"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in $BACKUP_DIR..."

# Backup from Docker container
if docker ps | grep blacklist; then
    echo "Backing up from Docker container..."
    docker exec blacklist tar -czf - /app/instance /app/data 2>/dev/null > "$BACKUP_DIR/container-data.tar.gz" || true
fi

# Backup from Kubernetes
if kubectl get pods -n blacklist &>/dev/null; then
    echo "Backing up from Kubernetes..."
    POD=$(kubectl get pods -n blacklist -o jsonpath='{.items[0].metadata.name}')
    kubectl exec $POD -n blacklist -- tar -czf - /app/instance /app/data 2>/dev/null > "$BACKUP_DIR/k8s-data.tar.gz" || true
fi

echo "Backup completed: $BACKUP_DIR"
tar -czf "${BACKUP_DIR}.tar.gz" -C /tmp "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"
echo "Backup archive: ${BACKUP_DIR}.tar.gz"
EOF

# Make scripts executable
chmod +x "$PACKAGE_DIR/scripts"/*.sh

# Create comprehensive documentation
log_info "Creating documentation..."

cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Blacklist Management System - Offline Package

Complete offline deployment package for air-gapped environments.

## Quick Start

1. **Extract package:**
   ```bash
   tar -xzf blacklist-offline-YYYYMMDD-HHMMSS.tar.gz
   cd blacklist-offline-YYYYMMDD-HHMMSS/
   ```

2. **Quick deployment:**
   ```bash
   ./scripts/quick-deploy.sh
   ```

3. **Access application:**
   - Docker Compose: http://localhost:8541
   - Kubernetes: http://localhost:32542

## Deployment Options

### 1. Docker Compose (Recommended for single server)
```bash
./scripts/quick-deploy.sh  # Select option 1
```

### 2. Kubernetes (Production)
```bash
./scripts/production-deploy.sh
```

### 3. Development Environment
```bash
./scripts/dev-setup.sh
```

## Package Contents

- `docker/` - Docker image and metadata
- `source/` - Complete source code
- `k8s/` - Kubernetes manifests
- `helm/` - Helm charts
- `scripts/` - Deployment and management scripts
- `docs/` - Comprehensive documentation

## Management Scripts

- `scripts/quick-deploy.sh` - Interactive deployment
- `scripts/production-deploy.sh` - Production Kubernetes deployment
- `scripts/dev-setup.sh` - Development environment setup
- `scripts/monitor.sh` - System status monitoring
- `scripts/backup.sh` - Data backup utility

## System Requirements

- **Minimum**: 2GB RAM, 5GB disk, Docker 20.10+
- **Production**: 4GB RAM, 10GB disk, Kubernetes 1.20+

## Configuration

Edit environment variables in `.env` file:
```bash
PORT=8541
SECRET_KEY=your-secret-key
REGTECH_USERNAME=your-username
REGTECH_PASSWORD=your-password
```

## Health Check

```bash
curl http://localhost:8541/health
```

## Monitoring

```bash
./scripts/monitor.sh
```

## Backup

```bash
./scripts/backup.sh
```

## Support

- See `docs/INSTALLATION.md` for detailed instructions
- Check `docs/CLAUDE.md` for comprehensive documentation
- Use `scripts/monitor.sh` for system status

## Troubleshooting

1. **Port conflicts**: Change ports in configuration files
2. **Permission issues**: Run with sudo if needed
3. **Memory issues**: Increase system resources
4. **Network issues**: Check firewall settings

For additional help, see the documentation in the `docs/` directory.
EOF

# Create usage guide
cat > "$PACKAGE_DIR/USAGE.md" << 'EOF'
# 사용법 가이드 (Usage Guide)

## 빠른 시작 (Quick Start)

### 1단계: 패키지 압축 해제
```bash
tar -xzf blacklist-offline-YYYYMMDD-HHMMSS.tar.gz
cd blacklist-offline-YYYYMMDD-HHMMSS/
```

### 2단계: 배포 방법 선택

#### A. 간단한 배포 (Docker Compose)
```bash
./scripts/quick-deploy.sh
# 옵션 1 선택
```

#### B. 프로덕션 배포 (Kubernetes)  
```bash
./scripts/production-deploy.sh
```

#### C. 개발 환경 설정
```bash
./scripts/dev-setup.sh
```

## 주요 스크립트 설명

### 배포 스크립트
- `quick-deploy.sh`: 대화형 배포 스크립트
- `production-deploy.sh`: 프로덕션 Kubernetes 배포
- `dev-setup.sh`: 개발 환경 설정

### 관리 스크립트  
- `monitor.sh`: 시스템 상태 모니터링
- `backup.sh`: 데이터 백업

## 접속 정보

- **Docker Compose**: http://localhost:8541
- **Kubernetes**: http://localhost:32542
- **상태 확인**: http://localhost:8541/health

## 설정 파일

`.env` 파일에서 환경변수 설정:
```
PORT=8541
SECRET_KEY=your-secret-key
REGTECH_USERNAME=사용자명
REGTECH_PASSWORD=비밀번호
```

## 문제 해결

1. **포트 충돌**: 설정 파일에서 포트 변경
2. **권한 문제**: sudo로 실행
3. **메모리 부족**: 시스템 리소스 증가
4. **네트워크 문제**: 방화벽 설정 확인

## 지원

- 상세 문서: `docs/INSTALLATION.md`
- 전체 가이드: `docs/CLAUDE.md`
- 시스템 상태: `./scripts/monitor.sh`
EOF

# Create tools directory with utilities
cat > "$PACKAGE_DIR/tools/check-requirements.sh" << 'EOF'
#!/bin/bash

# System Requirements Checker

echo "=========================================="
echo "System Requirements Check"
echo "=========================================="

# Check Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo "✓ Docker: $DOCKER_VERSION"
else
    echo "✗ Docker: Not installed"
fi

# Check system resources
MEMORY_GB=$(free -g | grep '^Mem:' | awk '{print $2}')
DISK_GB=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')

echo "Memory: ${MEMORY_GB}GB $([ $MEMORY_GB -ge 2 ] && echo '✓' || echo '✗ (minimum 2GB)')"
echo "Disk: ${DISK_GB}GB $([ $DISK_GB -ge 5 ] && echo '✓' || echo '✗ (minimum 5GB)')"

# Check optional components
if command -v kubectl &> /dev/null; then
    echo "✓ kubectl: $(kubectl version --client --short 2>/dev/null | cut -d' ' -f3)"
else
    echo "- kubectl: Not installed (optional for Kubernetes)"
fi

if command -v helm &> /dev/null; then
    echo "✓ helm: $(helm version --short 2>/dev/null)"
else
    echo "- helm: Not installed (optional for Helm deployment)"
fi

echo ""
echo "System ready for deployment!"
EOF

chmod +x "$PACKAGE_DIR/tools/check-requirements.sh"

# Copy important documentation
cp README.md "$PACKAGE_DIR/docs/" 2>/dev/null || true
cp CLAUDE.md "$PACKAGE_DIR/docs/" 2>/dev/null || true

# Create package info
cat > "$PACKAGE_DIR/PACKAGE_INFO.txt" << EOF
Blacklist Management System - Offline Package
=====================================================

Package: $PACKAGE_NAME
Created: $(date)
Version: $(cat VERSION 2>/dev/null || echo "3.0.0")
Git Commit: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

QUICK START:
1. tar -xzf $PACKAGE_NAME.tar.gz
2. cd $PACKAGE_NAME
3. ./scripts/quick-deploy.sh

CONTENTS:
- Docker Image: registry.jclee.me/jclee94/blacklist:latest
- Source Code: Complete repository
- Kubernetes Manifests: Production-ready
- Helm Charts: v1.0+
- Deployment Scripts: Automated deployment
- Management Tools: Monitoring, backup, utilities

DEPLOYMENT OPTIONS:
- Docker Compose: ./scripts/quick-deploy.sh (option 1)
- Kubernetes: ./scripts/production-deploy.sh
- Development: ./scripts/dev-setup.sh

ACCESS:
- Docker Compose: http://localhost:8541
- Kubernetes: http://localhost:32542
- Health Check: curl http://localhost:8541/health

MANAGEMENT:
- Monitor: ./scripts/monitor.sh
- Backup: ./scripts/backup.sh
- Requirements: ./tools/check-requirements.sh

SUPPORT:
- Installation Guide: docs/INSTALLATION.md
- Complete Documentation: docs/CLAUDE.md
- Usage Guide: USAGE.md
EOF

# Create final package
log_info "Creating final package..."
cd /tmp
tar -czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"

# Move to original directory and create checksum
ORIGINAL_DIR="/home/jclee/app/blacklist"
mv "$PACKAGE_NAME.tar.gz" "$ORIGINAL_DIR/"
cd "$ORIGINAL_DIR"

SIZE=$(du -h "$PACKAGE_NAME.tar.gz" | cut -f1)
CHECKSUM=$(sha256sum "$PACKAGE_NAME.tar.gz" | cut -d' ' -f1)

echo "$CHECKSUM  $PACKAGE_NAME.tar.gz" > "$PACKAGE_NAME.tar.gz.sha256"

# Cleanup
rm -rf "/tmp/$PACKAGE_NAME"

echo ""
echo "=========================================="
log_success "Offline Package Created!"
echo "=========================================="
echo ""
echo "Package: $PACKAGE_NAME.tar.gz"
echo "Size: $SIZE"
echo "SHA256: $CHECKSUM"
echo ""
echo "빠른 사용법 (Quick Usage):"
echo "1. tar -xzf $PACKAGE_NAME.tar.gz"
echo "2. cd $PACKAGE_NAME"  
echo "3. ./scripts/quick-deploy.sh"
echo ""
echo "포함된 스크립트 (Included Scripts):"
echo "- scripts/quick-deploy.sh (대화형 배포)"
echo "- scripts/production-deploy.sh (프로덕션 배포)"
echo "- scripts/monitor.sh (시스템 모니터링)"
echo "- scripts/backup.sh (데이터 백업)"
echo "- tools/check-requirements.sh (시스템 요구사항 확인)"
echo ""
echo "문서 (Documentation): docs/, README.md, USAGE.md"
echo "무결성 확인 (Verify): sha256sum -c $PACKAGE_NAME.tar.gz.sha256"
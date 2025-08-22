#!/bin/bash

# GitHub Actions Self-hosted Runner Optimization Script
# Optimizes performance, security, and resource utilization for self-hosted runners

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RUNNER_USER="github-runner"
RUNNER_HOME="/home/$RUNNER_USER"
DOCKER_GROUP="docker"
LOG_FILE="/tmp/runner-optimization.log"
BACKUP_DIR="/opt/runner-backups"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
}

create_runner_user() {
    log "Creating GitHub Actions runner user..."
    
    if ! id "$RUNNER_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$RUNNER_USER"
        usermod -aG "$DOCKER_GROUP" "$RUNNER_USER"
        log "Created user: $RUNNER_USER"
    else
        info "User $RUNNER_USER already exists"
    fi
    
    # Configure sudo access for runner
    cat > /etc/sudoers.d/github-runner << EOF
$RUNNER_USER ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/systemctl, /usr/bin/apt, /usr/bin/snap
$RUNNER_USER ALL=(ALL) NOPASSWD: /bin/mount, /bin/umount
EOF
    
    chmod 440 /etc/sudoers.d/github-runner
    log "Configured sudo access for $RUNNER_USER"
}

optimize_system() {
    log "Optimizing system configuration for CI/CD workloads..."
    
    # Increase file descriptor limits
    cat >> /etc/security/limits.conf << EOF
$RUNNER_USER soft nofile 65536
$RUNNER_USER hard nofile 65536
$RUNNER_USER soft nproc 32768
$RUNNER_USER hard nproc 32768
EOF
    
    # Optimize kernel parameters for container workloads
    cat > /etc/sysctl.d/99-github-runner.conf << EOF
# Network optimizations
net.core.somaxconn = 32768
net.core.netdev_max_backlog = 5000
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216

# File system optimizations
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 256

# Docker optimizations
vm.max_map_count = 262144
vm.overcommit_memory = 1

# Disable swap for better performance
vm.swappiness = 1
EOF
    
    sysctl -p /etc/sysctl.d/99-github-runner.conf
    log "Applied kernel optimizations"
}

optimize_docker() {
    log "Optimizing Docker configuration..."
    
    # Create Docker daemon configuration
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << EOF
{
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "live-restore": true,
    "userland-proxy": false,
    "experimental": true,
    "metrics-addr": "127.0.0.1:9323",
    "default-ulimits": {
        "nofile": {
            "Hard": 64000,
            "Name": "nofile",
            "Soft": 64000
        }
    },
    "default-runtime": "runc",
    "runtimes": {
        "runc": {
            "path": "runc"
        }
    },
    "exec-opts": ["native.cgroupdriver=systemd"],
    "cgroup-parent": "docker.slice",
    "storage-opts": [
        "dm.thinpooldev=/dev/mapper/docker-thinpool",
        "dm.use_deferred_removal=true",
        "dm.use_deferred_deletion=true"
    ],
    "insecure-registries": [],
    "registry-mirrors": [],
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "debug": false
}
EOF
    
    # Restart Docker to apply configuration
    systemctl restart docker
    systemctl enable docker
    
    # Configure Docker cleanup cron job
    cat > /etc/cron.d/docker-cleanup << EOF
# Clean up Docker resources daily at 2 AM
0 2 * * * root /usr/bin/docker system prune -af --volumes --filter "until=24h" >/dev/null 2>&1
EOF
    
    log "Docker optimization completed"
}

setup_caching() {
    log "Setting up advanced caching strategies..."
    
    # Create cache directories
    CACHE_BASE="/opt/github-runner-cache"
    mkdir -p "$CACHE_BASE"/{docker,pip,npm,maven,gradle,ccache}
    chown -R "$RUNNER_USER:$RUNNER_USER" "$CACHE_BASE"
    
    # Docker Buildx cache
    mkdir -p "$CACHE_BASE/docker/buildx"
    chmod 755 "$CACHE_BASE/docker/buildx"
    
    # Python pip cache
    mkdir -p "$CACHE_BASE/pip"
    export PIP_CACHE_DIR="$CACHE_BASE/pip"
    
    # Node.js npm cache
    mkdir -p "$CACHE_BASE/npm"
    npm config set cache "$CACHE_BASE/npm" --global
    
    # Configure cache cleanup
    cat > /etc/cron.d/runner-cache-cleanup << EOF
# Clean old cache files weekly
0 3 * * 0 root find $CACHE_BASE -type f -atime +7 -delete >/dev/null 2>&1
EOF
    
    log "Cache directories configured"
}

install_dependencies() {
    log "Installing and updating CI/CD dependencies..."
    
    # Update package lists
    apt-get update
    
    # Essential packages
    apt-get install -y \
        curl wget git jq \
        build-essential \
        python3 python3-pip python3-venv \
        nodejs npm \
        docker.io docker-compose \
        unzip zip \
        ca-certificates \
        gnupg \
        lsb-release \
        software-properties-common \
        apt-transport-https
    
    # Install Docker Buildx
    DOCKER_BUILDX_VERSION="v0.12.0"
    curl -sL "https://github.com/docker/buildx/releases/download/${DOCKER_BUILDX_VERSION}/buildx-${DOCKER_BUILDX_VERSION}.linux-amd64" \
        -o /usr/local/bin/docker-buildx
    chmod +x /usr/local/bin/docker-buildx
    
    # Install kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    
    # Install Helm
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    
    # Install Trivy for security scanning
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    
    # Install GitHub CLI
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    apt-get update
    apt-get install -y gh
    
    log "Dependencies installed successfully"
}

configure_monitoring() {
    log "Setting up runner monitoring..."
    
    # Install node_exporter for Prometheus monitoring
    NODE_EXPORTER_VERSION="1.6.1"
    wget "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    tar xvfz "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/
    rm -rf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64"*
    
    # Create systemd service for node_exporter
    cat > /etc/systemd/system/node_exporter.service << EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=nobody
Group=nogroup
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable node_exporter
    systemctl start node_exporter
    
    # Create monitoring script
    cat > /usr/local/bin/runner-health-check.sh << 'EOF'
#!/bin/bash

RUNNER_SERVICE="actions.runner.*.service"
DOCKER_SERVICE="docker.service"

check_service() {
    systemctl is-active --quiet $1 && echo "✅ $1 is running" || echo "❌ $1 is not running"
}

echo "🏃 GitHub Runner Health Check - $(date)"
echo "================================="

# Check runner service
check_service "$RUNNER_SERVICE"

# Check Docker service
check_service "$DOCKER_SERVICE"

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2{printf "%.0f", $5}')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️  Disk usage high: ${DISK_USAGE}%"
else
    echo "✅ Disk usage normal: ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEM_USAGE -gt 80 ]; then
    echo "⚠️  Memory usage high: ${MEM_USAGE}%"
else
    echo "✅ Memory usage normal: ${MEM_USAGE}%"
fi

# Check Docker space
DOCKER_SPACE=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | grep -v TYPE | awk '{sum += $3} END {print sum}')
echo "📦 Docker space usage: ${DOCKER_SPACE} MB"

echo "================================="
EOF
    
    chmod +x /usr/local/bin/runner-health-check.sh
    
    # Schedule health checks
    cat > /etc/cron.d/runner-health-check << EOF
# Run health check every 15 minutes
*/15 * * * * root /usr/local/bin/runner-health-check.sh >> /var/log/runner-health.log 2>&1
EOF
    
    log "Monitoring configured"
}

setup_security() {
    log "Configuring security settings..."
    
    # Configure firewall (UFW)
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 9323/tcp  # Docker metrics
    ufw allow 9100/tcp  # Node exporter
    
    # Secure SSH configuration
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    systemctl restart ssh
    
    # Configure fail2ban
    apt-get install -y fail2ban
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF
    
    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Set up unattended upgrades for security updates
    apt-get install -y unattended-upgrades
    cat > /etc/apt/apt.conf.d/50unattended-upgrades << EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
    "\${distro_id}ESMApps:\${distro_codename}-apps-security";
    "\${distro_id}ESM:\${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
    
    log "Security configuration completed"
}

create_backup_system() {
    log "Setting up backup and recovery system..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup script
    cat > /usr/local/bin/runner-backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/runner-backups"
RUNNER_HOME="/home/github-runner"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
tar -czf "$BACKUP_DIR/runner-backup-$DATE.tar.gz" \
    "$RUNNER_HOME" \
    /etc/docker/daemon.json \
    /etc/systemd/system/actions.runner.*.service \
    /opt/github-runner-cache

# Keep only last 7 backups
find "$BACKUP_DIR" -name "runner-backup-*.tar.gz" -type f -mtime +7 -delete

echo "Backup completed: runner-backup-$DATE.tar.gz"
EOF
    
    chmod +x /usr/local/bin/runner-backup.sh
    
    # Schedule daily backups
    cat > /etc/cron.d/runner-backup << EOF
# Daily backup at 1 AM
0 1 * * * root /usr/local/bin/runner-backup.sh >> /var/log/runner-backup.log 2>&1
EOF
    
    log "Backup system configured"
}

performance_tuning() {
    log "Applying performance tuning..."
    
    # CPU governor for performance
    echo 'GOVERNOR="performance"' > /etc/default/cpufrequtils
    
    # Disable unnecessary services
    systemctl disable snapd.service snapd.socket
    systemctl disable bluetooth.service
    systemctl disable cups.service
    
    # Configure tmpfs for temporary build files
    echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=2G 0 0" >> /etc/fstab
    
    # I/O scheduler optimization for SSDs
    echo 'ACTION=="add|change", KERNEL=="sd[a-z]*", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"' > /etc/udev/rules.d/60-schedulers.rules
    
    log "Performance tuning completed"
}

generate_runner_config() {
    log "Generating runner configuration template..."
    
    cat > "$RUNNER_HOME/configure-runner.sh" << 'EOF'
#!/bin/bash

# GitHub Actions Runner Configuration Script
# Run this script as the github-runner user

set -e

REPO_URL="$1"
TOKEN="$2"
RUNNER_NAME="${3:-$(hostname)-runner}"

if [ -z "$REPO_URL" ] || [ -z "$TOKEN" ]; then
    echo "Usage: $0 <repo_url> <token> [runner_name]"
    echo "Example: $0 https://github.com/user/repo ghp_token_here my-runner"
    exit 1
fi

# Download and extract runner
RUNNER_VERSION="2.311.0"
mkdir -p ~/actions-runner && cd ~/actions-runner

curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
    https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# Configure runner
./config.sh --url "$REPO_URL" --token "$TOKEN" --name "$RUNNER_NAME" --work _work --replace

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start

echo "✅ GitHub Actions runner configured and started!"
echo "Runner name: $RUNNER_NAME"
echo "Repository: $REPO_URL"
EOF
    
    chmod +x "$RUNNER_HOME/configure-runner.sh"
    chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME/configure-runner.sh"
    
    log "Runner configuration script created at $RUNNER_HOME/configure-runner.sh"
}

main() {
    log "Starting GitHub Actions self-hosted runner optimization..."
    
    check_root
    create_runner_user
    optimize_system
    optimize_docker
    setup_caching
    install_dependencies
    configure_monitoring
    setup_security
    create_backup_system
    performance_tuning
    generate_runner_config
    
    log "✅ GitHub Actions runner optimization completed successfully!"
    
    cat << EOF

🎉 OPTIMIZATION COMPLETE!
========================

Next steps:
1. Reboot the system to apply all optimizations:
   sudo reboot

2. After reboot, configure the GitHub Actions runner:
   sudo -u $RUNNER_USER $RUNNER_HOME/configure-runner.sh <repo_url> <token> [runner_name]

3. Monitor the runner:
   sudo /usr/local/bin/runner-health-check.sh

Configuration files:
- Runner user: $RUNNER_USER
- Cache directory: /opt/github-runner-cache
- Backup directory: $BACKUP_DIR
- Log file: $LOG_FILE

Monitoring:
- Node exporter: http://localhost:9100/metrics
- Docker metrics: http://localhost:9323/metrics
- Health checks: /var/log/runner-health.log

For more information, check the logs at: $LOG_FILE
EOF
}

# Execute main function
main "$@"
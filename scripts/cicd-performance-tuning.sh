#!/bin/bash
# CI/CD 성능 튜닝 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== CI/CD 성능 최적화 설정 ===${NC}"
echo ""

# 1. Docker 빌드킷 설정
setup_docker_buildkit() {
    echo -e "${YELLOW}1. Docker BuildKit 최적화${NC}"
    
    # Docker 데몬 설정
    DOCKER_CONFIG="/etc/docker/daemon.json"
    
    if [ -w "$DOCKER_CONFIG" ]; then
        echo -e "  Docker 데몬 설정 업데이트 중..."
        
        # 기존 설정 백업
        sudo cp "$DOCKER_CONFIG" "${DOCKER_CONFIG}.backup" 2>/dev/null || true
        
        # BuildKit 설정 추가
        sudo tee "$DOCKER_CONFIG" > /dev/null <<EOF
{
  "features": {
    "buildkit": true
  },
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"
    }
  },
  "registry-mirrors": [],
  "insecure-registries": ["registry.jclee.me"],
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5,
  "log-level": "warn"
}
EOF
        
        # Docker 재시작
        echo -e "  Docker 데몬 재시작..."
        sudo systemctl restart docker
        echo -e "  ${GREEN}✅ Docker BuildKit 활성화됨${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Docker 설정 권한 없음 (수동 설정 필요)${NC}"
    fi
    
    # 사용자 BuildKit 설정
    mkdir -p ~/.docker
    cat > ~/.docker/config.json <<EOF
{
  "experimental": "enabled",
  "aliases": {
    "builder": "buildx"
  }
}
EOF
    
    # BuildKit 환경 변수 설정
    cat >> ~/.bashrc <<'EOF'

# Docker BuildKit 성능 최적화
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_CLI_EXPERIMENTAL=enabled
EOF
    
    echo -e "  ${GREEN}✅ BuildKit 환경 변수 설정됨${NC}"
}

# 2. Python 의존성 캐싱 최적화
optimize_python_cache() {
    echo -e "\n${YELLOW}2. Python 캐싱 최적화${NC}"
    
    # pip 캐시 디렉토리 생성
    mkdir -p ~/.cache/pip
    
    # pip 설정 최적화
    mkdir -p ~/.config/pip
    cat > ~/.config/pip/pip.conf <<EOF
[global]
cache-dir = ~/.cache/pip
download-cache = ~/.cache/pip
wheel-dir = ~/.cache/pip/wheels

[install]
use-wheel = true
find-links = file://~/.cache/pip/wheels

[wheel]
wheel-dir = ~/.cache/pip/wheels
EOF
    
    echo -e "  ${GREEN}✅ pip 캐시 설정 완료${NC}"
    
    # 사전 빌드된 wheel 생성
    if [ -f "requirements.txt" ]; then
        echo -e "  의존성 wheel 사전 빌드 중..."
        pip3 wheel -r requirements.txt -w ~/.cache/pip/wheels/ || true
        echo -e "  ${GREEN}✅ Wheel 캐시 생성됨${NC}"
    fi
}

# 3. Git 최적화
optimize_git() {
    echo -e "\n${YELLOW}3. Git 성능 최적화${NC}"
    
    # Git 설정
    git config --global core.preloadindex true
    git config --global core.fscache true
    git config --global gc.auto 256
    git config --global feature.manyFiles true
    
    # Shallow clone 설정
    git config --global fetch.prune true
    git config --global fetch.pruneTags true
    
    echo -e "  ${GREEN}✅ Git 설정 최적화됨${NC}"
    
    # Git LFS 설정 (있는 경우)
    if command -v git-lfs &> /dev/null; then
        git lfs install --skip-smudge
        echo -e "  ${GREEN}✅ Git LFS 최적화됨${NC}"
    fi
}

# 4. 시스템 리소스 최적화
optimize_system_resources() {
    echo -e "\n${YELLOW}4. 시스템 리소스 최적화${NC}"
    
    # 파일 디스크립터 제한 증가
    if [ -w "/etc/security/limits.conf" ]; then
        echo -e "  파일 디스크립터 제한 증가..."
        echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
        echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
        echo -e "  ${GREEN}✅ 파일 디스크립터 제한 증가됨${NC}"
    fi
    
    # 메모리 스왑 설정
    if [ -w "/proc/sys/vm/swappiness" ]; then
        echo 10 | sudo tee /proc/sys/vm/swappiness
        echo -e "  ${GREEN}✅ 스왑 사용 최적화됨${NC}"
    fi
}

# 5. CI/CD 전용 디렉토리 설정
setup_cicd_directories() {
    echo -e "\n${YELLOW}5. CI/CD 전용 디렉토리 설정${NC}"
    
    # 캐시 디렉토리 생성
    CACHE_DIRS=(
        "/tmp/blacklist-cache"
        "/tmp/blacklist-build"
        "/tmp/blacklist-test"
    )
    
    for dir in "${CACHE_DIRS[@]}"; do
        mkdir -p "$dir"
        echo -e "  ✅ $dir 생성됨"
    done
    
    # tmpfs 마운트 (메모리 기반 빠른 저장소)
    if command -v mount &> /dev/null && [ "$EUID" -eq 0 ]; then
        mount -t tmpfs -o size=2G tmpfs /tmp/blacklist-build
        echo -e "  ${GREEN}✅ 빌드 디렉토리를 메모리에 마운트${NC}"
    fi
}

# 6. 병렬 처리 설정
setup_parallel_processing() {
    echo -e "\n${YELLOW}6. 병렬 처리 최적화${NC}"
    
    # CPU 코어 수 확인
    CPU_CORES=$(nproc)
    OPTIMAL_WORKERS=$((CPU_CORES - 1))
    
    # 환경 변수 설정
    cat >> ~/.bashrc <<EOF

# CI/CD 병렬 처리 설정
export MAKEFLAGS="-j${OPTIMAL_WORKERS}"
export PYTEST_WORKERS="${OPTIMAL_WORKERS}"
export DOCKER_BUILD_PARALLEL="${OPTIMAL_WORKERS}"
EOF
    
    echo -e "  CPU 코어: ${CPU_CORES}"
    echo -e "  최적 워커 수: ${OPTIMAL_WORKERS}"
    echo -e "  ${GREEN}✅ 병렬 처리 설정됨${NC}"
}

# 7. 네트워크 최적화
optimize_network() {
    echo -e "\n${YELLOW}7. 네트워크 최적화${NC}"
    
    # DNS 캐싱
    if command -v systemd-resolve &> /dev/null; then
        sudo systemd-resolve --set-dns=1.1.1.1 --interface=docker0
        echo -e "  ${GREEN}✅ Docker DNS 최적화됨${NC}"
    fi
    
    # TCP 설정 최적화
    if [ -w "/etc/sysctl.conf" ]; then
        echo -e "  TCP 설정 최적화..."
        cat | sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# CI/CD 네트워크 최적화
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_tw_reuse = 1
EOF
        sudo sysctl -p
        echo -e "  ${GREEN}✅ 네트워크 설정 최적화됨${NC}"
    fi
}

# 8. 모니터링 설정
setup_monitoring() {
    echo -e "\n${YELLOW}8. 성능 모니터링 설정${NC}"
    
    # 모니터링 스크립트 생성
    cat > /tmp/cicd-performance-monitor.sh <<'EOF'
#!/bin/bash
# CI/CD 성능 모니터링

while true; do
    # CPU 사용률
    CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    
    # 메모리 사용률
    MEM=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
    
    # Docker 상태
    CONTAINERS=$(docker ps -q | wc -l)
    
    # 로그
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] CPU: ${CPU}%, MEM: ${MEM}%, Containers: ${CONTAINERS}"
    
    # 임계값 확인
    if (( $(echo "$CPU > 80" | bc -l) )); then
        echo "⚠️  높은 CPU 사용률 감지: ${CPU}%"
    fi
    
    sleep 60
done
EOF
    chmod +x /tmp/cicd-performance-monitor.sh
    
    echo -e "  ${GREEN}✅ 모니터링 스크립트 생성됨${NC}"
}

# 9. 최적화 검증
verify_optimization() {
    echo -e "\n${YELLOW}9. 최적화 검증${NC}"
    
    # Docker BuildKit 확인
    if docker buildx version &> /dev/null; then
        echo -e "  ✅ Docker BuildKit 활성화됨"
    else
        echo -e "  ❌ Docker BuildKit 비활성화"
    fi
    
    # Python 캐시 확인
    if [ -d ~/.cache/pip/wheels ]; then
        WHEEL_COUNT=$(ls ~/.cache/pip/wheels/*.whl 2>/dev/null | wc -l)
        echo -e "  ✅ Python wheel 캐시: ${WHEEL_COUNT}개"
    else
        echo -e "  ❌ Python wheel 캐시 없음"
    fi
    
    # Git 설정 확인
    if git config --get core.preloadindex &> /dev/null; then
        echo -e "  ✅ Git 최적화 설정됨"
    else
        echo -e "  ❌ Git 최적화 미설정"
    fi
}

# 메인 실행
main() {
    echo -e "${BLUE}CI/CD 성능 최적화를 시작합니다...${NC}"
    echo ""
    
    # 각 최적화 단계 실행
    setup_docker_buildkit
    optimize_python_cache
    optimize_git
    optimize_system_resources
    setup_cicd_directories
    setup_parallel_processing
    optimize_network
    setup_monitoring
    verify_optimization
    
    echo ""
    echo -e "${GREEN}✅ CI/CD 성능 최적화가 완료되었습니다!${NC}"
    echo ""
    echo -e "${BLUE}다음 단계:${NC}"
    echo -e "1. 시스템 재부팅 또는 source ~/.bashrc 실행"
    echo -e "2. Docker 서비스 재시작: sudo systemctl restart docker"
    echo -e "3. CI/CD 파이프라인 실행하여 성능 확인"
    echo -e "4. 모니터링 시작: /tmp/cicd-performance-monitor.sh"
}

# 실행
main "$@"
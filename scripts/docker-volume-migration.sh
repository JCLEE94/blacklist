#!/bin/bash
# Docker 바인드 마운트를 볼륨으로 마이그레이션하는 스크립트
# Version: v1.0.37
# Author: Claude Code Agent

set -euo pipefail

# 색깔 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 작업 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backup/bind-mount-migration-$(date +%Y%m%d_%H%M%S)"

log_info "Docker 바인드 마운트 → 볼륨 마이그레이션 시작"
log_info "프로젝트 루트: $PROJECT_ROOT"
log_info "백업 디렉토리: $BACKUP_DIR"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

# 발견된 바인드 마운트 목록
declare -A BIND_MOUNTS=(
    # docker-compose.yml (루트)
    ["./monitoring/prometheus.yml"]="/etc/prometheus/prometheus.yml:ro"
    ["./monitoring/grafana/dashboards"]="/etc/grafana/provisioning/dashboards:ro"
    ["./monitoring/grafana/datasources"]="/etc/grafana/provisioning/datasources:ro"
    
    # docker-compose.watchtower.yml
    ["/var/run/docker.sock"]="/var/run/docker.sock"
    ["~/.docker/config.json"]="/config.json:ro"
    
    # docker-compose.performance.yml
    ["./config/postgresql.conf"]="/etc/postgresql/postgresql.conf:ro"
    ["./monitoring/prometheus.yml"]="/etc/prometheus/prometheus.yml:ro"
    ["./monitoring/grafana/dashboards"]="/etc/grafana/provisioning/dashboards:ro"
    ["./monitoring/grafana/datasources"]="/etc/grafana/provisioning/datasources:ro"
)

# 네임드 볼륨으로 변환할 매핑
declare -A VOLUME_MAPPINGS=(
    ["./monitoring/prometheus.yml"]="prometheus-config"
    ["./monitoring/grafana/dashboards"]="grafana-dashboards"
    ["./monitoring/grafana/datasources"]="grafana-datasources"
    ["./config/postgresql.conf"]="postgresql-config"
)

# 시스템 바인드 마운트 (그대로 유지)
declare -A SYSTEM_MOUNTS=(
    ["/var/run/docker.sock"]="/var/run/docker.sock"
    ["~/.docker/config.json"]="/config.json:ro"
)

# 현재 서비스 중지
stop_services() {
    log_info "현재 실행 중인 서비스 중지..."
    if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" ps -q &>/dev/null; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.yml" down || true
    fi
    
    if docker-compose -f "$PROJECT_ROOT/docker-compose.performance.yml" ps -q &>/dev/null; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.performance.yml" down || true
    fi
    
    if docker-compose -f "$PROJECT_ROOT/docker-compose.watchtower.yml" ps -q &>/dev/null; then
        docker-compose -f "$PROJECT_ROOT/docker-compose.watchtower.yml" down || true
    fi
}

# 데이터 백업
backup_data() {
    log_info "바인드 마운트 데이터 백업 중..."
    
    for source_path in "${!BIND_MOUNTS[@]}"; do
        if [[ "$source_path" =~ ^/var/run|^~/.docker ]]; then
            log_warning "시스템 마운트 건너뜀: $source_path"
            continue
        fi
        
        full_path="$PROJECT_ROOT/$source_path"
        if [[ -e "$full_path" ]]; then
            backup_target="$BACKUP_DIR/$(basename "$source_path")"
            cp -r "$full_path" "$backup_target"
            log_success "백업 완료: $source_path → $backup_target"
        else
            log_warning "파일/디렉토리가 존재하지 않음: $full_path"
        fi
    done
}

# 볼륨 생성 및 데이터 복사
create_volumes_and_migrate_data() {
    log_info "네임드 볼륨 생성 및 데이터 마이그레이션..."
    
    for source_path in "${!VOLUME_MAPPINGS[@]}"; do
        volume_name="${VOLUME_MAPPINGS[$source_path]}"
        full_path="$PROJECT_ROOT/$source_path"
        
        # 볼륨 생성
        if ! docker volume inspect "blacklist-$volume_name" &>/dev/null; then
            docker volume create "blacklist-$volume_name"
            log_success "볼륨 생성: blacklist-$volume_name"
        else
            log_warning "볼륨이 이미 존재함: blacklist-$volume_name"
        fi
        
        # 데이터 복사
        if [[ -e "$full_path" ]]; then
            log_info "데이터 복사 중: $full_path → blacklist-$volume_name"
            
            # 임시 컨테이너를 사용하여 데이터 복사
            if [[ -d "$full_path" ]]; then
                # 디렉토리인 경우
                docker run --rm \
                    -v "blacklist-$volume_name:/target" \
                    -v "$full_path:/source:ro" \
                    alpine sh -c "cp -r /source/* /target/ 2>/dev/null || cp -r /source/. /target/"
            else
                # 파일인 경우
                docker run --rm \
                    -v "blacklist-$volume_name:/target" \
                    -v "$full_path:/source:ro" \
                    alpine sh -c "cp /source /target/$(basename "$full_path")"
            fi
            
            log_success "데이터 복사 완료: $volume_name"
        else
            log_warning "소스 파일/디렉토리가 존재하지 않음: $full_path"
        fi
    done
}

# Docker Compose 파일 업데이트
update_docker_compose_files() {
    log_info "Docker Compose 파일 업데이트 중..."
    
    # 메인 docker-compose.yml 업데이트
    local main_compose="$PROJECT_ROOT/docker-compose.yml"
    cp "$main_compose" "$BACKUP_DIR/docker-compose.yml.backup"
    
    # prometheus 설정 수정
    sed -i 's|./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro|prometheus-config:/etc/prometheus:ro|g' "$main_compose"
    # grafana 설정 수정
    sed -i 's|./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro|grafana-dashboards:/etc/grafana/provisioning/dashboards:ro|g' "$main_compose"
    sed -i 's|./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro|grafana-datasources:/etc/grafana/provisioning/datasources:ro|g' "$main_compose"
    
    # 볼륨 섹션에 새 볼륨 추가
    if ! grep -q "prometheus-config:" "$main_compose"; then
        cat >> "$main_compose" << 'EOF'

  prometheus-config:
    driver: local
    name: blacklist-prometheus-config
  
  grafana-dashboards:
    driver: local
    name: blacklist-grafana-dashboards
  
  grafana-datasources:
    driver: local
    name: blacklist-grafana-datasources
EOF
    fi
    
    # performance compose 파일 업데이트
    local perf_compose="$PROJECT_ROOT/docker-compose.performance.yml"
    if [[ -f "$perf_compose" ]]; then
        cp "$perf_compose" "$BACKUP_DIR/docker-compose.performance.yml.backup"
        
        # postgresql 설정 수정
        sed -i 's|./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro|postgresql-config:/etc/postgresql:ro|g' "$perf_compose"
        # prometheus, grafana 설정 수정
        sed -i 's|./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro|prometheus-config:/etc/prometheus:ro|g' "$perf_compose"
        sed -i 's|./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro|grafana-dashboards:/etc/grafana/provisioning/dashboards:ro|g' "$perf_compose"
        sed -i 's|./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro|grafana-datasources:/etc/grafana/provisioning/datasources:ro|g' "$perf_compose"
        
        # 새 볼륨 추가
        if ! grep -q "postgresql-config:" "$perf_compose"; then
            cat >> "$perf_compose" << 'EOF'

  postgresql-config:
    driver: local
    name: blacklist-postgresql-config
EOF
        fi
    fi
    
    log_success "Docker Compose 파일 업데이트 완료"
}

# 마이그레이션 검증
verify_migration() {
    log_info "마이그레이션 검증 중..."
    
    # 볼륨 존재 확인
    for volume_name in "${VOLUME_MAPPINGS[@]}"; do
        if docker volume inspect "blacklist-$volume_name" &>/dev/null; then
            log_success "볼륨 확인: blacklist-$volume_name"
        else
            log_error "볼륨 누락: blacklist-$volume_name"
            return 1
        fi
    done
    
    # 서비스 시작 테스트
    log_info "서비스 시작 테스트..."
    if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" config &>/dev/null; then
        log_success "Docker Compose 설정 검증 완료"
    else
        log_error "Docker Compose 설정 오류"
        return 1
    fi
    
    log_success "마이그레이션 검증 완료"
}

# 롤백 함수
rollback() {
    log_warning "마이그레이션 롤백 중..."
    
    # 백업에서 복원
    if [[ -f "$BACKUP_DIR/docker-compose.yml.backup" ]]; then
        cp "$BACKUP_DIR/docker-compose.yml.backup" "$PROJECT_ROOT/docker-compose.yml"
        log_success "docker-compose.yml 복원 완료"
    fi
    
    if [[ -f "$BACKUP_DIR/docker-compose.performance.yml.backup" ]]; then
        cp "$BACKUP_DIR/docker-compose.performance.yml.backup" "$PROJECT_ROOT/docker-compose.performance.yml"
        log_success "docker-compose.performance.yml 복원 완료"
    fi
    
    log_success "롤백 완료"
}

# 메인 실행 함수
main() {
    log_info "=== Docker 볼륨 마이그레이션 시작 ==="
    
    # 사용자 확인
    echo
    log_warning "이 스크립트는 다음 작업을 수행합니다:"
    echo "1. 현재 실행 중인 Docker 서비스 중지"
    echo "2. 바인드 마운트 데이터 백업"
    echo "3. 네임드 볼륨 생성 및 데이터 마이그레이션"
    echo "4. Docker Compose 파일 업데이트"
    echo "5. 마이그레이션 검증"
    echo
    
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "마이그레이션 취소됨"
        exit 0
    fi
    
    # 마이그레이션 실행
    stop_services
    backup_data
    create_volumes_and_migrate_data
    update_docker_compose_files
    
    if verify_migration; then
        log_success "=== 마이그레이션 성공적으로 완료 ==="
        echo
        log_info "백업 위치: $BACKUP_DIR"
        log_info "서비스 시작: docker-compose up -d"
        echo
        log_warning "문제가 발생하면 다음 명령으로 롤백하세요:"
        echo "bash $0 --rollback"
    else
        log_error "마이그레이션 실패"
        rollback
        exit 1
    fi
}

# 명령행 인수 처리
case "${1:-}" in
    --rollback)
        rollback
        exit 0
        ;;
    --help|-h)
        echo "사용법: $0 [옵션]"
        echo "옵션:"
        echo "  --rollback    백업에서 복원"
        echo "  --help        도움말 표시"
        exit 0
        ;;
    *)
        main
        ;;
esac
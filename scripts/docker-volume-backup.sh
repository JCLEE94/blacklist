#!/bin/bash
# Docker 볼륨 백업 스크립트
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

# 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-$PROJECT_ROOT/backup/volumes}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"

# 백업할 볼륨 목록
VOLUMES=(
    "blacklist-data"
    "blacklist-logs"
    "blacklist-redis-data"
    "blacklist-postgresql-data"
    "blacklist-prometheus-data"
    "blacklist-grafana-data"
    "blacklist-prometheus-config"
    "blacklist-grafana-dashboards"
    "blacklist-grafana-datasources"
    "blacklist-postgresql-config"
)

# 보존 정책 (일 단위)
RETENTION_DAYS=${RETENTION_DAYS:-7}

# 백업 함수
backup_volume() {
    local volume_name="$1"
    local backup_path="$BACKUP_DIR/$volume_name.tar.gz"
    
    log_info "볼륨 백업 중: $volume_name"
    
    # 볼륨 존재 확인
    if ! docker volume inspect "$volume_name" &>/dev/null; then
        log_warning "볼륨이 존재하지 않음: $volume_name"
        return 0
    fi
    
    # 백업 실행
    docker run --rm \
        -v "$volume_name:/source:ro" \
        -v "$BACKUP_DIR:/backup" \
        alpine:latest \
        tar -czf "/backup/$volume_name.tar.gz" -C /source .
    
    if [[ -f "$backup_path" ]]; then
        local size=$(du -h "$backup_path" | cut -f1)
        log_success "백업 완료: $volume_name ($size)"
    else
        log_error "백업 실패: $volume_name"
        return 1
    fi
}

# 복원 함수
restore_volume() {
    local volume_name="$1"
    local backup_file="$2"
    
    log_info "볼륨 복원 중: $volume_name"
    
    # 백업 파일 확인
    if [[ ! -f "$backup_file" ]]; then
        log_error "백업 파일이 존재하지 않음: $backup_file"
        return 1
    fi
    
    # 볼륨 생성 (존재하지 않는 경우)
    if ! docker volume inspect "$volume_name" &>/dev/null; then
        docker volume create "$volume_name"
        log_info "볼륨 생성: $volume_name"
    fi
    
    # 복원 실행
    docker run --rm \
        -v "$volume_name:/target" \
        -v "$(dirname "$backup_file"):/backup:ro" \
        alpine:latest \
        sh -c "cd /target && tar -xzf /backup/$(basename "$backup_file")"
    
    log_success "복원 완료: $volume_name"
}

# 전체 백업
backup_all() {
    log_info "=== Docker 볼륨 전체 백업 시작 ==="
    log_info "백업 디렉토리: $BACKUP_DIR"
    
    # 백업 디렉토리 생성
    mkdir -p "$BACKUP_DIR"
    
    # 메타데이터 파일 생성
    cat > "$BACKUP_DIR/backup_info.txt" << EOF
백업 날짜: $(date)
백업 시스템: $(hostname)
프로젝트: Blacklist Management System
백업 타입: Docker Volumes
백업 버전: v1.0.37

볼륨 목록:
EOF
    
    local success_count=0
    local total_count=${#VOLUMES[@]}
    
    for volume in "${VOLUMES[@]}"; do
        if backup_volume "$volume"; then
            echo "✓ $volume" >> "$BACKUP_DIR/backup_info.txt"
            ((success_count++))
        else
            echo "✗ $volume (실패)" >> "$BACKUP_DIR/backup_info.txt"
        fi
    done
    
    # 백업 요약
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo -e "\n백업 요약:" >> "$BACKUP_DIR/backup_info.txt"
    echo "성공: $success_count/$total_count" >> "$BACKUP_DIR/backup_info.txt"
    echo "총 크기: $total_size" >> "$BACKUP_DIR/backup_info.txt"
    
    log_success "=== 백업 완료 ==="
    log_info "성공한 볼륨: $success_count/$total_count"
    log_info "총 백업 크기: $total_size"
    log_info "백업 위치: $BACKUP_DIR"
}

# 백업 목록 조회
list_backups() {
    log_info "=== 백업 목록 ==="
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log_warning "백업 디렉토리가 존재하지 않음: $BACKUP_BASE_DIR"
        return 0
    fi
    
    local count=0
    for backup_dir in "$BACKUP_BASE_DIR"/*; do
        if [[ -d "$backup_dir" && -f "$backup_dir/backup_info.txt" ]]; then
            local backup_name=$(basename "$backup_dir")
            local backup_size=$(du -sh "$backup_dir" | cut -f1)
            local backup_date=$(date -d "${backup_name:0:8} ${backup_name:9:2}:${backup_name:11:2}:${backup_name:13:2}" 2>/dev/null || echo "알 수 없음")
            
            echo "[$count] $backup_name ($backup_size) - $backup_date"
            ((count++))
        fi
    done
    
    if [[ $count -eq 0 ]]; then
        log_warning "백업이 존재하지 않음"
    else
        log_info "총 $count개의 백업 발견"
    fi
}

# 백업 정리 (보존 정책 적용)
cleanup_old_backups() {
    log_info "오래된 백업 정리 중... (보존 기간: ${RETENTION_DAYS}일)"
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log_warning "백업 디렉토리가 존재하지 않음: $BACKUP_BASE_DIR"
        return 0
    fi
    
    local deleted_count=0
    local cutoff_date=$(date -d "${RETENTION_DAYS} days ago" +%Y%m%d)
    
    for backup_dir in "$BACKUP_BASE_DIR"/*; do
        if [[ -d "$backup_dir" ]]; then
            local backup_name=$(basename "$backup_dir")
            local backup_date="${backup_name:0:8}"
            
            if [[ "$backup_date" < "$cutoff_date" ]]; then
                log_info "삭제 중: $backup_name"
                rm -rf "$backup_dir"
                ((deleted_count++))
            fi
        fi
    done
    
    log_success "정리 완료: ${deleted_count}개 백업 삭제"
}

# 개별 볼륨 복원
restore_single() {
    local volume_name="$1"
    local backup_timestamp="$2"
    
    local backup_file="$BACKUP_BASE_DIR/$backup_timestamp/$volume_name.tar.gz"
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "백업 파일을 찾을 수 없음: $backup_file"
        return 1
    fi
    
    log_warning "볼륨 복원은 기존 데이터를 완전히 덮어씁니다!"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "복원 취소됨"
        return 0
    fi
    
    restore_volume "$volume_name" "$backup_file"
}

# 전체 복원
restore_all() {
    local backup_timestamp="$1"
    local backup_dir="$BACKUP_BASE_DIR/$backup_timestamp"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "백업 디렉토리를 찾을 수 없음: $backup_dir"
        return 1
    fi
    
    log_warning "전체 복원은 모든 볼륨 데이터를 덮어씁니다!"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "복원 취소됨"
        return 0
    fi
    
    log_info "=== 전체 복원 시작 ==="
    
    local success_count=0
    local total_count=0
    
    for backup_file in "$backup_dir"/*.tar.gz; do
        if [[ -f "$backup_file" ]]; then
            local volume_name=$(basename "$backup_file" .tar.gz)
            ((total_count++))
            
            if restore_volume "$volume_name" "$backup_file"; then
                ((success_count++))
            fi
        fi
    done
    
    log_success "=== 복원 완료 ==="
    log_info "성공한 볼륨: $success_count/$total_count"
}

# 도움말
show_help() {
    cat << EOF
Docker 볼륨 백업 관리 도구

사용법:
  $0 backup                     # 전체 볼륨 백업
  $0 list                       # 백업 목록 조회
  $0 cleanup                    # 오래된 백업 정리
  $0 restore <timestamp>        # 전체 복원
  $0 restore <volume> <timestamp>  # 개별 볼륨 복원
  $0 help                       # 도움말

환경 변수:
  BACKUP_BASE_DIR               # 백업 기본 디렉토리 (기본값: ./backup/volumes)
  RETENTION_DAYS                # 백업 보존 기간 (기본값: 7일)

예시:
  $0 backup                     # 백업 생성
  $0 list                       # 백업 목록 확인
  $0 restore 20241222_143000    # 특정 시점으로 전체 복원
  $0 restore blacklist-data 20241222_143000  # 특정 볼륨만 복원
  $0 cleanup                    # 7일 이전 백업 삭제

EOF
}

# 메인 함수
main() {
    case "${1:-}" in
        backup)
            backup_all
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        restore)
            if [[ $# -eq 2 ]]; then
                restore_all "$2"
            elif [[ $# -eq 3 ]]; then
                restore_single "$2" "$3"
            else
                log_error "잘못된 인수입니다. 도움말: $0 help"
                exit 1
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "알 수 없는 명령입니다: ${1:-}"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
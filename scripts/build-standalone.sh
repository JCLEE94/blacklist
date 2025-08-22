#!/bin/bash
# Complete Standalone Docker Build Script
# Builds all standalone images with zero dependencies
# Version: v1.0.37

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
VERSION="${VERSION:-v1.0.37}"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Function to show usage
show_usage() {
    cat << EOF
Blacklist Management System - Standalone Docker Build Script

USAGE:
    $0 [OPTIONS] [IMAGES...]

OPTIONS:
    --registry URL      Docker registry URL (default: registry.jclee.me)
    --version VERSION   Version tag (default: v1.0.37)
    --push             Push images after building
    --no-cache         Build without using cache
    --parallel         Build images in parallel
    --help, -h         Show this help message

IMAGES:
    app                Build main application image
    postgresql         Build PostgreSQL database image
    redis              Build Redis cache image
    all                Build all images (default)

EXAMPLES:
    $0                          # Build all images
    $0 app                      # Build only application image
    $0 --push                   # Build and push all images
    $0 --registry custom.io app # Build app with custom registry
    $0 --no-cache all          # Build all without cache
    $0 --parallel all          # Build all in parallel

ENVIRONMENT VARIABLES:
    REGISTRY_URL               Docker registry URL
    VERSION                    Image version tag
    DOCKER_BUILDKIT           Enable BuildKit (recommended: 1)

EOF
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check if BuildKit is available
    if [ "${DOCKER_BUILDKIT:-1}" = "1" ]; then
        if docker buildx version &> /dev/null; then
            log_info "Using Docker BuildKit for enhanced builds"
            export DOCKER_BUILDKIT=1
        else
            log_warning "BuildKit not available, using standard docker build"
        fi
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required files exist
    required_files=(
        "$PROJECT_ROOT/Dockerfile.standalone"
        "$PROJECT_ROOT/build/docker/postgresql/Dockerfile.standalone"
        "$PROJECT_ROOT/build/docker/redis/Dockerfile.standalone"
        "$PROJECT_ROOT/config/requirements.txt"
        "$PROJECT_ROOT/version.txt"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    
    # Check if git is available for VCS ref
    if command -v git &> /dev/null && git rev-parse --git-dir &> /dev/null; then
        VCS_REF=$(git rev-parse --short HEAD)
        log_info "Git repository detected, using VCS ref: $VCS_REF"
    else
        VCS_REF="unknown"
        log_warning "Git not available, using VCS ref: $VCS_REF"
    fi
    
    log_success "Prerequisites check completed"
}

# Function to build main application image
build_app_image() {
    local use_cache="$1"
    local image_name="$REGISTRY_URL/blacklist:standalone"
    local latest_tag="$REGISTRY_URL/blacklist:standalone-latest"
    
    log_info "Building main application image..."
    log_info "Image: $image_name"
    log_info "Context: $PROJECT_ROOT"
    log_info "Dockerfile: Dockerfile.standalone"
    
    local build_args=(
        "--build-arg" "VERSION=$VERSION"
        "--build-arg" "BUILD_DATE=$BUILD_DATE"
        "--build-arg" "VCS_REF=$VCS_REF"
        "--tag" "$image_name"
        "--tag" "$latest_tag"
        "--file" "$PROJECT_ROOT/Dockerfile.standalone"
    )
    
    if [ "$use_cache" = "false" ]; then
        build_args+=("--no-cache")
    fi
    
    build_args+=("$PROJECT_ROOT")
    
    if ! docker build "${build_args[@]}"; then
        log_error "Failed to build main application image"
        return 1
    fi
    
    log_success "Main application image built successfully"
    
    # Show image size
    local size=$(docker images --format "table {{.Size}}" "$image_name" | tail -n 1)
    log_info "Image size: $size"
}

# Function to build PostgreSQL image
build_postgresql_image() {
    local use_cache="$1"
    local image_name="$REGISTRY_URL/blacklist-postgresql:standalone"
    local latest_tag="$REGISTRY_URL/blacklist-postgresql:standalone-latest"
    
    log_info "Building PostgreSQL image..."
    log_info "Image: $image_name"
    log_info "Context: $PROJECT_ROOT/build/docker/postgresql"
    log_info "Dockerfile: Dockerfile.standalone"
    
    local build_args=(
        "--build-arg" "VERSION=$VERSION"
        "--build-arg" "BUILD_DATE=$BUILD_DATE"
        "--build-arg" "VCS_REF=$VCS_REF"
        "--tag" "$image_name"
        "--tag" "$latest_tag"
        "--file" "$PROJECT_ROOT/build/docker/postgresql/Dockerfile.standalone"
    )
    
    if [ "$use_cache" = "false" ]; then
        build_args+=("--no-cache")
    fi
    
    build_args+=("$PROJECT_ROOT/build/docker/postgresql")
    
    if ! docker build "${build_args[@]}"; then
        log_error "Failed to build PostgreSQL image"
        return 1
    fi
    
    log_success "PostgreSQL image built successfully"
    
    # Show image size
    local size=$(docker images --format "table {{.Size}}" "$image_name" | tail -n 1)
    log_info "Image size: $size"
}

# Function to build Redis image
build_redis_image() {
    local use_cache="$1"
    local image_name="$REGISTRY_URL/blacklist-redis:standalone"
    local latest_tag="$REGISTRY_URL/blacklist-redis:standalone-latest"
    
    log_info "Building Redis image..."
    log_info "Image: $image_name"
    log_info "Context: $PROJECT_ROOT/build/docker/redis"
    log_info "Dockerfile: Dockerfile.standalone"
    
    local build_args=(
        "--build-arg" "VERSION=$VERSION"
        "--build-arg" "BUILD_DATE=$BUILD_DATE"
        "--build-arg" "VCS_REF=$VCS_REF"
        "--tag" "$image_name"
        "--tag" "$latest_tag"
        "--file" "$PROJECT_ROOT/build/docker/redis/Dockerfile.standalone"
    )
    
    if [ "$use_cache" = "false" ]; then
        build_args+=("--no-cache")
    fi
    
    build_args+=("$PROJECT_ROOT/build/docker/redis")
    
    if ! docker build "${build_args[@]}"; then
        log_error "Failed to build Redis image"
        return 1
    fi
    
    log_success "Redis image built successfully"
    
    # Show image size
    local size=$(docker images --format "table {{.Size}}" "$image_name" | tail -n 1)
    log_info "Image size: $size"
}

# Function to push images
push_images() {
    local images_to_push="$1"
    
    log_info "Pushing images to registry: $REGISTRY_URL"
    
    case "$images_to_push" in
        "app")
            docker push "$REGISTRY_URL/blacklist:standalone"
            docker push "$REGISTRY_URL/blacklist:standalone-latest"
            ;;
        "postgresql")
            docker push "$REGISTRY_URL/blacklist-postgresql:standalone"
            docker push "$REGISTRY_URL/blacklist-postgresql:standalone-latest"
            ;;
        "redis")
            docker push "$REGISTRY_URL/blacklist-redis:standalone"
            docker push "$REGISTRY_URL/blacklist-redis:standalone-latest"
            ;;
        "all")
            docker push "$REGISTRY_URL/blacklist:standalone"
            docker push "$REGISTRY_URL/blacklist:standalone-latest"
            docker push "$REGISTRY_URL/blacklist-postgresql:standalone"
            docker push "$REGISTRY_URL/blacklist-postgresql:standalone-latest"
            docker push "$REGISTRY_URL/blacklist-redis:standalone"
            docker push "$REGISTRY_URL/blacklist-redis:standalone-latest"
            ;;
    esac
    
    log_success "Images pushed successfully"
}

# Function to build images in parallel
build_parallel() {
    local use_cache="$1"
    
    log_info "Building all images in parallel..."
    
    # Start builds in background
    (build_app_image "$use_cache") &
    app_pid=$!
    
    (build_postgresql_image "$use_cache") &
    postgres_pid=$!
    
    (build_redis_image "$use_cache") &
    redis_pid=$!
    
    # Wait for all builds to complete
    local failed=0
    
    if ! wait $app_pid; then
        log_error "Application build failed"
        failed=1
    fi
    
    if ! wait $postgres_pid; then
        log_error "PostgreSQL build failed"
        failed=1
    fi
    
    if ! wait $redis_pid; then
        log_error "Redis build failed"
        failed=1
    fi
    
    if [ $failed -eq 1 ]; then
        log_error "Some builds failed"
        return 1
    fi
    
    log_success "All images built successfully in parallel"
}

# Function to show build summary
show_build_summary() {
    log_info "Build Summary:"
    echo
    
    images=(
        "$REGISTRY_URL/blacklist:standalone"
        "$REGISTRY_URL/blacklist-postgresql:standalone"
        "$REGISTRY_URL/blacklist-redis:standalone"
    )
    
    for image in "${images[@]}"; do
        if docker images "$image" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -q standalone; then
            docker images "$image" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep standalone
        else
            echo "$image - Not found"
        fi
    done
    
    echo
    log_info "Total images built: $(docker images "$REGISTRY_URL/blacklist*:*standalone*" -q | wc -l)"
    
    # Show total size
    local total_size=$(docker images "$REGISTRY_URL/blacklist*:*standalone*" --format "{{.Size}}" | sed 's/[^0-9.]//g' | awk '{sum += $1} END {print sum}')
    log_info "Approximate total size: ${total_size}MB"
}

# Function to validate images
validate_images() {
    local images_to_validate="$1"
    
    log_info "Validating built images..."
    
    local validation_failed=0
    
    case "$images_to_validate" in
        "app"|"all")
            if docker run --rm "$REGISTRY_URL/blacklist:standalone" python3 -c "import sys; print('Python version:', sys.version)" &> /dev/null; then
                log_success "Application image validation passed"
            else
                log_error "Application image validation failed"
                validation_failed=1
            fi
            ;;
    esac
    
    case "$images_to_validate" in
        "postgresql"|"all")
            if docker run --rm "$REGISTRY_URL/blacklist-postgresql:standalone" postgres --version &> /dev/null; then
                log_success "PostgreSQL image validation passed"
            else
                log_error "PostgreSQL image validation failed"
                validation_failed=1
            fi
            ;;
    esac
    
    case "$images_to_validate" in
        "redis"|"all")
            if docker run --rm "$REGISTRY_URL/blacklist-redis:standalone" redis-server --version &> /dev/null; then
                log_success "Redis image validation passed"
            else
                log_error "Redis image validation failed"
                validation_failed=1
            fi
            ;;
    esac
    
    if [ $validation_failed -eq 1 ]; then
        log_error "Image validation failed"
        return 1
    fi
    
    log_success "All image validations passed"
}

# Parse command line arguments
IMAGES_TO_BUILD="all"
USE_CACHE="true"
PUSH_IMAGES="false"
PARALLEL_BUILD="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY_URL="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGES="true"
            shift
            ;;
        --no-cache)
            USE_CACHE="false"
            shift
            ;;
        --parallel)
            PARALLEL_BUILD="true"
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        app|postgresql|redis|all)
            IMAGES_TO_BUILD="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
log_info "Blacklist Management System - Standalone Docker Build"
log_info "Registry: $REGISTRY_URL"
log_info "Version: $VERSION"
log_info "Build Date: $BUILD_DATE"
log_info "VCS Ref: $VCS_REF"
log_info "Images: $IMAGES_TO_BUILD"
log_info "Use Cache: $USE_CACHE"
log_info "Push: $PUSH_IMAGES"
log_info "Parallel: $PARALLEL_BUILD"
echo

# Check prerequisites
check_docker
check_prerequisites

# Record start time
start_time=$(date +%s)

# Build images
if [ "$PARALLEL_BUILD" = "true" ] && [ "$IMAGES_TO_BUILD" = "all" ]; then
    build_parallel "$USE_CACHE"
else
    case "$IMAGES_TO_BUILD" in
        "app")
            build_app_image "$USE_CACHE"
            ;;
        "postgresql")
            build_postgresql_image "$USE_CACHE"
            ;;
        "redis")
            build_redis_image "$USE_CACHE"
            ;;
        "all")
            build_app_image "$USE_CACHE"
            build_postgresql_image "$USE_CACHE"
            build_redis_image "$USE_CACHE"
            ;;
        *)
            log_error "Unknown image type: $IMAGES_TO_BUILD"
            exit 1
            ;;
    esac
fi

# Validate images
validate_images "$IMAGES_TO_BUILD"

# Push images if requested
if [ "$PUSH_IMAGES" = "true" ]; then
    push_images "$IMAGES_TO_BUILD"
fi

# Calculate build time
end_time=$(date +%s)
build_time=$((end_time - start_time))

# Show summary
echo
show_build_summary
echo
log_success "Build completed successfully in ${build_time} seconds"

# Show next steps
echo
log_info "Next steps:"
log_info "1. Test the images: $PROJECT_ROOT/scripts/run-standalone.sh start"
log_info "2. Push to registry: $0 --push"
log_info "3. Deploy standalone: $PROJECT_ROOT/scripts/run-standalone.sh start --pull"
#!/bin/bash
# Common functions and utilities for blacklist CI/CD scripts

# Color definitions
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# Logging functions
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Error handling
set_error_trap() {
    trap 'error_handler $? $LINENO' ERR
}

error_handler() {
    local exit_code=$1
    local line_number=$2
    print_error "Command failed with exit code $exit_code at line $line_number"
    exit "$exit_code"
}

# Check prerequisites
check_command() {
    local cmd=$1
    local install_hint=$2
    
    if ! command -v "$cmd" &> /dev/null; then
        print_error "$cmd is not installed"
        if [[ -n "$install_hint" ]]; then
            print_info "Install hint: $install_hint"
        fi
        return 1
    fi
    return 0
}

# Load environment variables
load_env() {
    local env_file="${1:-.env}"
    
    if [[ -f "$env_file" ]]; then
        # Export variables while excluding comments and empty lines
        set -a
        source <(grep -v '^#' "$env_file" | grep -v '^$')
        set +a
        print_info "Loaded environment from $env_file"
    else
        print_warning "Environment file not found: $env_file"
        return 1
    fi
}

# Mask sensitive output
mask_value() {
    local value="$1"
    local show_chars="${2:-3}"
    
    if [[ -z "$value" ]]; then
        echo "(empty)"
    elif [[ ${#value} -le $((show_chars * 2)) ]]; then
        echo "***"
    else
        echo "${value:0:$show_chars}***${value: -$show_chars}"
    fi
}

# Retry mechanism
retry() {
    local max_attempts="${1:-3}"
    local delay="${2:-5}"
    local command="${@:3}"
    local attempt=1
    
    until [[ $attempt -gt $max_attempts ]]; do
        print_info "Attempt $attempt/$max_attempts: $command"
        
        if eval "$command"; then
            return 0
        fi
        
        print_warning "Command failed. Retrying in ${delay}s..."
        sleep "$delay"
        ((attempt++))
    done
    
    print_error "Command failed after $max_attempts attempts"
    return 1
}

# Get script directory
get_script_dir() {
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
}

# Get project root
get_project_root() {
    local script_dir="$(get_script_dir)"
    # Assuming scripts/lib/common.sh structure
    echo "$(cd "$script_dir/../.." && pwd)"
}

# Export common functions
export -f print_step print_success print_warning print_error print_info
export -f check_command load_env mask_value retry
export -f get_script_dir get_project_root
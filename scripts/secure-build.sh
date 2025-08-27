#!/bin/bash
# Secure Docker Build Script for Blacklist Management System
# This script builds the Docker image with proper secret management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="blacklist"
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile"

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build Docker image securely with proper secret management"
    echo ""
    echo "Options:"
    echo "  -n, --name NAME       Image name (default: blacklist)"
    echo "  -t, --tag TAG         Image tag (default: latest)"
    echo "  -f, --file FILE       Dockerfile path (default: Dockerfile)"
    echo "  -e, --env-file FILE   Environment file for secrets"
    echo "  -h, --help            Show this help"
    echo ""
    echo "Environment variables (required):"
    echo "  SECRET_KEY           Application secret key"
    echo "  JWT_SECRET_KEY       JWT secret key"
    echo "  DEFAULT_API_KEY      Default API key"
    echo "  ADMIN_PASSWORD       Admin password"
    echo ""
    echo "Example:"
    echo "  $0 --env-file .env.production"
    echo "  SECRET_KEY=xxx JWT_SECRET_KEY=yyy $0"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        -e|--env-file)
            if [[ -f "$2" ]]; then
                export $(cat "$2" | grep -v '^#' | xargs)
                echo -e "${GREEN}Loaded environment from $2${NC}"
            else
                echo -e "${RED}Error: Environment file $2 not found${NC}"
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Check required environment variables
check_required_vars() {
    local missing_vars=()
    
    [[ -z "$SECRET_KEY" ]] && missing_vars+=("SECRET_KEY")
    [[ -z "$JWT_SECRET_KEY" ]] && missing_vars+=("JWT_SECRET_KEY")  
    [[ -z "$DEFAULT_API_KEY" ]] && missing_vars+=("DEFAULT_API_KEY")
    [[ -z "$ADMIN_PASSWORD" ]] && missing_vars+=("ADMIN_PASSWORD")
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${RED}Error: Missing required environment variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${RED}  - $var${NC}"
        done
        echo ""
        echo -e "${YELLOW}Set them via environment or --env-file option${NC}"
        exit 1
    fi
}

# Security validation
validate_secrets() {
    echo -e "${YELLOW}Validating secret requirements...${NC}"
    
    # Check minimum length requirements
    [[ ${#SECRET_KEY} -lt 32 ]] && echo -e "${YELLOW}Warning: SECRET_KEY should be at least 32 characters${NC}"
    [[ ${#JWT_SECRET_KEY} -lt 32 ]] && echo -e "${YELLOW}Warning: JWT_SECRET_KEY should be at least 32 characters${NC}"
    [[ ${#ADMIN_PASSWORD} -lt 12 ]] && echo -e "${YELLOW}Warning: ADMIN_PASSWORD should be at least 12 characters${NC}"
    
    # Check for default/weak values
    [[ "$SECRET_KEY" == "changeme" ]] && echo -e "${RED}Error: SECRET_KEY cannot be 'changeme'${NC}" && exit 1
    [[ "$JWT_SECRET_KEY" == "changeme" ]] && echo -e "${RED}Error: JWT_SECRET_KEY cannot be 'changeme'${NC}" && exit 1
    [[ "$ADMIN_PASSWORD" == "changeme" ]] && echo -e "${RED}Error: ADMIN_PASSWORD cannot be 'changeme'${NC}" && exit 1
    
    echo -e "${GREEN}Secret validation passed${NC}"
}

# Build Docker image
build_image() {
    echo -e "${GREEN}Building Docker image: $IMAGE_NAME:$IMAGE_TAG${NC}"
    
    docker build \
        --build-arg SECRET_KEY="$SECRET_KEY" \
        --build-arg JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        --build-arg DEFAULT_API_KEY="$DEFAULT_API_KEY" \
        --build-arg ADMIN_PASSWORD="$ADMIN_PASSWORD" \
        -t "$IMAGE_NAME:$IMAGE_TAG" \
        -f "$DOCKERFILE" \
        .
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}Build completed successfully${NC}"
        echo -e "${GREEN}Image: $IMAGE_NAME:$IMAGE_TAG${NC}"
    else
        echo -e "${RED}Build failed${NC}"
        exit 1
    fi
}

# Security scan (if trivy is available)
security_scan() {
    if command -v trivy &> /dev/null; then
        echo -e "${YELLOW}Running security scan...${NC}"
        trivy image --severity HIGH,CRITICAL "$IMAGE_NAME:$IMAGE_TAG"
    else
        echo -e "${YELLOW}Trivy not found, skipping security scan${NC}"
        echo -e "${YELLOW}Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh${NC}"
    fi
}

# Main execution
main() {
    echo -e "${GREEN}=== Secure Docker Build ===${NC}"
    echo ""
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker is not running${NC}"
        exit 1
    fi
    
    # Check if Dockerfile exists
    if [[ ! -f "$DOCKERFILE" ]]; then
        echo -e "${RED}Error: Dockerfile not found: $DOCKERFILE${NC}"
        exit 1
    fi
    
    check_required_vars
    validate_secrets
    build_image
    security_scan
    
    echo ""
    echo -e "${GREEN}=== Build Complete ===${NC}"
    echo -e "Image: ${GREEN}$IMAGE_NAME:$IMAGE_TAG${NC}"
    echo -e "Run with: ${YELLOW}docker run -p 2541:2541 $IMAGE_NAME:$IMAGE_TAG${NC}"
}

# Run main function
main "$@"
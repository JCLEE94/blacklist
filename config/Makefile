# Makefile for Blacklist Management System

.PHONY: help init test lint start stop restart logs status clean

# Default target
help:
	@echo "Blacklist Management System - Makefile"
	@echo "====================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make help         Show this help message"
	@echo "  make init         Initialize environment"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run code linting"
	@echo "  make start        Start services"
	@echo "  make stop         Stop services"
	@echo "  make restart      Restart services"
	@echo "  make logs         Show logs"
	@echo "  make status       Check status"
	@echo "  make clean        Clean up resources"
	@echo ""
	@echo "Registry operations:"
	@echo "  make registry-test      Test registry connectivity"
	@echo "  make registry-deploy    Build and deploy to registry"
	@echo "  make docker-build       Build Docker image"
	@echo "  make docker-push        Push Docker image"
	@echo ""
	@echo "Quick start:"
	@echo "  make init         # Setup environment"
	@echo "  make start        # Start services"
	@echo "  make logs         # Check logs"

# Initialize environment
init:
	@echo "Initializing environment..."
	@pip install -r config/requirements.txt
	@pip install -r config/requirements-dev.txt || echo "No dev requirements"
	@python3 init_database.py
	@cp .env.example .env 2>/dev/null || echo ".env already exists"
	@echo "Environment initialized! Edit .env if needed."

# Run tests
test:
	@echo "Running tests..."
	@pytest tests/ -v --cov=src --cov-report=term-missing

# Run linting
lint:
	@echo "Running linters..."
	@flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
	@black --check src/
	@isort --check-only src/

# Start services
start:
	@docker-compose -f docker/docker-compose.yml up -d

# Stop services
stop:
	@docker-compose -f docker/docker-compose.yml down

# Restart services
restart:
	@docker-compose -f docker/docker-compose.yml restart

# Show logs
logs:
	@docker-compose -f docker/docker-compose.yml logs -f

# Check status
status:
	@docker-compose -f docker/docker-compose.yml ps

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .coverage htmlcov/
	@docker-compose -f docker/docker-compose.yml down --volumes --remove-orphans
	@echo "Cleanup completed!"

# Development shortcuts
.PHONY: run dev install docker-build docker-push k8s-deploy k8s-status argocd-sync registry-test registry-deploy

# Run development server (local)
run:
	@python3 commands/scripts/main.py --debug

# Install dependencies
install:
	@pip install -r config/requirements.txt

# Development mode with auto-reload (local)
dev:
	@FLASK_ENV=development python3 commands/scripts/main.py --debug

# Docker operations
docker-build:
	@echo "Building Docker image..."
	@docker build -f docker/Dockerfile -t registry.jclee.me/jclee94/blacklist:latest .
	@echo "Docker image built successfully!"

docker-push:
	@echo "Pushing Docker image to registry..."
	@docker push registry.jclee.me/jclee94/blacklist:latest
	@echo "Docker image pushed successfully!"

docker-run:
	@echo "Running Docker container locally..."
	@docker run -d --name blacklist-test \
		-p 2541:2541 \
		-e FLASK_ENV=production \
		registry.jclee.me/jclee94/blacklist:latest

# Registry operations
registry-test:
	@echo "Testing registry connectivity..."
	@scripts/test-registry-connection.sh

registry-deploy:
	@echo "Building and deploying to registry..."
	@scripts/registry-deploy.sh

# Kubernetes operations
k8s-deploy:
	@echo "Deploying to Kubernetes..."
	@kubectl apply -k k8s/overlays/production
	@echo "Kubernetes deployment initiated!"

k8s-status:
	@echo "Kubernetes deployment status:"
	@kubectl get pods -l app=blacklist -o wide
	@echo ""
	@kubectl get services -l app=blacklist
	@echo ""
	@kubectl get ingress blacklist-ingress

k8s-logs:
	@echo "Fetching Kubernetes logs..."
	@kubectl logs -l app=blacklist --tail=100

k8s-describe:
	@echo "Describing Kubernetes resources..."
	@kubectl describe deployment blacklist
	@echo ""
	@kubectl describe service blacklist-service

# ArgoCD operations
argocd-sync:
	@echo "Triggering ArgoCD sync..."
	@curl -k -X POST https://argo.jclee.me/api/v1/applications/blacklist-production/sync \
		-H "Authorization: Bearer $(ARGOCD_TOKEN)" || echo "Manual sync required via ArgoCD UI"

argocd-status:
	@echo "ArgoCD application status:"
	@curl -k -s https://argo.jclee.me/api/v1/applications/blacklist-production \
		-H "Authorization: Bearer $(ARGOCD_TOKEN)" | jq '.status.sync, .status.health' || echo "Check ArgoCD UI manually"

# Complete deployment workflow
deploy:
	@echo "🚀 Complete GitOps Deployment Workflow"
	@echo "======================================"
	@echo ""
	@echo "1. Building and pushing Docker image..."
	@make docker-build
	@make docker-push
	@echo ""
	@echo "2. Waiting for ArgoCD auto-sync (2 minutes)..."
	@sleep 120
	@echo ""
	@echo "3. Checking deployment status..."
	@make k8s-status
	@echo ""
	@echo "🎯 Deployment URLs:"
	@echo "   Application: https://blacklist.jclee.me"
	@echo "   ArgoCD: https://argo.jclee.me"
	@echo "   Health: https://blacklist.jclee.me/health"
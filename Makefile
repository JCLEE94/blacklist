# CNCF Compliant Makefile for Blacklist Management System
.PHONY: help build test deploy clean lint security e2e integration docker-build docker-push helm-install

# Variables
DOCKER_REGISTRY ?= registry.jclee.me
VERSION ?= $(shell cat config/VERSION 2>/dev/null || echo "1.0.1411")
IMAGE_NAME ?= $(DOCKER_REGISTRY)/blacklist:$(VERSION)
LATEST_IMAGE ?= $(DOCKER_REGISTRY)/blacklist:latest
CHART_NAME ?= blacklist
NAMESPACE ?= blacklist

# Colors for output
YELLOW := \033[33m
GREEN := \033[32m
BLUE := \033[34m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Blacklist Management System - CNCF Compliant Makefile$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Development Commands
install: ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	pip install -r config/requirements.txt
	pip install -r config/requirements-dev.txt

dev: ## Start development server
	@echo "$(GREEN)Starting development server...$(NC)"
	python app/main.py --debug

run: ## Run the application locally
	@echo "$(GREEN)Running application...$(NC)"
	python app/main.py

# Testing Commands
test: ## Run all tests
	@echo "$(GREEN)Running unit tests...$(NC)"
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	python -m pytest tests/ -m "unit" -v

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	python -m pytest test/integration/ -v

test-e2e: e2e ## Run end-to-end tests

e2e: ## Run end-to-end tests
	@echo "$(GREEN)Running end-to-end tests...$(NC)"
	python -m pytest test/e2e/ -v

# Code Quality Commands
lint: ## Run linters
	@echo "$(GREEN)Running linters...$(NC)"
	black --check src/ tests/ app/
	isort --check-only src/ tests/ app/
	flake8 src/ tests/ app/ --max-line-length=88 --extend-ignore=E203,W503

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	black src/ tests/ app/
	isort src/ tests/ app/

security: ## Run security checks
	@echo "$(GREEN)Running security checks...$(NC)"
	bandit -r src/ app/ -ll
	safety check

# Build Commands
build: docker-build ## Build the application

docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(IMAGE_NAME) -t $(LATEST_IMAGE) -f build/docker/Dockerfile .

docker-push: ## Push Docker image to registry
	@echo "$(GREEN)Pushing Docker image to registry...$(NC)"
	./scripts/build-and-push.sh

registry-deploy: ## Direct deploy to registry.jclee.me with Watchtower
	@echo "$(GREEN)Deploying directly to registry.jclee.me...$(NC)"
	./scripts/build-and-push.sh

registry-workflow: ## Complete registry.jclee.me deployment workflow
	@echo "$(GREEN)Running complete registry.jclee.me deployment workflow...$(NC)"
	./scripts/registry-deploy-workflow.sh

registry-verify: ## Verify registry.jclee.me deployment status
	@echo "$(GREEN)Verifying registry.jclee.me deployment...$(NC)"
	./scripts/verify-registry-deployment.sh

# Deployment Commands
deploy: ## Deploy to Kubernetes using Helm
	@echo "$(GREEN)Deploying to Kubernetes...$(NC)"
	helm upgrade --install $(CHART_NAME) ./charts/blacklist \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--set image.repository=$(DOCKER_REGISTRY)/blacklist \
		--set image.tag=$(VERSION)

deploy-local: ## Deploy locally using standalone Docker
	@echo "$(GREEN)Deploying locally with standalone Docker...$(NC)"
	./start.sh build && ./start.sh start

helm-install: ## Install/upgrade Helm chart
	@echo "$(GREEN)Installing Helm chart...$(NC)"
	helm upgrade --install $(CHART_NAME) ./charts/blacklist \
		--namespace $(NAMESPACE) \
		--create-namespace

helm-uninstall: ## Uninstall Helm chart
	@echo "$(GREEN)Uninstalling Helm chart...$(NC)"
	helm uninstall $(CHART_NAME) --namespace $(NAMESPACE)

# Environment Commands
init: ## Initialize development environment
	@echo "$(GREEN)Initializing development environment...$(NC)"
	python scripts/setup-credentials.py
	python commands/utils/init_database.py

clean: ## Clean build artifacts and caches
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	rm -rf __pycache__/ .pytest_cache/ htmlcov/ .coverage
	rm -rf build/ dist/ *.egg-info/
	docker system prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

start: ## Start standalone Docker container
	@echo "$(GREEN)Starting standalone container...$(NC)"
	./start.sh start

stop: ## Stop standalone container
	@echo "$(GREEN)Stopping standalone container...$(NC)"
	./start.sh stop

restart: ## Restart standalone container
	@echo "$(GREEN)Restarting standalone container...$(NC)"
	./start.sh restart

logs: ## View container logs
	@echo "$(GREEN)Viewing container logs...$(NC)"
	./start.sh logs

status: ## Check container status
	@echo "$(GREEN)Checking container status...$(NC)"
	./start.sh status

# Verification Commands
verify: ## Verify CNCF compliance and project health
	@echo "$(GREEN)Verifying CNCF compliance...$(NC)"
	./hack/verify-structure.sh
	./hack/verify-security.sh

health: ## Check application health
	@echo "$(GREEN)Checking application health...$(NC)"
	curl -f http://localhost:32542/health || curl -f http://localhost:2542/health

# Documentation Commands
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	@echo "Documentation available in docs/ directory"

# CI/CD Commands
ci: lint test security ## Run CI pipeline locally
	@echo "$(GREEN)CI pipeline completed successfully$(NC)"

cd: build docker-push deploy ## Run CD pipeline
	@echo "$(GREEN)CD pipeline completed successfully$(NC)"

# Version Commands
version: ## Show current version
	@echo "Current version: $(VERSION)"

version-bump: ## Bump version (requires version argument: make version-bump version=1.4.0)
	@if [ -z "$(version)" ]; then \
		echo "$(RED)Please provide version: make version-bump version=1.4.0$(NC)"; \
		exit 1; \
	fi
	@echo "$(version)" > config/VERSION
	@echo "$(GREEN)Version bumped to $(version)$(NC)"
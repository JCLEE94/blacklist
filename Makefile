# Makefile for Blacklist Management System

.PHONY: help init test lint security build deploy clean

# Default target
help:
	@echo "Blacklist Management System - Makefile"
	@echo "====================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make help        Show this help message"
	@echo "  make init        Initialize development environment"
	@echo "  make test        Run all tests"
	@echo "  make lint        Run code linting"
	@echo "  make security    Run security checks"
	@echo "  make build       Build Docker image"
	@echo "  make deploy      Deploy to Kubernetes"
	@echo "  make clean       Clean up resources"
	@echo ""
	@echo "Quick start:"
	@echo "  make init        # Setup environment"
	@echo "  make test        # Run tests"
	@echo "  make build       # Build image"
	@echo "  make deploy      # Deploy application"

# Initialize environment
init:
	@echo "Initializing development environment..."
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt || echo "No dev requirements"
	@python3 init_database.py
	@./scripts/manage.sh init
	@echo "Environment initialized!"

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

# Run security checks
security:
	@echo "Running security checks..."
	@bandit -r src/ -f json -o bandit-report.json || true
	@safety check --json > safety-report.json || true
	@./scripts/manage.sh security

# Build Docker image
build:
	@echo "Building Docker image..."
	@docker build -f deployment/Dockerfile.optimized -t registry.jclee.me/blacklist:latest .

# Deploy application
deploy:
	@echo "Deploying application..."
	@./scripts/manage.sh deploy

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .coverage htmlcov/
	@rm -f *-report.json *-report.xml
	@echo "Cleanup completed!"

# Development shortcuts
.PHONY: run dev install

# Run development server
run:
	@python3 main.py --debug

# Install dependencies
install:
	@pip install -r requirements.txt

# Development mode with auto-reload
dev:
	@FLASK_ENV=development python3 main.py --debug
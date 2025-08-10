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
	@echo "Quick start:"
	@echo "  make init         # Setup environment"
	@echo "  make start        # Start services"
	@echo "  make logs         # Check logs"

# Initialize environment
init:
	@echo "Initializing environment..."
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt || echo "No dev requirements"
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
	@./start.sh start

# Stop services
stop:
	@./start.sh stop

# Restart services
restart:
	@./start.sh restart

# Show logs
logs:
	@./start.sh logs

# Check status
status:
	@./start.sh status

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .coverage htmlcov/
	@./start.sh clean
	@echo "Cleanup completed!"

# Development shortcuts
.PHONY: run dev install

# Run development server (local)
run:
	@python3 main.py --debug

# Install dependencies
install:
	@pip install -r requirements.txt

# Development mode with auto-reload (local)
dev:
	@FLASK_ENV=development python3 main.py --debug
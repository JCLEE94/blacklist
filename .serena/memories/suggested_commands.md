# Suggested Development Commands

## Application Startup
```bash
# Install dependencies
pip install -r requirements.txt

# Development server (with fallback chain)
python3 main.py                    # Default port 8541
python3 main.py --port 8080        # Custom port
python3 main.py --debug            # Debug mode

# Production server
gunicorn -w 4 -b 0.0.0.0:2541 --timeout 120 main:application
```

## Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not slow and not integration"    # Unit tests only
pytest tests/test_blacklist_unified.py      # Specific module
pytest -v --cov=src                         # With coverage
```

## Container Operations
```bash
# Build and deploy
./deployment/deploy.sh              # Full deployment to registry.jclee.me

# Local development
docker-compose -f docker/docker-compose.yml up -d --build
docker logs blacklist-app-1 -f     # View logs
docker exec -it blacklist-app-1 /bin/bash  # Shell access
```

## Data Collection
```bash
# Check collection status
curl http://localhost:8541/api/collection/status

# Enable/disable collection
curl -X POST http://localhost:8541/api/collection/enable
curl -X POST http://localhost:8541/api/collection/disable

# Manual triggers
curl -X POST http://localhost:8541/api/collection/regtech/trigger
curl -X POST http://localhost:8541/api/collection/secudium/trigger
```

## Git Operations
```bash
# Conventional commits
git add .
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git commit -m "docs: update README"

# GitHub setup
./scripts/github-setup.sh
./scripts/set-github-secrets.sh
```

## System Commands (Linux)
```bash
# File operations
ls -la              # List files with details
find . -name "*.py" # Find Python files
grep -r "pattern"   # Search in files

# Process management
ps aux | grep python
kill -9 <PID>
systemctl status <service>

# Log viewing
tail -f logs/updater.log
journalctl -u blacklist -f

# Network debugging
netstat -tlnp | grep 8541
curl -I http://localhost:8541/health
```

## Debugging
```bash
# REGTECH authentication analysis
python3 scripts/debug_regtech_advanced.py

# Integration testing
python3 scripts/integration_test_comprehensive.py

# Performance profiling
python3 -m cProfile -o profile.out main.py
```
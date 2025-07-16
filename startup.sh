#!/bin/bash
set -e

echo "=== Starting Blacklist Application ==="
echo "Environment: ${ENV:-production}"
echo "Port: ${PORT:-8541}"
echo "Working directory: $(pwd)"

# Database initialization
echo "Initializing database..."
python3 init_database.py || echo "Database initialization failed (may already exist)"

# Start application
echo "Starting Gunicorn..."
# Add preload to ensure app is ready before accepting requests
exec gunicorn -w 4 -b 0.0.0.0:${PORT:-8541} --timeout 120 --preload --access-logfile - --error-logfile - main:application
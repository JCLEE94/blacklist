#!/bin/bash
set -e

echo "=== Starting Blacklist Application ==="
echo "Environment: ${ENV:-production}"
echo "Port: ${PORT:-2541}"
echo "Working directory: $(pwd)"

# Database initialization
echo "Initializing database..."
python3 init_database.py || echo "Database initialization failed (may already exist)"

# Start application
echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:${PORT:-2541} --timeout 120 --access-logfile - --error-logfile - main:application
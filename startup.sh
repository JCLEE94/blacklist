#!/bin/bash
# Startup script to handle permissions and initialize the application

echo "Starting blacklist application..."
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"

# Create necessary directories
mkdir -p /app/instance /app/data /app/logs /app/data/by_detection_month 2>/dev/null || true

# Try to set permissions (will fail if not root, but that's OK)
chmod 777 /app/instance /app/data /app/logs /app/data/by_detection_month 2>/dev/null || true

# List directories to debug
echo "Directory permissions:"
ls -la /app/ | grep -E "instance|data|logs"

# Remove old database if exists and create new one
echo "Removing old database files..."
rm -f /app/instance/blacklist.db /app/instance/secudium.db 2>/dev/null || true

# Initialize database - ALWAYS create fresh
echo "Initializing fresh database..."
python3 init_database.py --force-recreate || true

# Start the application
echo "Starting application..."
exec python3 main.py
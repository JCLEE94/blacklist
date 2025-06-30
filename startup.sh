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

# Check if database exists
if [ -f "/app/instance/blacklist.db" ]; then
    echo "Database exists, using existing database..."
else
    echo "Database not found, creating new database..."
    python3 init_database.py || true
fi

# Start the application
echo "Starting application..."
exec python3 main.py
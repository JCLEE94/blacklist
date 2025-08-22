# Multi-stage build for Python Flask application
FROM python:3.11-slim as builder

# Build dependencies (PostgreSQL support)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /build

# Copy requirements and install dependencies
COPY config/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Production stage
FROM python:3.11-slim

# Runtime dependencies (PostgreSQL support)
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --user-group app \
    && mkdir -p /app/instance /app/data /app/logs /app/backups \
    && chown -R app:app /app

WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=app:app . .

# Create additional directories that might be needed at runtime  
RUN mkdir -p /app/data/by_detection_month /app/data/by_source /app/data/blacklist_ips /app/data/exports /app/data/logs /app/data/regtech /app/data/secudium /app/temp \
    && chown -R app:app /app

# Set PATH to include user packages
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Switch to non-root user
USER app

# Create required directories with proper permissions
RUN mkdir -p instance data logs \
    && chmod 755 instance data logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:2542/health || exit 1

# Expose port
EXPOSE 2542

# Default command - use proper entry point path
CMD ["python3", "src/core/app_compact.py"]
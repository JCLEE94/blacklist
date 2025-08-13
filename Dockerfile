# Multi-stage build for Python Flask application
FROM python:3.11-slim as builder

# Build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --user-group app \
    && mkdir -p /app/instance /app/data /app/logs \
    && chown -R app:app /app

WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY --chown=app:app . .

# Set PATH to include user packages
ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONPATH=/app:/home/app/.local/lib/python3.11/site-packages
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Switch to non-root user
USER app

# Create required directories with proper permissions
RUN mkdir -p instance data logs \
    && chmod 755 instance data logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:2541/health || exit 1

# Expose port
EXPOSE 2541

# Default command
CMD ["python3", "app/main.py", "--host", "0.0.0.0", "--port", "2541"]
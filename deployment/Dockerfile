# Multi-stage Python FastAPI Blacklist Management System
# Stage 1: Builder for production dependencies
FROM python:3.9 AS builder

# Build arguments - Force rebuild: 2025-07-06T03:11:00Z
ARG BUILD_TIME="2025-07-06T03:11:00Z"  
ENV BUILD_TIME=${BUILD_TIME}
ENV TZ=Asia/Seoul

# python:3.9 already includes gcc, g++, and other build tools
# No need to install them separately, saving significant build time

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (production only)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image with all dependencies
FROM python:3.9-slim AS production

# Build arguments
ARG BUILD_TIME="Unknown"
ENV BUILD_TIME=${BUILD_TIME}
ENV TZ=Asia/Seoul
ENV PYTHONPATH=/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p instance data logs && \
    chown -R app:app /app

# Switch to app user
USER app

# Create database directory  
RUN mkdir -p instance

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8541}/health || exit 1

# Expose port (configurable)
EXPOSE ${PORT:-8541}

# Copy startup script
COPY --chown=app:app startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Initialize database if needed and start application
CMD ["/app/startup.sh"]
# Multi-stage build for Blacklist Application
# Stage 1: Build dependencies
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev

# Copy dependency files
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    && adduser -D appuser

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/instance /app/logs /app/temp \
    && chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-2542}/health || exit 1

# Expose port
EXPOSE ${PORT:-2542}

# Run application
CMD ["python", "-m", "gunicorn", "main:app", "--bind", "0.0.0.0:2542", "--workers", "4", "--timeout", "120"]
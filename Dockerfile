# Multi-stage build for Django backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
# Note: Installing as root during build is acceptable, we'll switch to non-root user later
COPY requirements.txt /app/
RUN pip install --upgrade pip --no-warn-script-location && \
    pip install --no-warn-script-location -r requirements.txt

# Create a non-root user for running the application
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles && \
    chown -R appuser:appuser /app

# Copy project files
COPY --chown=appuser:appuser . /app/

# Copy and set up entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user for runtime
USER appuser

# Expose ports
# 8000 for HTTP/WebSocket (daphne)
EXPOSE 8000

# Use entrypoint script to handle migrations before starting server
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (can be overridden)
# Using daphne for ASGI (supports both HTTP and WebSocket)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]


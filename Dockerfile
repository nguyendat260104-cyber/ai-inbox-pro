# syntax=docker/dockerfile:1
# AI Inbox & Sales Management Platform - Production Dockerfile
# Lightweight, secure, non-root Python 3.13 image

FROM python:3.13-slim AS runner

# Install essential runtime tools (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Set production environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    PYTHONPATH=/app

# Prepare persistent data directory with proper ownership
RUN mkdir -p /app/data && chown -R appuser:appgroup /app/data

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source files
COPY --chown=appuser:appgroup ai_inbox/ /app/ai_inbox/
COPY --chown=appuser:appgroup scripts/ /app/scripts/

USER appuser

# Expose unified HTTP port
EXPOSE 8080

# Healthcheck validating server response and database connectivity
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Launch production server with database initialization and seed checks
CMD ["python", "scripts/serve_inbox.py"]

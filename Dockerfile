# ==============================================================================
# CareerLens — Production Dockerfile
# Compatible with Render.com, Railway, Fly.io, DigitalOcean, AWS
# ==============================================================================

FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout for logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Render injects PORT at runtime; default 10000 for Render, 5001 locally
    PORT=10000 \
    DATABASE_PATH=/app/data/careerlens.db

WORKDIR /app

# Install system deps (curl for healthcheck, libmupdf deps for PyMuPDF)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (Docker layer cache)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . /app/

# Create persistent storage dirs and non-root user
RUN mkdir -p /app/data /app/uploads && \
    useradd -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port (Render will override via $PORT env var)
EXPOSE ${PORT}

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Start Gunicorn using the config file (reads $PORT automatically)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]

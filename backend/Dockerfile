# ==============================================================================
# AgriChain AI — FastAPI Backend Dockerfile
# Production-ready Python 3.11 container with geospatial support.
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system dependencies required by database and network tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies with pip layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application source code, migrations, and ML structure
COPY backend /app/backend
COPY database /app/database
COPY ml /app/ml

# Ensure backend directory and root are importable
ENV PYTHONPATH=/app/backend:/app

WORKDIR /app/backend

# Use non-root user for container security
RUN adduser --disabled-password --gecos "" agrichain && \
    chown -R agrichain:agrichain /app
USER agrichain

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

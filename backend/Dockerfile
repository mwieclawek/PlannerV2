# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker cache optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create package structure for correct imports (backend.app...)
RUN mkdir -p backend/app

# Copy application code into the package structure
COPY app/ backend/app/

# Copy Alembic configuration and migrations
COPY alembic.ini .
COPY alembic/ alembic/

# Set PYTHONPATH so python can find the 'backend' package
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Create entrypoint script that runs migrations then starts server
RUN echo '#!/bin/sh\n\
    echo "Running database migrations..."\n\
    alembic upgrade head\n\
    echo "Starting uvicorn server..."\n\
    exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000\n\
    ' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Run entrypoint script
CMD ["/app/entrypoint.sh"]


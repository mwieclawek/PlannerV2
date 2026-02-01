# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker cache optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create package structure for correct imports (backend.app...)
RUN mkdir -p backend/app

# Copy application code into the package structure
COPY app/ backend/app/

# Set PYTHONPATH so python can find the 'backend' package
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run uvicorn server with full package path
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Dockerfile
ARG TARGETPLATFORM=linux/amd64
ARG PYTHON_IMAGE=python
ARG PYTHON_TAG=3.12-slim
FROM --platform=${TARGETPLATFORM} ${PYTHON_IMAGE}:${PYTHON_TAG}

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKERS=4

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements-run.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-run.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run application with multiple workers for production
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $WORKERS"]

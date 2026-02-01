# Build stage
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir build

# Copy only dependency files first for better caching
COPY pyproject.toml ./

# Build wheel
COPY src/ src/
RUN python -m build --wheel

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install the application
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create data directories
RUN mkdir -p /data /vault && chown -R appuser:appuser /data /vault

# Switch to non-root user
USER appuser

# Set environment variables
ENV VAULT_PATH=/vault
ENV DATA_PATH=/data
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

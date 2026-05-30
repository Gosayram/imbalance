FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev --no-install-project

# Install the project
RUN uv sync --no-dev

# Create data directory
RUN mkdir -p /data

# Set environment variables
ENV IMBALANCE_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

# Expose port for daemon
EXPOSE 4731

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:4731/health')" || exit 1

# Run daemon
CMD ["uv", "run", "imbalance", "daemon", "start", "--port", "4731"]

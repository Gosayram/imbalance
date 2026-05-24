FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN pip install uv==0.11.* && uv sync --frozen --no-dev --compile-bytecode \
    --extra ui --extra ollama

COPY src/ ./src/

FROM python:3.14-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src   /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    IMBALANCE_DATA_DIR=/data

VOLUME ["/data"]
EXPOSE 4731

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:4731/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "imbalance.server"]

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TORCH_BACKEND=cpu
ENV PYTHONUNBUFFERED=1
ENV MLFLOW_DISABLE_AGENT_HINT=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY ecommerce_agent ./ecommerce_agent
RUN uv sync --frozen --no-dev

COPY db ./db
COPY evals ./evals
COPY static ./static

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "ecommerce_agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

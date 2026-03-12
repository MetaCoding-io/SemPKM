FROM python:3.12-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# uv settings: compile bytecode for faster startup, copy mode for Docker layers
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Put the venv on PATH so uvicorn/alembic are available without activation
ENV PATH="/app/.venv/bin:$PATH"

# Create persistent data directory for SQLite and secrets
RUN mkdir -p /app/data
VOLUME /app/data

# Copy dependency definition and lockfile
COPY pyproject.toml uv.lock ./

# Install dependencies from lockfile (frozen = no resolution, no-dev = skip dev deps)
RUN uv sync --frozen --no-dev --no-editable

# Copy Alembic migration configuration and scripts
COPY alembic.ini .
COPY migrations/ migrations/

# Copy application code
COPY app/ app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]

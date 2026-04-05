FROM python:3.12-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# uv settings: compile bytecode for faster startup, copy mode for Docker layers
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Create non-root user for runtime security
RUN groupadd -r sempkm && useradd -r -u 1000 -g sempkm sempkm

# Put the venv on PATH so uvicorn/alembic are available without activation
ENV PATH="/app/.venv/bin:$PATH"

# Create persistent data directory for SQLite and secrets
RUN mkdir -p /app/data
RUN chown -R sempkm:sempkm /app/data
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

# Copy entrypoint script (ensures data subdirectories exist on startup)
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

# Switch to non-root user for runtime
USER sempkm

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

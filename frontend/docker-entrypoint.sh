#!/bin/sh
# Populate the shared volume from the build output on every container start.
# /build-assets/ holds the pristine build output baked into the Docker image.
# /srv/built-assets/ is the shared named volume:
#   - nginx serves /assets/* from this path (via alias directive)
#   - API container reads manifest.json from here (mounted at /app/frontend_assets/)
#
# This runs on every start, so `docker compose build frontend && docker compose up -d`
# automatically updates assets without needing `docker compose down -v`.

if [ -d /build-assets ] && [ -f /build-assets/manifest.json ]; then
    cp -r /build-assets/* /srv/built-assets/ 2>/dev/null || true
fi

exec "$@"

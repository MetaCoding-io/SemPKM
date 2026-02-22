#!/usr/bin/env bash
# Reset the SemPKM instance: wipes auth database, setup token, and secret key.
# The next API restart will trigger first-run setup mode with a new token.
set -euo pipefail

echo "Resetting SemPKM instance..."
docker compose exec api rm -f /app/data/sempkm.db /app/data/.setup-token /app/data/.secret-key
echo "Database and credentials wiped."

echo "Restarting API..."
docker compose restart api

echo ""
echo "Done. Run 'docker compose logs api' to see the new setup token."

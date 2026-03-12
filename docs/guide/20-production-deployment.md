# Chapter 20: Production Deployment

This chapter covers the operational concerns of running SemPKM in a production environment: securing the instance, switching to PostgreSQL, sizing resources, backing up and restoring data, and resetting the instance when needed.

SemPKM ships as a Docker Compose stack with three services: a Python/FastAPI **API** backend, an Nginx **frontend**, and an Eclipse RDF4J **triplestore**. The default configuration is optimized for local development. Production deployment requires adjustments to security, persistence, and resource allocation.

## Securing the Instance

### Secret Key

SemPKM uses a secret key for signing session cookies and authentication tokens. By default, it auto-generates a random key on first run and stores it at `./data/.secret-key` inside the API container.

For production, set an explicit `SECRET_KEY` environment variable so the key persists across container rebuilds:

```bash
# Generate a strong random key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Add it to your environment or `.env` file:

```
SECRET_KEY=your-generated-key-here
```

> **Warning:** If the secret key changes, all existing sessions and magic link tokens are invalidated. Users will need to log in again. Never commit the secret key to version control.

### SMTP Configuration

In development, magic link tokens are displayed directly in the browser when SMTP is not configured. For production, configure SMTP so authentication emails are sent properly:

```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=sempkm@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=sempkm@example.com
```

Without SMTP configured, the setup token and magic link tokens are only visible in the API container logs. This is acceptable for single-user local installations but not for multi-user production deployments.

### Reverse Proxy and HTTPS

The default Docker Compose configuration exposes the frontend on port 3000 (HTTP) and the API on port 8001 (HTTP). For production, place a reverse proxy in front of SemPKM to handle TLS termination.

A common setup uses Nginx, Caddy, or Traefik as the edge proxy:

```
Internet -> Reverse Proxy (HTTPS :443) -> SemPKM Frontend (:3000) -> API (:8001)
```

Example Nginx reverse proxy configuration:

```nginx
server {
    listen 443 ssl;
    server_name sempkm.example.com;

    ssl_certificate     /etc/ssl/certs/sempkm.crt;
    ssl_certificate_key /etc/ssl/private/sempkm.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

> **Note:** SemPKM's session cookies do not currently set the `Secure` flag automatically. When serving over HTTPS, the reverse proxy handles the encryption layer. Ensure your proxy strips and re-adds headers correctly so the backend receives forwarded protocol information.

### Firewall Considerations

In production, only the reverse proxy port (443) should be exposed to the internet. Lock down direct access to:

- Port 3000 (frontend) -- bind to `127.0.0.1:3000:80` in `docker-compose.yml`
- Port 8001 (API) -- bind to `127.0.0.1:8001:8000`
- The triplestore has no published ports by default, which is correct for production

Modify the `ports` section of your `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "127.0.0.1:8001:8000"
  frontend:
    ports:
      - "127.0.0.1:3000:80"
```

## PostgreSQL

### Switching from SQLite

SemPKM uses SQLite by default for the authentication and event metadata database. This is fine for single-user local use but may not scale for multi-user production or cloud deployments.

To switch to PostgreSQL, set the `DATABASE_URL` environment variable:

```
DATABASE_URL=postgresql+asyncpg://sempkm:password@db:5432/sempkm
```

If running PostgreSQL in Docker, add it to your `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: sempkm
      POSTGRES_USER: sempkm
      POSTGRES_PASSWORD: your-secure-password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sempkm"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - sempkm

volumes:
  pgdata:
```

Update the API service to depend on the database:

```yaml
services:
  api:
    environment:
      DATABASE_URL: postgresql+asyncpg://sempkm:your-secure-password@db:5432/sempkm
    depends_on:
      db:
        condition: service_healthy
      triplestore:
        condition: service_healthy
```

### Running Migrations

SemPKM uses Alembic for database schema migrations. The migration scripts are located in `backend/migrations/` and the configuration is in `backend/alembic.ini`.

After switching to PostgreSQL (or after upgrading SemPKM), run migrations:

```bash
docker compose exec api alembic upgrade head
```

Alembic reads the `DATABASE_URL` from the application settings, so it automatically targets the correct database.

> **Tip:** On first run with a new database, SemPKM's startup process creates the initial tables automatically. You only need to run Alembic manually when upgrading between versions that include schema changes.

## Resource Sizing

### Triplestore Memory

The RDF4J triplestore runs as a Java application. The default `JAVA_OPTS` setting allocates 1 GB of heap memory:

```yaml
environment:
  JAVA_OPTS: "-Xmx1g"
```

This is sufficient for most personal use (up to tens of thousands of objects). Adjust based on your expected data volume:

| Usage Level         | Objects    | Triples (approx.)   | Recommended `-Xmx` |
|--------------------|-----------|---------------------|---------------------|
| Personal           | < 5,000   | < 100,000           | 512m - 1g           |
| Small team         | 5,000 - 50,000 | 100,000 - 1,000,000 | 1g - 2g        |
| Large deployment   | 50,000+   | 1,000,000+          | 2g - 4g             |

To change the allocation:

```yaml
services:
  triplestore:
    environment:
      JAVA_OPTS: "-Xmx2g"
```

> **Note:** Each SemPKM object typically produces 5--20 triples depending on the number of properties. Event graphs add additional triples for audit history. A workspace with 10,000 objects will likely have 100,000--300,000 triples in the current state graph, plus historical event data.

### API Container

The API container runs a Python application with Uvicorn. It is generally lightweight, requiring 256--512 MB of RAM for typical workloads. The main memory consumers are:

- rdflib graph parsing (during model installation)
- SHACL validation (during the async validation queue processing)
- Large SPARQL result sets

No special tuning is needed for most deployments.

### Disk Space

Plan for disk usage across three areas:

| Component          | Storage Volume  | Typical Size                              |
|-------------------|----------------|-------------------------------------------|
| Triplestore data  | `rdf4j_data`   | 50 MB -- 5 GB depending on object count   |
| SQL database      | `sempkm_data`  | 1 MB -- 100 MB (auth data, event metadata)|
| Container images  | Docker cache    | ~500 MB total for all three images        |

## Backup and Restore

SemPKM stores data in two places: the RDF4J triplestore (all object data, ontologies, shapes, events) and the SQL database (user accounts, sessions, settings). A complete backup must cover both.

### RDF4J Triplestore Backup

The triplestore data lives in the `rdf4j_data` Docker volume. Back it up by copying the volume contents:

```bash
# Stop the triplestore to ensure consistency
docker compose stop triplestore

# Create a tarball of the volume
docker run --rm \
  -v sempkm_rdf4j_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/rdf4j-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restart the triplestore
docker compose start triplestore
```

Alternatively, use the RDF4J Server REST API to export repositories:

```bash
# Export the sempkm repository as N-Quads (includes named graphs)
curl -H "Accept: application/n-quads" \
  http://localhost:8001/rdf4j-server/repositories/sempkm/statements \
  > backups/sempkm-export-$(date +%Y%m%d).nq
```

The N-Quads export captures all named graphs including event history, current state, and model data.

### SQL Database Backup

For **SQLite** (the default):

```bash
# The database file is inside the sempkm_data volume
docker compose exec api cp /app/data/sempkm.db /app/data/sempkm-backup.db

# Copy the backup out of the container
docker cp $(docker compose ps -q api):/app/data/sempkm-backup.db ./backups/
```

For **PostgreSQL**:

```bash
docker compose exec db pg_dump -U sempkm sempkm > backups/sempkm-pg-$(date +%Y%m%d).sql
```

### Restore Procedure

To restore from backups:

1. Stop all services: `docker compose down`
2. Restore the RDF4J volume from the tarball
3. Restore the SQL database (copy the SQLite file back, or `psql < backup.sql` for PostgreSQL)
4. Start services: `docker compose up -d`
5. Verify data integrity by browsing objects and checking the event log

### Events as Source of Truth

SemPKM uses an event-sourcing architecture. Every mutation is stored as an immutable event in a named graph. The "current state" graph is a materialized view derived by replaying these events.

This means that even if the current state graph is corrupted or lost, it can theoretically be rebuilt from the event history. However, in practice, restoring from a backup is faster and simpler than replaying events. The event architecture primarily provides:

- **Complete audit trail** -- every change is attributed and timestamped
- **Undo capability** -- compensating events can reverse prior changes
- **Temporal queries** -- you can query what the data looked like at any point in time

> **Tip:** For critical deployments, schedule automated backups of both the RDF4J volume and the SQL database. A daily backup with 7-day retention is a reasonable starting point.

## Resetting the Instance

SemPKM includes a reset script that wipes the authentication database and credentials, returning the instance to its first-run state. This is useful for development, testing, or when you need to start fresh with user accounts.

### What the Reset Script Does

The script at `scripts/reset-instance.sh` performs these steps:

1. Deletes the SQLite database (`/app/data/sempkm.db`)
2. Deletes the setup token (`/app/data/.setup-token`)
3. Deletes the secret key (`/app/data/.secret-key`)
4. Restarts the API container

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Resetting SemPKM instance..."
docker compose exec api rm -f /app/data/sempkm.db /app/data/.setup-token /app/data/.secret-key
echo "Database and credentials wiped."

echo "Restarting API..."
docker compose restart api

echo ""
echo "Done. Run 'docker compose logs api' to see the new setup token."
```

### What is Preserved

- **Triplestore data** -- all objects, events, ontologies, shapes, and views in RDF4J remain intact
- **Mental Model files** -- the `models/` directory is not touched
- **Configuration files** -- `docker-compose.yml`, `.env`, and `config/` are not affected

### What is Deleted

- **User accounts** -- all users (owners and members) are removed
- **Sessions** -- all active sessions are invalidated
- **Settings** -- user-configured settings are lost (they live in the SQL database)
- **Setup token** -- a new token is generated on the next API startup
- **Secret key** -- a new key is generated (unless `SECRET_KEY` is set as an environment variable)

### Running the Reset

```bash
./scripts/reset-instance.sh
```

After reset, check the API logs for the new setup token:

```bash
docker compose logs api | grep "setup token"
```

Use this token to complete the setup wizard and create a new owner account, just like the first time you installed SemPKM.

> **Warning:** Resetting does not delete triplestore data. If you need a completely clean slate (including all object data), you must also delete the RDF4J volume: `docker compose down -v` (this removes all Docker volumes for the project).

## Namespace Configuration

SemPKM uses the `BASE_NAMESPACE` setting as the IRI prefix for every object and named graph in the triplestore. For example, with the default namespace, an object might receive the IRI `https://example.org/data/abc123` and its event graphs would live under the same prefix.

The default value is:

```
BASE_NAMESPACE=https://example.org/data/
```

### Why the Default is Dangerous in Production

`example.org` is a shared placeholder domain. If multiple SemPKM instances use the same namespace, their IRIs will collide — object `abc123` on your instance and object `abc123` on someone else's instance would have identical IRIs. This causes real problems during:

- **Data federation** — querying across instances returns ambiguous results because the same IRI refers to different objects on different instances
- **Data migration** — importing an N-Quads export from one instance into another silently merges or overwrites objects that share IRIs
- **Linked Data interoperability** — IRIs are meant to be globally unique identifiers; reusing `example.org` violates this contract

### Setting BASE_NAMESPACE Correctly

Choose a namespace rooted in a domain you control:

```
BASE_NAMESPACE=https://yourdomain.com/data/
```

The value must:
- End with a trailing slash (`/`)
- Be a valid IRI prefix (use `https://`)
- Be unique to this SemPKM instance

> **Warning:** Set `BASE_NAMESPACE` **before creating any data**. Every object and event graph IRI is minted using this prefix. Changing it after data exists does not rename existing IRIs — those objects become orphaned (the application generates new IRIs with the new prefix while old data remains under the old one). If you must change it after the fact, you would need to rewrite all IRIs in the triplestore manually.

### Example Configuration

Add to your `.env` file or Docker Compose environment:

```
BASE_NAMESPACE=https://sempkm.example.com/data/
```

For organizations running multiple instances (e.g. staging and production), use distinct namespaces:

```
# Production
BASE_NAMESPACE=https://knowledge.acme.com/data/

# Staging
BASE_NAMESPACE=https://knowledge-staging.acme.com/data/
```

## Production Checklist

Before going live, verify each item:

- [ ] `SECRET_KEY` set as a persistent environment variable (not auto-generated)
- [ ] `BASE_NAMESPACE` set to your domain (not the default `example.org`)
- [ ] SMTP configured for magic link email delivery
- [ ] Reverse proxy with TLS termination in front of SemPKM
- [ ] Ports 3000 and 8001 bound to `127.0.0.1` (not exposed to the internet)
- [ ] `JAVA_OPTS` set appropriately for expected triplestore data volume
- [ ] `DATABASE_URL` pointing to PostgreSQL (for multi-user deployments)
- [ ] Alembic migrations run after any version upgrade
- [ ] Automated backup schedule for both RDF4J volume and SQL database
- [ ] Monitoring for container health (`docker compose ps`, healthcheck endpoints)
- [ ] Log aggregation configured for the API container

---

**Previous:** [Chapter 19: Creating Mental Models](19-creating-mental-models.md) | **Next:** [Chapter 21: SPARQL Console](21-sparql-console.md)

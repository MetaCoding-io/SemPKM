# Appendix A: Environment Variable Reference

This appendix lists every environment variable recognized by SemPKM, drawn directly from the application configuration in `backend/app/config.py`. All variables can be set in the `environment` section of `docker-compose.yml`, in a `.env` file, or as shell environment variables.

## Complete Variable Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TRIPLESTORE_URL` | URL of the RDF4J triplestore server. The API connects to this endpoint for all SPARQL operations. | `http://triplestore:8080/rdf4j-server` | No |
| `REPOSITORY_ID` | Name of the RDF4J repository to use. Created automatically on first run if it does not exist. | `sempkm` | No |
| `BASE_NAMESPACE` | Base IRI namespace for user-created objects. All minted object IRIs start with this prefix. | `https://example.org/data/` | No |
| `APP_VERSION` | Application version string, exposed via the `/api/health` endpoint. | `0.1.0` | No |
| `DATABASE_URL` | SQLAlchemy-compatible connection string for the authentication and metadata database. Use `sqlite+aiosqlite:///` for SQLite or `postgresql+asyncpg://` for PostgreSQL. | `sqlite+aiosqlite:///./data/sempkm.db` | No |
| `SECRET_KEY` | Secret key for signing session cookies and authentication tokens. If empty, a random key is auto-generated on first run and saved to `SECRET_KEY_PATH`. | (empty -- auto-generated) | Recommended for production |
| `SECRET_KEY_PATH` | File path where the auto-generated secret key is stored. Only used when `SECRET_KEY` is not set. | `./data/.secret-key` | No |
| `SETUP_TOKEN_PATH` | File path where the first-run setup token is written. The owner checks this file (or the API logs) to retrieve the token during initial setup. | `./data/.setup-token` | No |
| `SESSION_DURATION_DAYS` | Number of days a session cookie remains valid before requiring re-authentication. | `30` | No |
| `SMTP_HOST` | SMTP server hostname for sending magic link emails and invitation emails. When empty, email sending is disabled and tokens are shown in the browser or API logs instead. | (empty -- disabled) | For multi-user deployments |
| `SMTP_PORT` | SMTP server port. Common values: 587 (STARTTLS), 465 (SSL), 25 (unencrypted). | `587` | No |
| `SMTP_USER` | Username for SMTP authentication. | (empty) | When SMTP is enabled |
| `SMTP_PASSWORD` | Password for SMTP authentication. | (empty) | When SMTP is enabled |
| `SMTP_FROM_EMAIL` | The "From" email address used in outgoing emails (magic links, invitations). | (empty) | When SMTP is enabled |
| `APP_BASE_URL` | Public base URL for the application (e.g., `https://app.example.com`). Used to generate WebID profile URIs and email links. When empty, derived from incoming request headers. | (empty -- derived from request) | For WebID / IndieAuth |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins (e.g., `https://app.example.com,https://admin.example.com`). When empty, defaults to wildcard (no credentials). | (empty -- wildcard) | No |
| `COOKIE_SECURE` | Whether session cookies require HTTPS. Set to `false` for local HTTP development. Must be `true` in production behind HTTPS. | `true` | No |
| `POSTHOG_ENABLED` | Enable PostHog analytics and error monitoring. Set to `true` for cloud deployments; leave `false` for self-hosted. | `false` | No |
| `POSTHOG_API_KEY` | PostHog project API key. Required when `POSTHOG_ENABLED` is `true`. | (empty) | When PostHog is enabled |
| `POSTHOG_HOST` | PostHog ingestion endpoint URL. | `https://us.i.posthog.com` | No |
| `DEBUG` | Enable debug mode. When `true`, produces verbose logging and enables development-only features. Do not enable in production. | `false` | No |

## Docker Compose Variables

The following variables are used by `docker-compose.yml` to configure the triplestore container, but are not part of the Python application settings:

| Variable | Description | Default | Service |
|----------|-------------|---------|---------|
| `JAVA_OPTS` | JVM options for the RDF4J triplestore. Controls heap memory allocation. | `-Xmx1g` | `triplestore` |

## Configuration Precedence

SemPKM uses Pydantic Settings for configuration loading. Values are resolved in this order (highest priority first):

1. **Shell environment variables** -- set directly in the container environment
2. **Docker Compose `environment` section** -- defined in `docker-compose.yml`
3. **`.env` file** -- loaded automatically if present in the working directory
4. **Default values** -- hardcoded in `config.py`

## Examples

### Minimal Production Configuration

```env
SECRET_KEY=your-64-char-random-string
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=sempkm@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=sempkm@example.com
```

### PostgreSQL with Custom Namespace

```env
DATABASE_URL=postgresql+asyncpg://sempkm:password@db:5432/sempkm
BASE_NAMESPACE=https://knowledge.example.com/data/
SECRET_KEY=your-64-char-random-string
```

### Extended Session Duration

```env
SESSION_DURATION_DAYS=90
```

## See Also

- [Production Deployment](20-production-deployment.md) -- full deployment guide
- [Installation and Setup](03-installation-and-setup.md) -- first-run configuration

---

**Previous:** [Chapter 26: IndieAuth](26-indieauth.md) | **Next:** [Appendix B: Keyboard Shortcut Reference](appendix-b-keyboard-shortcuts.md)

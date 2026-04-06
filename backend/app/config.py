"""Application configuration using Pydantic BaseSettings.

Config loading priority (highest wins):
1. Explicit environment variables (BASE_NAMESPACE=... in .env or shell)
2. Instance config file (data/.instance-config.json)
3. Pydantic defaults defined below
"""

import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_config_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """SemPKM application settings.

    Values are loaded from environment variables, with fallback to defaults.
    In Docker Compose, these are set via the `environment` section.
    """

    triplestore_url: str = "http://triplestore:8080/rdf4j-server"
    repository_id: str = "sempkm"
    base_namespace: str = "https://example.org/data/"
    app_version: str = "2.6.0"

    # SQL database (SQLite for local, PostgreSQL for cloud)
    database_url: str = "sqlite+aiosqlite:///./data/sempkm.db"

    # Security - empty means auto-generate on first run
    secret_key: str = ""
    secret_key_path: str = "./data/.secret-key"
    setup_token_path: str = "./data/.setup-token"

    # Session configuration
    session_duration_days: int = 30

    # SMTP (optional - only needed for invitations and magic links)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    # Application base URL for email links (e.g., https://app.example.com)
    # Empty = derive from request headers
    app_base_url: str = ""

    # CORS: comma-separated allowed origins; empty string means wildcard (no credentials)
    # Example: CORS_ORIGINS=https://app.example.com,https://admin.example.com
    cors_origins: str = ""

    # Session cookie secure flag — set COOKIE_SECURE=false for local HTTP development
    cookie_secure: bool = True

    # Debug mode
    debug: bool = False

    # Demo mode — when True, all auth dependencies return a synthetic
    # read-only guest user without checking session/cookie/DB.
    # Set DEMO_MODE=true in env for the hosted demo instance.
    demo_mode: bool = False

    # Federation — comma-separated list of allowed external SPARQL endpoints
    # Empty string means no endpoints are allowed (secure default).
    # Example: FEDERATION_ALLOWED_ENDPOINTS=https://query.wikidata.org/sparql,https://dbpedia.org/sparql
    federation_allowed_endpoints: str = ""

    def get_allowed_endpoints(self) -> list[str]:
        """Parse the comma-separated allowlist into a list of stripped URLs."""
        if not self.federation_allowed_endpoints.strip():
            return []
        return [
            ep.strip()
            for ep in self.federation_allowed_endpoints.split(",")
            if ep.strip()
        ]

    # Rate limiting — disable for E2E test environments
    rate_limit_enabled: bool = True

    # Firebase Cloud Messaging — path to service account JSON.
    # Empty string means FCM is disabled (no-op mode).
    firebase_credentials_path: str = ""

    # Marketplace — remote model registry
    # Empty URL means marketplace is disabled.
    marketplace_registry_url: str = ""
    marketplace_models_dir: str = "/app/data/models"

    # PostHog analytics and error monitoring
    # Set posthog_enabled=True for cloud deployments; leave False for self-hosted
    posthog_enabled: bool = False
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"

    # OpenTelemetry tracing (optional — app works without Jaeger)
    otel_enabled: bool = False
    otel_exporter_endpoint: str = "http://jaeger:4318/v1/traces"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

# ── HTTP timeout defaults (seconds) ────────────────────────────────────────
# Centralised constants — import these instead of hardcoding timeout values.
# Override per call-site only when a specific endpoint needs different timing.

TIMEOUT_DEFAULT = 30.0       # General-purpose HTTP calls, triplestore, SSE queues
TIMEOUT_SHORT = 5.0          # Webhooks, IndieAuth, quick external checks
TIMEOUT_FEDERATION = 15.0    # Federation HTTP signatures, WebFinger, remote fetch
TIMEOUT_LLM = 300.0          # LLM streaming (large model responses)
TIMEOUT_LLM_SHORT = 60.0    # LLM non-streaming (embeddings, single-shot)


def _apply_instance_config_overrides() -> None:
    """Apply instance config overrides to settings where env vars are absent.

    Priority: explicit env var > instance config > Pydantic default.
    Only ``base_namespace`` and ``app_base_url`` are overridable via
    instance config.
    """
    # Lazy import to avoid circular dependency (instance_config imports nothing
    # from config, but keeping the import local is defensive).
    from app.instance_config import load_instance_config

    ic = load_instance_config()
    if ic is None:
        _config_logger.info("base_namespace source: default = %s", settings.base_namespace)
        return

    # For each overridable field, check if the env var was explicitly set.
    # If it was, the env var wins. Otherwise, the instance config wins.
    for field_name in ("base_namespace", "app_base_url"):
        env_key = field_name.upper()  # BASE_NAMESPACE, APP_BASE_URL
        env_value = os.environ.get(env_key)
        if env_value is not None:
            source = "env"
            value = env_value
        else:
            source = "instance_config"
            value = getattr(ic, field_name)
            # Pydantic Settings objects are mutable — direct assignment works.
            object.__setattr__(settings, field_name, value)

        _config_logger.info("%s source: %s = %s", field_name, source, value)


_apply_instance_config_overrides()

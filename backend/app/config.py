"""Application configuration using Pydantic BaseSettings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SemPKM application settings.

    Values are loaded from environment variables, with fallback to defaults.
    In Docker Compose, these are set via the `environment` section.
    """

    triplestore_url: str = "http://triplestore:8080/rdf4j-server"
    repository_id: str = "sempkm"
    base_namespace: str = "https://example.org/data/"
    app_version: str = "0.1.0"

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

    # Debug mode
    debug: bool = False

    # PostHog analytics and error monitoring
    # Set posthog_enabled=True for cloud deployments; leave False for self-hosted
    posthog_enabled: bool = False
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

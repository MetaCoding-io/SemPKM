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

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

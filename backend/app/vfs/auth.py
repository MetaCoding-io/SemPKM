"""wsgidav domain controller that validates API tokens via sync SQLAlchemy.

Provides Basic auth for WebDAV clients: username is the SemPKM email,
password is a revocable API token. The token is SHA-256 hashed and checked
against the api_tokens table using a synchronous SQLAlchemy session (required
because wsgidav runs in a WSGI thread pool, not on the async event loop).
"""

import hashlib

from wsgidav.dc.base_dc import BaseDomainController


class SemPKMWsgiAuthenticator(BaseDomainController):
    """wsgidav domain controller that validates API tokens via sync SQLAlchemy."""

    def __init__(self, wsgidav_app, config: dict) -> None:
        super().__init__(wsgidav_app, config)
        # Extract db_url from wsgidav config; strip async driver prefix
        db_url = config.get("sempkm_db_url", "")
        self._sync_db_url = db_url.replace("+aiosqlite", "")

    def get_domain_realm(self, path_info: str, environ: dict) -> str:
        return "SemPKM"

    def require_authentication(self, realm: str, environ: dict) -> bool:
        return True

    def is_share_anonymous(self, path_info: str) -> bool:
        return False

    def basic_auth_user(
        self, realm: str, user_name: str, password: str, environ: dict
    ) -> bool:
        """Validate username (email) + password (API token). Returns True if valid."""
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.auth.models import ApiToken, User

        token_hash = hashlib.sha256(password.encode()).hexdigest()
        engine = create_engine(self._sync_db_url)
        try:
            with Session(engine) as session:
                result = session.execute(
                    select(ApiToken)
                    .join(User)
                    .where(
                        User.email == user_name,
                        ApiToken.token_hash == token_hash,
                        ApiToken.revoked_at.is_(None),
                    )
                )
                token_row = result.scalar_one_or_none()
                if token_row:
                    # Store user info in environ for downstream use
                    environ["sempkm.user_email"] = user_name
                    return True
                return False
        finally:
            engine.dispose()

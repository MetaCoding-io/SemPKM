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

    def supports_http_digest_auth(self) -> bool:
        """We only support Basic auth, not Digest."""
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
                # Load both token and user in a single join query
                user_result = session.execute(
                    select(User).where(User.email == user_name)
                )
                user = user_result.scalar_one_or_none()
                if user is None:
                    return False
                token_result = session.execute(
                    select(ApiToken).where(
                        ApiToken.user_id == user.id,
                        ApiToken.token_hash == token_hash,
                        ApiToken.revoked_at.is_(None),
                    )
                )
                token_row = token_result.scalar_one_or_none()
                if token_row:
                    # Store user info in environ for downstream use by the DAV provider.
                    # user_id and user_role are consumed by ResourceFile.end_write()
                    # to record event provenance (who made the change and in what role).
                    environ["sempkm.user_id"] = str(user.id)
                    environ["sempkm.user_email"] = user.email
                    environ["sempkm.user_role"] = user.role  # "owner", "member", or "guest"
                    return True
                return False
        finally:
            engine.dispose()

"""LLM connection configuration service.

Stores LLM config instance-wide in InstanceConfig (not user_settings).
API key is encrypted at rest using Fernet symmetric encryption derived
from the application secret_key via PBKDF2.
"""
import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import InstanceConfig

# InstanceConfig keys for LLM configuration
LLM_API_BASE_URL_KEY = "llm.api_base_url"
LLM_API_KEY_KEY = "llm.api_key"
LLM_DEFAULT_MODEL_KEY = "llm.default_model"

# Fixed salt for Fernet key derivation (not secret — stability matters, not secrecy)
# Using a fixed salt is acceptable because secret_key is already high-entropy.
_LLM_KDF_SALT = b"sempkm-llm-config-v1"


def _get_fernet(secret_key: str) -> Fernet:
    """Derive a Fernet key from the application secret_key via PBKDF2."""
    if not secret_key:
        raise ValueError("secret_key is not set — cannot derive Fernet key for LLM config")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_LLM_KDF_SALT,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)


def encrypt_api_key(api_key: str, secret_key: str) -> str:
    """Encrypt an API key, returning a Fernet token string."""
    return _get_fernet(secret_key).encrypt(api_key.encode()).decode()


def decrypt_api_key(ciphertext: str, secret_key: str) -> str | None:
    """Decrypt a Fernet token. Returns None on failure."""
    try:
        return _get_fernet(secret_key).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return None


class LLMConfigService:
    """Manages LLM connection configuration stored in InstanceConfig.

    All three LLM config values (api_base_url, api_key, default_model) are
    stored as InstanceConfig rows — they are instance-wide, not per-user.
    The API key is stored as a Fernet-encrypted ciphertext.
    """

    async def get_config(self, db: AsyncSession) -> dict:
        """Return LLM config safe for display: api_key_set is bool, never the key value."""
        result = await db.execute(
            select(InstanceConfig).where(
                InstanceConfig.key.in_([
                    LLM_API_BASE_URL_KEY,
                    LLM_API_KEY_KEY,
                    LLM_DEFAULT_MODEL_KEY,
                ])
            )
        )
        rows = {row.key: row.value for row in result.scalars()}
        return {
            "api_base_url": rows.get(LLM_API_BASE_URL_KEY, ""),
            "api_key_set": bool(rows.get(LLM_API_KEY_KEY)),
            "default_model": rows.get(LLM_DEFAULT_MODEL_KEY, ""),
        }

    async def save_config(
        self,
        db: AsyncSession,
        api_base_url: str | None = None,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        """Upsert LLM config values. Pass None to skip updating a field.
        api_key is encrypted before storage. Empty string clears the value.
        """
        from app.config import settings as app_settings

        updates: list[tuple[str, str]] = []
        if api_base_url is not None:
            updates.append((LLM_API_BASE_URL_KEY, api_base_url))
        if api_key is not None:
            if api_key:
                encrypted = encrypt_api_key(api_key, app_settings.secret_key)
                updates.append((LLM_API_KEY_KEY, encrypted))
            # If api_key is empty string, skip (don't overwrite existing key with empty)
        if default_model is not None:
            updates.append((LLM_DEFAULT_MODEL_KEY, default_model))

        for key, value in updates:
            existing = await db.execute(
                select(InstanceConfig).where(InstanceConfig.key == key)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.value = value
            else:
                db.add(InstanceConfig(key=key, value=value))
        await db.commit()

    async def get_decrypted_api_key(self, db: AsyncSession) -> str | None:
        """Return the decrypted API key. Returns None if not set or decryption fails."""
        from app.config import settings as app_settings

        result = await db.execute(
            select(InstanceConfig).where(InstanceConfig.key == LLM_API_KEY_KEY)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return decrypt_api_key(row.value, app_settings.secret_key)

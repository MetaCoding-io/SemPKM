"""Shared helpers used across browser sub-router modules."""

from datetime import datetime
from urllib.parse import urlparse

from fastapi import Request

from app.services.icons import IconService
from app.services.settings import SettingsService


def _validate_iri(iri: str) -> bool:
    """Validate that a decoded IRI is an absolute URI before SPARQL interpolation.

    Accepts both https://... object IRIs and urn:sempkm:... model/seed IRIs.
    The Basic PKM model uses urn: scheme for all object and type IRIs
    (e.g. urn:sempkm:model:basic-pkm:Note, urn:sempkm:model:basic-pkm:seed-note-arch).

    Blocks SPARQL injection characters (>, <, ", whitespace) that would break
    the SPARQL template interpolation <{decoded_iri}>.
    """
    if not iri:
        return False
    try:
        result = urlparse(iri)
        if not result.scheme:
            return False
        # Reject characters that would break SPARQL angle-bracket quoting
        forbidden = set('<>"\\{}\n\r\t ')
        if any(c in forbidden for c in iri):
            return False
        # https/http IRIs must have a netloc (host)
        if result.scheme in ("http", "https"):
            return bool(result.netloc)
        # urn: IRIs are opaque (no netloc) but valid semantic web IRIs
        if result.scheme == "urn":
            return bool(result.path)
        # Reject unknown schemes
        return False
    except Exception:
        return False


# Models directory path -- mirrors the Docker mount used in main.py
_MODELS_DIR = "/app/models"


def get_settings_service() -> SettingsService:
    """FastAPI dependency that returns a SettingsService with the models directory."""
    return SettingsService(installed_models_dir=_MODELS_DIR)


<<<<<<< HEAD
def get_icon_service(request: Request) -> IconService:
    """FastAPI dependency that returns an IconService with the models directory.

    Also injects user-type icon overrides from app.state.user_type_icons
    (populated by the create-class endpoint) so that user-created types
    show correct icons in the TBox tree, workspace, and type pickers.
    """
    svc = IconService(models_dir=_MODELS_DIR)
    user_icons = getattr(request.app.state, "user_type_icons", None)
    if user_icons:
        svc.set_user_type_icons(user_icons)
    return svc
=======
def get_icon_service() -> IconService:
    """FastAPI dependency that returns an IconService with the models directory."""
    return IconService(models_dir=_MODELS_DIR)
>>>>>>> gsd/M002/S04


def _format_date(value: str) -> str:
    """Format ISO date string to human-readable: 'Feb 23, 2026'."""
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(value)


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"

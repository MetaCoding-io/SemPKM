"""WebID profile management API endpoints.

Handles username setup, key generation, link management, and publish toggling.
All endpoints require authentication via session cookie.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings
from app.db.session import get_db_session
from app.webid.schemas import RelMeLinksUpdate, UsernameSetup, WebIDProfileResponse
from app.webid.service import (
    build_webid_uri,
    encrypt_private_key,
    generate_ed25519_keypair,
    get_base_url,
    key_fingerprint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webid", tags=["webid"])


def _build_profile_response(user: User, base_url: str) -> WebIDProfileResponse:
    """Build a WebIDProfileResponse from a User model."""
    links: list[str] = []
    if user.webid_links:
        try:
            links = json.loads(user.webid_links)
        except (json.JSONDecodeError, TypeError):
            links = []

    return WebIDProfileResponse(
        username=user.username,
        webid_uri=build_webid_uri(user.username, base_url) if user.username else None,
        published=bool(user.webid_published),
        public_key_fingerprint=key_fingerprint(user.public_key_pem) if user.public_key_pem else None,
        public_key_pem=user.public_key_pem,
        links=links,
    )


@router.get("/profile", response_model=WebIDProfileResponse)
async def get_profile(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Return current user's WebID profile data."""
    base_url = get_base_url(request)
    return _build_profile_response(user, base_url)


@router.post("/username", response_model=WebIDProfileResponse)
async def set_username(
    request: Request,
    body: UsernameSetup,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Claim a WebID username. Generates an Ed25519 key pair.

    Username is immutable after creation. Returns 400 if user already has one,
    409 if the username is already taken.
    """
    if user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already set and cannot be changed",
        )

    # Generate key pair
    public_pem, private_pem = generate_ed25519_keypair()
    encrypted_private = encrypt_private_key(private_pem, settings.secret_key)

    user.username = body.username
    user.public_key_pem = public_pem
    user.private_key_encrypted = encrypted_private
    user.webid_published = False

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken",
        )

    base_url = get_base_url(request)
    logger.info("User %s claimed username '%s'", user.id, body.username)
    return _build_profile_response(user, base_url)


@router.put("/links", response_model=WebIDProfileResponse)
async def update_links(
    request: Request,
    body: RelMeLinksUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update the user's rel='me' links."""
    user.webid_links = json.dumps([str(link) for link in body.links])
    await db.commit()
    await db.refresh(user)
    base_url = get_base_url(request)
    return _build_profile_response(user, base_url)


@router.post("/publish", response_model=WebIDProfileResponse)
async def publish_profile(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Publish the user's WebID profile (make it publicly accessible)."""
    if not user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set a username before publishing",
        )
    user.webid_published = True
    await db.commit()
    await db.refresh(user)
    base_url = get_base_url(request)
    return _build_profile_response(user, base_url)


@router.post("/unpublish", response_model=WebIDProfileResponse)
async def unpublish_profile(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Unpublish the user's WebID profile (returns 404 to public)."""
    user.webid_published = False
    await db.commit()
    await db.refresh(user)
    base_url = get_base_url(request)
    return _build_profile_response(user, base_url)


@router.post("/regenerate-key", response_model=WebIDProfileResponse)
async def regenerate_key(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Regenerate the user's Ed25519 key pair. Requires existing username."""
    if not user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set a username before regenerating keys",
        )

    public_pem, private_pem = generate_ed25519_keypair()
    encrypted_private = encrypt_private_key(private_pem, settings.secret_key)

    user.public_key_pem = public_pem
    user.private_key_encrypted = encrypted_private
    await db.commit()
    await db.refresh(user)

    base_url = get_base_url(request)
    logger.info("User %s regenerated WebID key pair", user.id)
    return _build_profile_response(user, base_url)

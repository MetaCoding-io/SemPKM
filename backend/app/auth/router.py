"""Auth endpoints: setup, magic-link, verify, logout, me, status.

Cookie settings:
- httponly=True (not accessible from JavaScript)
- samesite="lax" (sent with same-site and top-level navigation)
- secure=settings.cookie_secure (True by default; set COOKIE_SECURE=false for local HTTP dev)
- max_age based on settings.session_duration_days
- key name: "sempkm_session"
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.dependencies import get_current_user, get_session_token, require_role
from app.auth.models import User
from app.auth.schemas import (
    AuthResponse,
    InviteRequest,
    InviteResponse,
    LogoutResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    SetupRequest,
    SetupResponse,
    StatusResponse,
    VerifyTokenRequest,
)
from app.auth.service import AuthService
from app.auth.tokens import create_magic_link_token, delete_setup_token, verify_magic_link_token
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_MAX_AGE = settings.session_duration_days * 86400


def _set_session_cookie(response: Response, token: str) -> None:
    """Set the httpOnly session cookie on a response."""
    response.set_cookie(
        key="sempkm_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=COOKIE_MAX_AGE,
    )


def _get_auth_service(request: Request) -> AuthService:
    """Get AuthService from app state."""
    return request.app.state.auth_service


@router.get("/status", response_model=StatusResponse)
async def auth_status(request: Request):
    """Public endpoint: whether setup is complete and setup_mode is active."""
    auth_service = _get_auth_service(request)
    setup_complete = await auth_service.is_setup_complete()
    setup_mode = getattr(request.app.state, "setup_mode", False)
    return StatusResponse(setup_complete=setup_complete, setup_mode=setup_mode)


@router.post("/setup", response_model=SetupResponse)
async def setup(
    body: SetupRequest,
    request: Request,
    response: Response,
):
    """Claim the instance with the setup token.

    Creates the owner user, creates a session, sets the httpOnly cookie,
    deletes the setup token file, and disables setup mode.
    """
    # Verify setup mode is active
    if not getattr(request.app.state, "setup_mode", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed",
        )

    # Verify setup token matches
    expected_token = getattr(request.app.state, "setup_token", None)
    if expected_token is None or body.token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid setup token",
        )

    auth_service = _get_auth_service(request)

    # Create owner user
    email = body.email or "owner@local"
    try:
        user = await auth_service.create_owner(email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Create session
    session = await auth_service.create_session(user)
    _set_session_cookie(response, session.token)

    # Disable setup mode
    delete_setup_token()
    request.app.state.setup_mode = False
    request.app.state.setup_token = None

    logger.info("Instance setup complete. Owner: %s", email)
    return SetupResponse(message="Setup complete", user_id=str(user.id))


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(body: MagicLinkRequest, request: Request):
    """Request a magic link login email.

    When SMTP is configured, sends the token via email and returns a
    generic message. When SMTP is not configured (local instances),
    returns the token directly in the response and logs it to the terminal.
    """
    token = create_magic_link_token(body.email)
    smtp_configured = bool(settings.smtp_host)

    # Always log to terminal for local development
    logger.info("Magic link token for %s: %s", body.email, token)

    if smtp_configured:
        # TODO: send email with token via SMTP
        return MagicLinkResponse(
            message="If this email is registered, a login link has been sent."
        )

    # No SMTP — return token directly for local instances
    return MagicLinkResponse(
        message="No email configured. Use the token below to log in.",
        token=token,
    )


@router.post("/verify", response_model=AuthResponse)
async def verify_token(
    body: VerifyTokenRequest,
    request: Request,
    response: Response,
):
    """Verify a magic link token and create a session.

    If the user doesn't exist yet (first magic link login), creates them
    as a member.
    """
    email = verify_magic_link_token(body.token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    auth_service = _get_auth_service(request)

    # Get or create user
    user = await auth_service.get_user_by_email(email)
    if user is None:
        user = await auth_service.create_user(email, "member")

    # Create session
    session = await auth_service.create_session(user)
    _set_session_cookie(response, session.token)

    return AuthResponse(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        display_name=user.display_name,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    token: str = Depends(get_session_token),
    current_user: User = Depends(get_current_user),
):
    """Logout: revoke the current session and clear the cookie."""
    auth_service = _get_auth_service(request)
    await auth_service.revoke_session(token)
    response.delete_cookie(key="sempkm_session")
    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=AuthResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's info."""
    return AuthResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        display_name=current_user.display_name,
    )


@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    body: InviteRequest,
    request: Request,
    current_user: User = Depends(require_role("owner")),
):
    """Invite a user to the instance. Owner only."""
    auth_service = _get_auth_service(request)
    invitation = await auth_service.create_invitation(
        email=body.email,
        role=body.role,
        invited_by=current_user.id,
    )
    return InviteResponse(
        message=f"Invitation sent to {body.email}",
        invitation_id=str(invitation.id),
    )

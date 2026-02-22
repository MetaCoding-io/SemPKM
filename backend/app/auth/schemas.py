"""Pydantic request/response models for auth endpoints."""

from pydantic import BaseModel, EmailStr, field_validator


class SetupRequest(BaseModel):
    """Request to claim an instance with the setup token."""

    token: str
    email: str | None = None  # Optional; defaults to "owner@local" if not provided


class SetupResponse(BaseModel):
    """Response after successful setup."""

    message: str
    user_id: str


class MagicLinkRequest(BaseModel):
    """Request to send a magic link login email.

    Uses plain str instead of EmailStr to support local addresses
    like owner@local that don't have a valid TLD.
    """

    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Require at least user@domain format."""
        v = v.strip()
        if "@" not in v or len(v) < 3:
            msg = "Must be a valid email address"
            raise ValueError(msg)
        return v


class MagicLinkResponse(BaseModel):
    """Response after magic link request (always generic for security).

    When SMTP is not configured (local instances), the token is returned
    directly so the user can log in without email.
    """

    message: str
    token: str | None = None


class VerifyTokenRequest(BaseModel):
    """Request to verify a magic link or invitation token."""

    token: str


class AuthResponse(BaseModel):
    """Response with authenticated user info."""

    user_id: str
    email: str
    role: str
    display_name: str | None = None


class LogoutResponse(BaseModel):
    """Response after logout."""

    message: str


class InviteRequest(BaseModel):
    """Request to invite a user to the instance."""

    email: EmailStr
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Only member and guest roles can be invited."""
        if v not in ("member", "guest"):
            msg = "Role must be 'member' or 'guest'"
            raise ValueError(msg)
        return v


class InviteResponse(BaseModel):
    """Response after creating an invitation."""

    message: str
    invitation_id: str


class StatusResponse(BaseModel):
    """Response for auth status check."""

    setup_complete: bool
    setup_mode: bool

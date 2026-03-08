"""Pydantic schemas for WebID profile management."""

import re

from pydantic import BaseModel, HttpUrl, field_validator


class UsernameSetup(BaseModel):
    """Request body for claiming a WebID username."""

    username: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3 or len(v) > 63:
            raise ValueError("Username must be 3-63 characters")
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) and len(v) >= 3:
            raise ValueError(
                "Username must be lowercase alphanumeric with hyphens, "
                "and start/end with an alphanumeric character"
            )
        if "--" in v:
            raise ValueError("Username must not contain consecutive hyphens")
        return v


class RelMeLink(BaseModel):
    """A single rel='me' link."""

    url: HttpUrl


class RelMeLinksUpdate(BaseModel):
    """Request body for updating rel='me' links."""

    links: list[HttpUrl]


class WebIDProfileResponse(BaseModel):
    """Response for WebID profile data."""

    username: str | None = None
    webid_uri: str | None = None
    published: bool = False
    public_key_fingerprint: str | None = None
    public_key_pem: str | None = None
    links: list[str] = []

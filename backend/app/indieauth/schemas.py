"""Pydantic schemas for IndieAuth token and introspection responses."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """OAuth2 token response per IndieAuth spec."""

    access_token: str
    token_type: str = "Bearer"
    scope: str
    me: str
    expires_in: int
    refresh_token: str | None = None


class IntrospectionResponse(BaseModel):
    """OAuth2 Token Introspection response (RFC 7662)."""

    active: bool
    me: str | None = None
    client_id: str | None = None
    scope: str | None = None
    exp: int | None = None
    iat: int | None = None


class ClientInfo(BaseModel):
    """Client application metadata fetched from client_id URL."""

    name: str
    url: str
    logo: str | None = None

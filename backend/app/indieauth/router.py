"""IndieAuth HTTP endpoints: authorization, token, introspection, metadata."""

import logging
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, optional_current_user
from app.auth.models import User
from app.db.session import get_db_session
from app.indieauth.schemas import IntrospectionResponse, TokenResponse
from app.indieauth.scopes import SCOPE_REGISTRY, validate_scopes
from app.indieauth.service import IndieAuthService
from app.webid.service import build_profile_url, get_base_url

logger = logging.getLogger(__name__)

# Auth-protected endpoints
router = APIRouter(prefix="/api/indieauth", tags=["indieauth"])

# Public endpoints (no auth required)
public_router = APIRouter(tags=["indieauth"])


# ── Metadata ─────────────────────────────────────────────────────────


@public_router.get("/api/indieauth/metadata")
async def metadata(request: Request) -> JSONResponse:
    """IndieAuth server metadata (Section 4.1)."""
    base = get_base_url(request)
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/api/indieauth/authorize",
            "token_endpoint": f"{base}/api/indieauth/token",
            "introspection_endpoint": f"{base}/api/indieauth/introspect",
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": list(SCOPE_REGISTRY.keys()),
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "introspection_endpoint_auth_methods_supported": ["none"],
            "authorization_response_iss_parameter_supported": True,
        }
    )


@public_router.get("/.well-known/oauth-authorization-server")
async def well_known_oauth(request: Request):
    """Redirect to metadata endpoint per RFC 8414."""
    base = get_base_url(request)
    return RedirectResponse(
        url=f"{base}/api/indieauth/metadata", status_code=307
    )


# ── Authorization ────────────────────────────────────────────────────


@router.get("/authorize")
async def authorize_get(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(...),
    scope: str = Query("profile"),
    user: User | None = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Show consent screen (or redirect to login if unauthenticated)."""
    # If not logged in, redirect to login with return URL
    if user is None:
        next_url = str(request.url)
        return RedirectResponse(
            url=f"/login.html?next={next_url}", status_code=302
        )

    # Validate params
    if response_type != "code":
        return JSONResponse(
            {"error": "unsupported_response_type", "error_description": "Only response_type=code is supported"},
            status_code=400,
        )
    if code_challenge_method != "S256":
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Only code_challenge_method=S256 is supported"},
            status_code=400,
        )
    if not IndieAuthService.validate_client_id(client_id):
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Invalid client_id URL"},
            status_code=400,
        )

    # Fetch client info and validate scopes
    client_info = await IndieAuthService.fetch_client_info(client_id)
    valid_scopes = validate_scopes(scope)

    # Build scope detail list for template
    scope_details = []
    for s in valid_scopes:
        info = SCOPE_REGISTRY.get(s, {})
        scope_details.append(
            {"name": s, "description": info.get("description", s), "detail": info.get("claims", "")}
        )

    base_url = get_base_url(request)
    profile_url = build_profile_url(user.username, base_url)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "indieauth/consent.html",
        {
            "request": request,
            "client_info": client_info,
            "scopes": scope_details,
            "user": user,
            "profile_url": profile_url,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "scope": " ".join(valid_scopes) if valid_scopes else scope,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "state": state,
        },
    )


@router.post("/authorize")
async def authorize_post(
    request: Request,
    action: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form("profile"),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    state: str = Form(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Process consent form: approve or deny."""
    base_url = get_base_url(request)
    issuer = base_url  # iss parameter per spec

    if action == "deny":
        params = urlencode({"error": "access_denied", "state": state})
        return RedirectResponse(url=f"{redirect_uri}?{params}", status_code=302)

    # Approve: create authorization code
    svc = IndieAuthService(db)
    code = await svc.create_authorization_code(
        user_id=user.id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        state=state,
    )
    await db.commit()

    params = urlencode({"code": code, "state": state, "iss": issuer})
    return RedirectResponse(url=f"{redirect_uri}?{params}", status_code=302)


# ── Token ────────────────────────────────────────────────────────────


@public_router.post("/api/indieauth/token")
async def token_endpoint(
    request: Request,
    grant_type: str = Form(...),
    code: str | None = Form(None),
    client_id: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    code_verifier: str | None = Form(None),
    refresh_token: str | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Exchange authorization code or refresh token for access token."""
    base_url = get_base_url(request)
    svc = IndieAuthService(db)

    try:
        if grant_type == "authorization_code":
            if not all([code, client_id, redirect_uri, code_verifier]):
                return JSONResponse(
                    {"error": "invalid_request", "error_description": "Missing required parameters"},
                    status_code=400,
                )
            token_row, access_token, refresh_tok = await svc.exchange_code(
                code=code,
                client_id=client_id,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
            )
        elif grant_type == "refresh_token":
            if not refresh_token:
                return JSONResponse(
                    {"error": "invalid_request", "error_description": "Missing refresh_token"},
                    status_code=400,
                )
            token_row, access_token, refresh_tok = await svc.refresh_access_token(refresh_token)
        else:
            return JSONResponse(
                {"error": "unsupported_grant_type", "error_description": f"Unsupported grant_type: {grant_type}"},
                status_code=400,
            )

        await db.commit()

        # Build me URL from user
        from app.auth.models import User as UserModel
        from sqlalchemy import select

        user_result = await db.execute(
            select(UserModel).where(UserModel.id == token_row.user_id)
        )
        user = user_result.scalar_one_or_none()
        me = build_profile_url(user.username, base_url) if user else ""

        from datetime import datetime, timezone

        expires_in = int(
            (token_row.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
        )

        return JSONResponse(
            TokenResponse(
                access_token=access_token,
                token_type="Bearer",
                scope=token_row.scope,
                me=me,
                expires_in=expires_in,
                refresh_token=refresh_tok,
            ).model_dump()
        )

    except ValueError as exc:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": str(exc)},
            status_code=400,
        )


# ── Introspection ────────────────────────────────────────────────────


@public_router.post("/api/indieauth/introspect")
async def introspect_endpoint(
    request: Request,
    token: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Introspect an access token (RFC 7662). Always returns 200."""
    svc = IndieAuthService(db)
    result = await svc.introspect_token(token)
    return JSONResponse(result.model_dump())


# ── Token management (authenticated) ────────────────────────────────


@router.get("/tokens")
async def list_tokens(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List authorized apps for current user."""
    svc = IndieAuthService(db)
    tokens = await svc.list_authorized_apps(user.id)
    return [
        {
            "id": str(t.id),
            "client_id": t.client_id,
            "client_name": t.client_name,
            "scope": t.scope,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        }
        for t in tokens
    ]


@router.get("/tokens/list")
async def list_tokens_html(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return authorized apps as an HTML partial for htmx."""
    svc = IndieAuthService(db)
    tokens = await svc.list_authorized_apps(user.id)
    token_list = [
        {
            "id": str(t.id),
            "client_id": t.client_id,
            "client_name": t.client_name,
            "scope": t.scope,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        }
        for t in tokens
    ]
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "indieauth/_token_list.html",
        {"tokens": token_list},
    )


@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke a specific token by ID."""
    from sqlalchemy import select
    from app.indieauth.models import IndieAuthToken

    result = await db.execute(
        select(IndieAuthToken).where(
            IndieAuthToken.id == token_id,
            IndieAuthToken.user_id == user.id,
        )
    )
    token_row = result.scalar_one_or_none()
    if token_row is None:
        raise HTTPException(status_code=404, detail="Token not found")

    await db.delete(token_row)
    await db.commit()

    # Return refreshed HTML list for htmx swap
    svc = IndieAuthService(db)
    tokens = await svc.list_authorized_apps(user.id)
    token_list = [
        {
            "id": str(t.id),
            "client_id": t.client_id,
            "client_name": t.client_name,
            "scope": t.scope,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        }
        for t in tokens
    ]
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "indieauth/_token_list.html",
        {"tokens": token_list},
    )

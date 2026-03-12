"""WebFinger server endpoint and client discovery (RFC 7033).

Exposes /.well-known/webfinger for resolving user@domain handles to WebID
URLs. Also provides a client function for discovering remote WebIDs.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.db.session import get_db_session
from app.webid.service import build_profile_url, build_webid_uri, get_base_url

logger = logging.getLogger(__name__)

# Public router for /.well-known/webfinger -- no auth required
webfinger_router = APIRouter(tags=["webfinger"])


@webfinger_router.get("/.well-known/webfinger")
async def webfinger_endpoint(
    request: Request,
    resource: str = Query(..., description="Resource URI (acct: or http(s):)"),
    rel: list[str] = Query(default=[], description="Filter links by rel type"),
    db: AsyncSession = Depends(get_db_session),
):
    """WebFinger discovery endpoint per RFC 7033.

    Resolves acct:user@domain URIs and http(s) WebID URLs to JRD
    (JSON Resource Descriptor) responses containing WebID profile
    links, inbox URL, and aliases.

    Returns 404 if the user does not exist or has not published their profile.
    Returns 400 for unsupported resource URI schemes.
    """
    # Parse resource to extract username
    if resource.startswith("acct:"):
        # Format: acct:username@domain
        user_host = resource[5:]
        username = user_host.split("@")[0]
    elif resource.startswith("http://") or resource.startswith("https://"):
        # Format: https://domain/users/username#me or https://domain/users/username
        path = resource.split("?")[0].split("#")[0]
        username = path.rsplit("/", 1)[-1]
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported resource URI scheme. Use acct: or http(s): URI.",
        )

    # Look up user by username
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user or not user.webid_published:
        raise HTTPException(status_code=404, detail="Resource not found")

    base_url = get_base_url(request)
    webid_uri = build_webid_uri(username, base_url)
    profile_url = build_profile_url(username, base_url)

    # Build JRD response
    links = [
        {
            "rel": "self",
            "type": "text/turtle",
            "href": profile_url,
        },
        {
            "rel": "http://www.w3.org/ns/ldp#inbox",
            "href": f"{base_url}/api/inbox",
        },
    ]

    # Filter by rel if specified
    if rel:
        links = [link for link in links if link["rel"] in rel]

    jrd = {
        "subject": resource,
        "aliases": [webid_uri, profile_url],
        "links": links,
    }

    return JSONResponse(content=jrd, media_type="application/jrd+json")


async def discover_webid(handle_or_url: str) -> dict:
    """Discover a remote WebID from a handle or URL.

    Args:
        handle_or_url: Either a WebFinger handle (user@domain) or a WebID URL

    Returns:
        Dict with keys: webid, inbox (optional), profile (optional)
    """
    if handle_or_url.startswith("http://") or handle_or_url.startswith("https://"):
        # Already a WebID URL
        return {"webid": handle_or_url}

    # Treat as WebFinger handle: user@domain
    if "@" not in handle_or_url:
        raise ValueError(f"Invalid handle format: {handle_or_url}")

    parts = handle_or_url.split("@", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid handle format: {handle_or_url}")

    user, domain = parts
    resource = f"acct:{handle_or_url}"
    webfinger_url = f"https://{domain}/.well-known/webfinger"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                webfinger_url,
                params={"resource": resource},
                headers={"Accept": "application/jrd+json"},
            )
            resp.raise_for_status()
            jrd = resp.json()
    except Exception as e:
        logger.warning("WebFinger discovery failed for %s: %s", handle_or_url, e)
        raise ValueError(f"WebFinger discovery failed: {e}")

    result: dict = {}

    # Extract WebID and inbox from links
    for link in jrd.get("links", []):
        link_rel = link.get("rel", "")
        href = link.get("href", "")
        if link_rel == "self":
            result["profile"] = href
        elif link_rel == "http://www.w3.org/ns/ldp#inbox":
            result["inbox"] = href

    # Extract WebID from aliases (the #me URI)
    for alias in jrd.get("aliases", []):
        if "#me" in alias:
            result["webid"] = alias
            break

    # Fallback: use profile URL as WebID reference
    if "webid" not in result and "profile" in result:
        result["webid"] = result["profile"] + "#me"

    return result

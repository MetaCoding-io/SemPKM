"""Shell router serving dashboard pages via Jinja2 templates.

Serves the top-level navigation pages: dashboard, admin, health.
Each endpoint checks for the HX-Request header to decide between full page
rendering and htmx partial block rendering.

Note: /browser/ is now served by app.browser.router (plan 04-04).
"""

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.config import settings

router = APIRouter()


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    """Render the dashboard home page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "dashboard.html", {"active_page": "home", "user": user}
    )


@router.get("/shortcuts")
async def shortcuts_page(request: Request, user: User = Depends(get_current_user)):
    """Render the keyboard shortcuts reference page."""
    templates = request.app.state.templates
    context = {"active_page": "shortcuts", "user": user}
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "shortcuts.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "shortcuts.html", context)


@router.get("/health/")
async def health_page(request: Request, user: User = Depends(get_current_user)):
    """Render the health check page.

    Full page for direct navigation, content block only for htmx partial swap.
    """
    templates = request.app.state.templates
    smtp_configured = bool(settings.smtp_host)
    # Parse database type and path from URL
    db_url = settings.database_url
    if "://" in db_url:
        db_scheme, db_path = db_url.split("://", 1)
    else:
        db_scheme, db_path = db_url, ""
    # Friendly engine name
    if "sqlite" in db_scheme:
        db_engine = "SQLite"
    elif "postgres" in db_scheme:
        db_engine = "PostgreSQL"
    else:
        db_engine = db_scheme
    context = {
        "active_page": "health",
        "smtp": {
            "configured": smtp_configured,
            "host": settings.smtp_host or "Not configured",
            "port": settings.smtp_port,
            "user": settings.smtp_user or "Not configured",
            "from_email": settings.smtp_from_email or "Not configured",
        },
        "db": {
            "engine": db_engine,
            "path": db_path,
            "url": db_url,
        },
        "triplestore": {
            "url": settings.triplestore_url,
            "repository": settings.repository_id,
            "base_namespace": settings.base_namespace,
        },
        "session_duration_days": settings.session_duration_days,
        "user": user,
    }
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "health.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "health.html", context)

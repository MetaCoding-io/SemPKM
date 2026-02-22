"""Shell router serving dashboard pages via Jinja2 templates.

Serves the top-level navigation pages: dashboard, admin, health.
Each endpoint checks for the HX-Request header to decide between full page
rendering and htmx partial block rendering.

Note: /browser/ is now served by app.browser.router (plan 04-04).
"""

from fastapi import APIRouter, Request

from app.config import settings

router = APIRouter()


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def dashboard(request: Request):
    """Render the dashboard home page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "dashboard.html", {"active_page": "home"}
    )


@router.get("/health/")
async def health_page(request: Request):
    """Render the health check page.

    Full page for direct navigation, content block only for htmx partial swap.
    """
    templates = request.app.state.templates
    smtp_configured = bool(settings.smtp_host)
    context = {
        "active_page": "health",
        "smtp": {
            "configured": smtp_configured,
            "host": settings.smtp_host or "Not configured",
            "port": settings.smtp_port,
            "user": settings.smtp_user or "Not configured",
            "from_email": settings.smtp_from_email or "Not configured",
        },
        "database_url": settings.database_url.split("://")[0] if "://" in settings.database_url else settings.database_url,
        "session_duration_days": settings.session_duration_days,
    }
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "health.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "health.html", context)

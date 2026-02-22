"""Shell router serving dashboard pages via Jinja2 templates.

Serves the top-level navigation pages: dashboard, admin, browser, health.
Each endpoint checks for the HX-Request header to decide between full page
rendering and htmx partial block rendering.
"""

from fastapi import APIRouter, Request

router = APIRouter()


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def dashboard(request: Request):
    """Render the dashboard home page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "dashboard.html")


@router.get("/health/")
async def health_page(request: Request):
    """Render the health check page.

    Full page for direct navigation, content block only for htmx partial swap.
    """
    templates = request.app.state.templates
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "health.html", block_name="content"
        )
    return templates.TemplateResponse(request, "health.html")


@router.get("/browser/")
async def browser_page(request: Request):
    """Render the object browser workspace page (placeholder).

    Will be replaced by the full IDE workspace in plan 04-04.
    """
    templates = request.app.state.templates
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "browser/workspace.html", block_name="content"
        )
    return templates.TemplateResponse(request, "browser/workspace.html")

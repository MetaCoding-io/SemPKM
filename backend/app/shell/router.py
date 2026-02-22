"""Shell router serving dashboard pages via Jinja2 templates.

Serves the top-level navigation pages: dashboard, admin, health.
Each endpoint checks for the HX-Request header to decide between full page
rendering and htmx partial block rendering.

Note: /browser/ is now served by app.browser.router (plan 04-04).
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
    return templates.TemplateResponse(
        request, "dashboard.html", {"active_page": "home"}
    )


@router.get("/health/")
async def health_page(request: Request):
    """Render the health check page.

    Full page for direct navigation, content block only for htmx partial swap.
    """
    templates = request.app.state.templates
    context = {"active_page": "health"}
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "health.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "health.html", context)

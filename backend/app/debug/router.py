"""Debug tool routes: SPARQL query console and event console."""

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User

router = APIRouter(tags=["debug"])


@router.get("/sparql")
async def sparql_page(request: Request, user: User = Depends(require_role("owner"))):
    """Render the SPARQL query console. Owner role required."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/sparql.html", {"active_page": "sparql", "user": user}
    )


@router.get("/events")
async def event_console_page(request: Request, user: User = Depends(get_current_user)):
    """Render the event console (command executor + live event log)."""
    templates = request.app.state.templates
    context = {"active_page": "events", "user": user}
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request, "debug/event_console.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "debug/event_console.html", context)

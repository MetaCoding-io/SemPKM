"""Debug tool routes: SPARQL query console and command executor."""

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_role
from app.auth.models import User

router = APIRouter(tags=["debug"])


@router.get("/sparql")
async def sparql_page(request: Request, user: User = Depends(require_role("owner"))):
    """Render the SPARQL query console. Owner role required."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/sparql.html", {"active_page": "sparql", "user": user}
    )


@router.get("/commands")
async def commands_page(request: Request, user: User = Depends(require_role("owner"))):
    """Render the command executor console. Owner role required."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/commands.html", {"active_page": "commands", "user": user}
    )

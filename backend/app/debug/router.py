"""Debug tool routes: SPARQL query console and command executor."""

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user
from app.auth.models import User

router = APIRouter(tags=["debug"])


@router.get("/sparql")
async def sparql_page(request: Request, user: User = Depends(get_current_user)):
    """Render the SPARQL query console."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/sparql.html", {"active_page": "sparql"}
    )


@router.get("/commands")
async def commands_page(request: Request, user: User = Depends(get_current_user)):
    """Render the command executor console."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/commands.html", {"active_page": "commands"}
    )

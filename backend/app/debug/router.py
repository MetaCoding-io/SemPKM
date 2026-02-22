"""Debug tool routes: SPARQL query console and command executor."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["debug"])


@router.get("/sparql")
async def sparql_page(request: Request):
    """Render the SPARQL query console."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/sparql.html", {"active_page": "sparql"}
    )


@router.get("/commands")
async def commands_page(request: Request):
    """Render the command executor console."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "debug/commands.html", {"active_page": "commands"}
    )

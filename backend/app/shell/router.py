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

router = APIRouter(tags=["shell"])

# ---------------------------------------------------------------------------
# Guide page data
# ---------------------------------------------------------------------------
# Single source of truth for the Docs & Tutorials page chapter list.
# NOTE: docs/guide/README.md and docs/guide/index.html have their own
# manually-maintained chapter lists. When adding a chapter, update all three.
# See KNOWLEDGE.md "User guide has THREE files that must stay in sync".
#
# Section types:
#   "tours"    — Interactive tutorial cards (onclick navigation)
#   "chapters" — User Guide htmx-loaded markdown chapters
#   "links"    — External reference links (open in new tab)

GUIDE_SECTIONS: list[dict] = [
    {
        "title": "Interactive Tutorials",
        "type": "tours",
        "items": [
            {
                "title": "Welcome to SemPKM",
                "icon": "play-circle",
                "url": "/browser/?tour=welcome",
                "desc": "A quick tour of the workspace \u2014 sidebar, explorer, reading objects, the command palette, and saving your work.",
            },
            {
                "title": "Creating Your First Object",
                "icon": "plus-circle",
                "url": "/browser/?tour=create-object",
                "desc": "Step-by-step guide to choosing a type, filling out the form, and saving your first knowledge object.",
            },
        ],
    },
    {
        "title": "User Guide",
        "type": "chapters",
        "items": [
            {"filename": "01-what-is-sempkm.md", "title": "1. What is SemPKM?", "icon": "info"},
            {"filename": "02-core-concepts.md", "title": "2. Core Concepts", "icon": "layers"},
            {"filename": "03-installation-and-setup.md", "title": "3. Installation and Setup", "icon": "download"},
            {"filename": "04-workspace-interface.md", "title": "4. Workspace Interface", "icon": "layout-dashboard"},
            {"filename": "05-working-with-objects.md", "title": "5. Working with Objects", "icon": "box"},
            {"filename": "06-edges-and-relationships.md", "title": "6. Edges and Relationships", "icon": "git-branch"},
            {"filename": "07-browsing-and-visualizing.md", "title": "7. Browsing and Visualizing", "icon": "eye"},
            {"filename": "08-keyboard-shortcuts.md", "title": "8. Keyboard Shortcuts", "icon": "keyboard"},
            {"filename": "09-understanding-mental-models.md", "title": "9. Understanding Mental Models", "icon": "brain"},
            {"filename": "10-managing-mental-models.md", "title": "10. Managing Mental Models", "icon": "package"},
            {"filename": "39-mental-model-catalog.md", "title": "39. Mental Model Catalog", "icon": "library"},
            {"filename": "11-user-management.md", "title": "11. User Management", "icon": "users"},
            {"filename": "12-webhooks.md", "title": "12. Webhooks", "icon": "webhook"},
            {"filename": "13-settings.md", "title": "13. Settings", "icon": "settings"},
            {"filename": "14-system-health-and-debugging.md", "title": "14. System Health and Debugging", "icon": "activity"},
            {"filename": "15-event-log.md", "title": "15. Event Log", "icon": "clock"},
            {"filename": "16-data-model.md", "title": "16. Data Model", "icon": "database"},
            {"filename": "17-command-api.md", "title": "17. Command API", "icon": "terminal"},
            {"filename": "18-sparql-endpoint.md", "title": "18. SPARQL Endpoint", "icon": "search-code"},
            {"filename": "19-creating-mental-models.md", "title": "19. Creating Mental Models", "icon": "plus-square"},
            {"filename": "20-production-deployment.md", "title": "20. Production Deployment", "icon": "server"},
            {"filename": "21-sparql-console.md", "title": "21. SPARQL Console", "icon": "terminal-square"},
            {"filename": "22-keyword-search.md", "title": "22. Keyword Search", "icon": "search"},
            {"filename": "23-vfs.md", "title": "23. Virtual Filesystem (WebDAV)", "icon": "hard-drive"},
            {"filename": "24-obsidian-onboarding.md", "title": "24. Obsidian Onboarding", "icon": "gem"},
            {"filename": "45-notion-import.md", "title": "45. Notion Import", "icon": "file-input"},
            {"filename": "25-webid-profiles.md", "title": "25. WebID Profiles", "icon": "user-check"},
            {"filename": "26-indieauth.md", "title": "26. IndieAuth", "icon": "shield-check"},
            {"filename": "27-spatial-canvas.md", "title": "27. Spatial Canvas", "icon": "move"},
            {"filename": "28-dashboards-and-workflows.md", "title": "28. Dashboards & Workflows", "icon": "gauge"},
            {"filename": "29-app-platform.md", "title": "29. App Platform", "icon": "blocks"},
            {"filename": "40-rss-reader.md", "title": "40. RSS Reader", "icon": "rss"},
            {"filename": "30-personas.md", "title": "30. Workspace Personas", "icon": "user-cog"},
            {"filename": "31-api-surface.md", "title": "31. API Surface", "icon": "plug"},
            {"filename": "32-browser-extension.md", "title": "32. Browser Extension", "icon": "puzzle"},
            {"filename": "33-context-overlay.md", "title": "33. Context Overlay", "icon": "layers"},
            {"filename": "46-ai-features.md", "title": "46. AI Features", "icon": "sparkles"},
            {"filename": "34-linear-sync.md", "title": "34. Linear Sync", "icon": "refresh-cw"},
            {"filename": "35-github-sync.md", "title": "35. GitHub Sync", "icon": "github"},
            {"filename": "36-jira-sync.md", "title": "36. Jira Sync", "icon": "ticket"},
            {"filename": "37-monday-sync.md", "title": "37. Monday.com Sync", "icon": "columns-3"},
            {"filename": "41-google-calendar-sync.md", "title": "41. Google Calendar Sync", "icon": "calendar"},
            {"filename": "42-todoist-sync.md", "title": "42. Todoist Sync", "icon": "check-square"},
            {"filename": "43-outlook-calendar-sync.md", "title": "43. Outlook Calendar Sync", "icon": "mail"},
            {"filename": "44-caldav-calendar-sync.md", "title": "44. CalDAV Calendar Sync", "icon": "calendar-clock"},
            {"filename": "47-asana-sync.md", "title": "47. Asana Sync", "icon": "list-checks"},
            {"filename": "48-mobile-app-context.md", "title": "48. Mobile App & Context", "icon": "smartphone"},
            {"filename": "49-media-scheduler.md", "title": "49. Media Scheduler", "icon": "radio"},
            {"filename": "50-ppv-model.md", "title": "50. PPV Model", "icon": "compass"},
            {"filename": "38-hosted-demo.md", "title": "38. Hosted Demo", "icon": "globe"},
            {"filename": "51-federation.md", "title": "51. Federation & Shared Graphs", "icon": "share-2"},
            # Appendices
            {"filename": "appendix-a-environment-variables.md", "title": "Appendix A: Environment Variables", "icon": "file-text", "appendix": True},
            {"filename": "appendix-b-keyboard-shortcuts.md", "title": "Appendix B: Keyboard Shortcuts", "icon": "file-text", "appendix": True},
            {"filename": "appendix-c-command-api-reference.md", "title": "Appendix C: Command API Reference", "icon": "file-text", "appendix": True},
            {"filename": "appendix-d-glossary.md", "title": "Appendix D: Glossary", "icon": "book", "appendix": True},
            {"filename": "appendix-e-troubleshooting.md", "title": "Appendix E: Troubleshooting", "icon": "alert-triangle", "appendix": True},
            {"filename": "appendix-f-faq.md", "title": "Appendix F: FAQ", "icon": "help-circle", "appendix": True},
        ],
    },
    {
        "title": "External References",
        "type": "links",
        "items": [
            {"title": "API Reference (ReDoc)", "icon": "file-text", "url": "/redoc"},
            {"title": "API Reference (Swagger)", "icon": "file-code", "url": "/docs"},
            {"title": "Health Check", "icon": "activity", "url": "/health"},
        ],
    },
]


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


@router.get("/guide")
async def guide_page(request: Request, user: User = Depends(get_current_user)):
    """Render the Docs & Tutorials hub as a standalone page."""
    templates = request.app.state.templates
    context = {"active_page": "guide", "user": user, "guide_sections": GUIDE_SECTIONS}
    if _is_htmx_request(request):
        return templates.TemplateResponse(request, "guide.html", context, block_name="content")
    return templates.TemplateResponse(request, "guide.html", context)


@router.get("/guide/{filename:path}")
async def guide_article(
    filename: str, request: Request, user: User = Depends(get_current_user)
):
    """Render a single user guide article as a standalone page."""
    templates = request.app.state.templates
    context = {"active_page": "guide", "user": user, "filename": filename}
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "guide_article.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "guide_article.html", context)


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

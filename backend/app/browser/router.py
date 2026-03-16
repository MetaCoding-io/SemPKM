"""Browser router coordinator.

Thin assembler that mounts all browser sub-routers under the /browser
prefix.  Individual route handlers live in their own domain modules:
settings, pages, workspace, objects, events, search, ontology.
"""

from fastapi import APIRouter

from app.ontology.router import ontology_router

from .comments import comments_router
from .events import events_router
from .favorites import favorites_router
from .objects import objects_router
from .pages import pages_router
from .search import search_router
from .settings import settings_router
from .sparql_result import sparql_result_router
from .workspace import workspace_router

router = APIRouter(prefix="/browser", tags=["browser"])

# Include order: ontology, comments, and sparql-result before objects because
# objects_router has catch-all :path patterns that would consume their URLs.
router.include_router(settings_router)
router.include_router(ontology_router)
router.include_router(comments_router)
router.include_router(sparql_result_router)
router.include_router(objects_router)
router.include_router(pages_router)
router.include_router(workspace_router)
router.include_router(events_router)
router.include_router(search_router)
router.include_router(favorites_router)

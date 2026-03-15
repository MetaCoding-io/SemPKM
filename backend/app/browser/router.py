"""Browser router coordinator.

Thin assembler that mounts all browser sub-routers under the /browser
prefix.  Individual route handlers live in their own domain modules:
<<<<<<< HEAD
settings, pages, workspace, objects, events, search, ontology.
=======
settings, pages, workspace, objects, events, search.
>>>>>>> gsd/M002/S04
"""

from fastapi import APIRouter

<<<<<<< HEAD
from app.ontology.router import ontology_router

from .comments import comments_router
from .events import events_router
from .favorites import favorites_router
=======
from .events import events_router
>>>>>>> gsd/M002/S04
from .objects import objects_router
from .pages import pages_router
from .search import search_router
from .settings import settings_router
from .workspace import workspace_router

router = APIRouter(prefix="/browser", tags=["browser"])

<<<<<<< HEAD
# Include order: ontology and comments before objects because objects_router
# has catch-all :path patterns that would consume /ontology/* and /comments/*.
router.include_router(settings_router)
router.include_router(ontology_router)
router.include_router(comments_router)
=======
# Include order matches the original route registration order:
# settings → objects → pages → workspace → events → search
router.include_router(settings_router)
>>>>>>> gsd/M002/S04
router.include_router(objects_router)
router.include_router(pages_router)
router.include_router(workspace_router)
router.include_router(events_router)
router.include_router(search_router)
<<<<<<< HEAD
router.include_router(favorites_router)
=======
>>>>>>> gsd/M002/S04

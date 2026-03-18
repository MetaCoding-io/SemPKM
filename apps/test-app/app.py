"""Test application exercising all SDK features for E2E testing.

Registers handlers for every SDK integration point:
- 5 fragment routes (main page, right pane, view, command dialog, renderer)
- 1 scheduled task (heartbeat)
- 2 lifecycle hooks (startup, shutdown)
"""

from sempkm_app_sdk import App, AppContext
from starlette.requests import Request
from starlette.responses import HTMLResponse
import logging

logger = logging.getLogger(__name__)

test_app = App("test-app")


@test_app.route("/_fragments/main")
async def main_fragment(request: Request):
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("main.html"))


@test_app.route("/_fragments/right-pane")
async def right_pane_fragment(request: Request):
    iri = request.query_params.get("iri", "unknown")
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("right-pane.html", iri=iri))


@test_app.route("/_fragments/test-view")
async def test_view_fragment(request: Request):
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("test-view.html"))


@test_app.route("/_fragments/command-dialog")
async def command_dialog_fragment(request: Request):
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("command-dialog.html"))


@test_app.route("/_fragments/read-renderer")
async def read_renderer_fragment(request: Request):
    iri = request.query_params.get("iri", "unknown")
    ctx = request.app.state.ctx
    return HTMLResponse(ctx.render_template("read-renderer.html", iri=iri))


@test_app.task("heartbeat")
def heartbeat_task(ctx: AppContext):
    logger.info("Heartbeat task executed for %s", ctx.app_id)
    return {"status": "alive"}


@test_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("Test app started: %s", ctx.app_id)


@test_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("Test app stopped: %s", ctx.app_id)

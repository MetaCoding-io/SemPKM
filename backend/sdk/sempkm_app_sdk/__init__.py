"""SemPKM App SDK — build apps for the SemPKM platform.

Usage::

    from sempkm_app_sdk import App, AppContext

    app = App("my-app")

    @app.route("/_fragments/main")
    async def main_fragment(request):
        ctx = request.app.state.ctx
        return HTMLResponse(ctx.render_template("main.html"))
"""

from sempkm_app_sdk.app import App
from sempkm_app_sdk.context import AppContext

__all__ = ["App", "AppContext"]
__version__ = "0.1.0"

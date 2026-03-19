"""GitHub Sync app — two-way sync between SemPKM objects and GitHub issues.

Stub entrypoint. Full routes are added in T03 (settings UI).
"""

import logging

from sempkm_app_sdk import App, AppContext

logger = logging.getLogger("github_sync")

github_sync_app = App("github-sync")


@github_sync_app.on_startup
def on_startup(ctx: AppContext):
    logger.info("GitHub Sync app started: %s", ctx.app_id)


@github_sync_app.on_shutdown
def on_shutdown(ctx: AppContext):
    logger.info("GitHub Sync app stopped: %s", ctx.app_id)

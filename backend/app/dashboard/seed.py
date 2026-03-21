"""Seed sample data for first-time users.

Creates a "Getting Started" dashboard and a "Create & Review" workflow
when a user has none.  Called at app startup — idempotent.
"""

import logging
import uuid

from app.dashboard.service import DashboardService
from app.workflow.service import WorkflowService

logger = logging.getLogger(__name__)


async def seed_sample_data(
    dashboard_service: DashboardService,
    workflow_service: WorkflowService,
    user_id: uuid.UUID,
) -> dict:
    """Create sample dashboard and workflow if user has none.

    Returns dict with keys ``dashboard_created`` and ``workflow_created`` (bool).
    """
    result = {"dashboard_created": False, "workflow_created": False}

    # --- Dashboard seed ---
    existing_dashboards = await dashboard_service.list_for_user(user_id)
    if not existing_dashboards:
        await dashboard_service.create(
            user_id=user_id,
            name="Getting Started",
            layout="sidebar-main",
            description="A sample dashboard to help you get started with SemPKM.",
            blocks=[
                {
                    "type": "markdown",
                    "slot": "sidebar",
                    "config": {
                        "content": (
                            "# Welcome\n\n"
                            "This is a sample dashboard. Dashboards let you "
                            "combine views, forms, and content into a single "
                            "workspace.\n\n"
                            "**Try editing this dashboard** to add your own "
                            "blocks and customise the layout."
                        ),
                    },
                },
                {
                    "type": "view-embed",
                    "slot": "main",
                    "config": {
                        "spec_iri": "",
                        "renderer_type": "table",
                    },
                },
            ],
        )
        result["dashboard_created"] = True
        logger.info("Seeded 'Getting Started' dashboard for user %s", user_id)

    # --- Workflow seed ---
    existing_workflows = await workflow_service.list_for_user(user_id)
    if not existing_workflows:
        await workflow_service.create(
            user_id=user_id,
            name="Create & Review",
            description="A sample two-step workflow: create an item, then review it.",
            steps=[
                {
                    "type": "form",
                    "label": "Create",
                    "config": {"target_class": ""},
                },
                {
                    "type": "view",
                    "label": "Review",
                    "config": {
                        "spec_iri": "",
                        "renderer_type": "table",
                    },
                },
            ],
        )
        result["workflow_created"] = True
        logger.info("Seeded 'Create & Review' workflow for user %s", user_id)

    return result

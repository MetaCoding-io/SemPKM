"""Seed sample data for first-time users.

Creates a "Getting Started" dashboard and review workflows
when a user has none.  Called at app startup — idempotent.

Workflow seeding uses per-name idempotency: each seed workflow is
checked individually so user-created workflows are never affected
and partial re-seeding works correctly.
"""

import logging
import uuid

from app.dashboard.service import DashboardService
from app.workflow.service import WorkflowService

logger = logging.getLogger(__name__)

# All seed workflows defined declaratively.  Each entry is passed
# directly to WorkflowService.create() (minus ``user_id``).
# PPV-specific review workflows are now model-sourced (models/ppv/workflows/)
# and installed via TBox lifecycle — only the generic sample remains here.
SEED_WORKFLOWS: list[dict] = [
    {
        "name": "Create & Review",
        "description": "A sample two-step workflow: create an item, then review it.",
        "steps": [
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
    },
]


async def seed_sample_data(
    dashboard_service: DashboardService,
    workflow_service: WorkflowService,
    user_id: uuid.UUID,
) -> dict:
    """Create sample dashboard and seed workflows if missing.

    Workflow seeding is per-name: each workflow in ``SEED_WORKFLOWS`` is
    created only if no existing workflow with that name exists.  This
    means user-created workflows are never touched, and partial re-seeding
    (e.g. after adding new review types) works correctly.

    Returns dict with keys:
        ``dashboard_created`` (bool)
        ``workflow_created`` (bool) — True if *any* workflow was created
        ``workflows_created`` (int) — count of workflows created this call
    """
    result: dict = {
        "dashboard_created": False,
        "workflow_created": False,
        "workflows_created": 0,
    }

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

    # --- Workflow seed (per-name idempotency) ---
    existing_workflows = await workflow_service.list_for_user(user_id)
    existing_names: set[str] = {wf.name for wf in existing_workflows}

    created_count = 0
    for wf_def in SEED_WORKFLOWS:
        if wf_def["name"] in existing_names:
            logger.debug(
                "Skipping seed workflow '%s' — already exists for user %s",
                wf_def["name"],
                user_id,
            )
            continue
        await workflow_service.create(
            user_id=user_id,
            name=wf_def["name"],
            steps=wf_def["steps"],
            description=wf_def.get("description", ""),
        )
        created_count += 1
        logger.info(
            "Seeded '%s' workflow for user %s", wf_def["name"], user_id
        )

    result["workflows_created"] = created_count
    result["workflow_created"] = created_count > 0

    return result

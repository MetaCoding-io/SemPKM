"""Mock Asana REST API v1.0 server for E2E testing.

A lightweight HTTP server returning canned REST responses wrapped in
Asana's ``{"data": ..., "next_page": null}`` envelope.  Designed to run
inside Docker alongside the SemPKM test stack so the AsanaClient can be
redirected here via ``ASANA_API_URL``.

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import io
import json
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8080
VALID_TOKEN = "test-asana-pat-token-abc123"

# ---------------------------------------------------------------------------
# Canned IDs
# ---------------------------------------------------------------------------

USER_GID = "user-001"
WORKSPACE_GID = "ws-001"

PROJECT_1_GID = "proj-001"
PROJECT_2_GID = "proj-002"

# Sections for project 1
SEC_TODO_1 = "sec-001"
SEC_INPROG_1 = "sec-002"
SEC_DONE_1 = "sec-003"

# Sections for project 2
SEC_TODO_2 = "sec-004"
SEC_INPROG_2 = "sec-005"
SEC_DONE_2 = "sec-006"

# Custom field GIDs
CF_STATUS_GID = "cf-status-001"
CF_PRIORITY_GID = "cf-priority-001"
CF_STORYPTS_GID = "cf-storypts-001"

# Enum option GIDs — Status
STATUS_TODO_GID = "enum-status-todo"
STATUS_INPROG_GID = "enum-status-inprog"
STATUS_DONE_GID = "enum-status-done"

# Enum option GIDs — Priority
PRIO_LOW_GID = "enum-prio-low"
PRIO_MEDIUM_GID = "enum-prio-medium"
PRIO_HIGH_GID = "enum-prio-high"

# Task GIDs
TASK_1_GID = "task-001"
TASK_2_GID = "task-002"
TASK_3_GID = "task-003"
SUBTASK_1_GID = "subtask-001"

# Tag GIDs
TAG_1_GID = "tag-001"
TAG_2_GID = "tag-002"

# ---------------------------------------------------------------------------
# Canned response data
# ---------------------------------------------------------------------------

USER_DATA = {
    "gid": USER_GID,
    "name": "Test User",
    "email": "test@example.com",
    "resource_type": "user",
}

WORKSPACE_DATA = {
    "gid": WORKSPACE_GID,
    "name": "Test Workspace",
    "resource_type": "workspace",
}

# -- Custom fields ---------------------------------------------------------

STATUS_ENUM_OPTIONS = [
    {"gid": STATUS_TODO_GID, "name": "To Do", "resource_type": "enum_option"},
    {"gid": STATUS_INPROG_GID, "name": "In Progress", "resource_type": "enum_option"},
    {"gid": STATUS_DONE_GID, "name": "Done", "resource_type": "enum_option"},
]

PRIORITY_ENUM_OPTIONS = [
    {"gid": PRIO_LOW_GID, "name": "Low", "resource_type": "enum_option"},
    {"gid": PRIO_MEDIUM_GID, "name": "Medium", "resource_type": "enum_option"},
    {"gid": PRIO_HIGH_GID, "name": "High", "resource_type": "enum_option"},
]

CUSTOM_FIELD_STATUS = {
    "gid": CF_STATUS_GID,
    "name": "Status",
    "resource_subtype": "enum",
    "resource_type": "custom_field",
    "enum_options": STATUS_ENUM_OPTIONS,
}

CUSTOM_FIELD_PRIORITY = {
    "gid": CF_PRIORITY_GID,
    "name": "Priority",
    "resource_subtype": "enum",
    "resource_type": "custom_field",
    "enum_options": PRIORITY_ENUM_OPTIONS,
}

CUSTOM_FIELD_STORYPTS = {
    "gid": CF_STORYPTS_GID,
    "name": "Story Points",
    "resource_subtype": "number",
    "resource_type": "custom_field",
}

CUSTOM_FIELD_SETTINGS = [
    {"custom_field": CUSTOM_FIELD_STATUS},
    {"custom_field": CUSTOM_FIELD_PRIORITY},
    {"custom_field": CUSTOM_FIELD_STORYPTS},
]

# -- Projects --------------------------------------------------------------

PROJECTS = {
    PROJECT_1_GID: {
        "gid": PROJECT_1_GID,
        "name": "Project Alpha",
        "archived": False,
        "resource_type": "project",
        "custom_field_settings": CUSTOM_FIELD_SETTINGS,
    },
    PROJECT_2_GID: {
        "gid": PROJECT_2_GID,
        "name": "Project Beta",
        "archived": False,
        "resource_type": "project",
        "custom_field_settings": CUSTOM_FIELD_SETTINGS,
    },
}

# -- Sections per project --------------------------------------------------

SECTIONS = {
    PROJECT_1_GID: [
        {"gid": SEC_TODO_1, "name": "To Do", "resource_type": "section"},
        {"gid": SEC_INPROG_1, "name": "In Progress", "resource_type": "section"},
        {"gid": SEC_DONE_1, "name": "Done", "resource_type": "section"},
    ],
    PROJECT_2_GID: [
        {"gid": SEC_TODO_2, "name": "To Do", "resource_type": "section"},
        {"gid": SEC_INPROG_2, "name": "In Progress", "resource_type": "section"},
        {"gid": SEC_DONE_2, "name": "Done", "resource_type": "section"},
    ],
}

# All sections flat for addTask lookup
ALL_SECTIONS = {}
for _secs in SECTIONS.values():
    for _s in _secs:
        ALL_SECTIONS[_s["gid"]] = _s

# -- Tasks -----------------------------------------------------------------

TASKS = {
    PROJECT_1_GID: [
        {
            "gid": TASK_1_GID,
            "name": "Design landing page",
            "completed": False,
            "completed_at": None,
            "resource_subtype": "default_task",
            "resource_type": "task",
            "notes": "Create the main landing page with hero section.",
            "html_notes": "<body>Create the main landing page with hero section.</body>",
            "due_on": "2026-04-15",
            "due_at": None,
            "start_on": "2026-03-20",
            "start_at": None,
            "custom_fields": [
                {
                    "gid": CF_STATUS_GID,
                    "name": "Status",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": STATUS_INPROG_GID, "name": "In Progress"},
                    "number_value": None,
                },
                {
                    "gid": CF_PRIORITY_GID,
                    "name": "Priority",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": PRIO_HIGH_GID, "name": "High"},
                    "number_value": None,
                },
                {
                    "gid": CF_STORYPTS_GID,
                    "name": "Story Points",
                    "resource_subtype": "number",
                    "enum_value": None,
                    "number_value": 5,
                },
            ],
            "memberships": [
                {"section": {"gid": SEC_INPROG_1, "name": "In Progress"}},
            ],
            "tags": [
                {"gid": TAG_1_GID, "name": "frontend"},
                {"gid": TAG_2_GID, "name": "design"},
            ],
            "assignee": {
                "gid": USER_GID,
                "email": "test@example.com",
                "name": "Test User",
            },
            "followers": [
                {"gid": USER_GID, "email": "test@example.com", "name": "Test User"},
            ],
            "parent": None,
            "permalink_url": "https://app.asana.com/0/proj-001/task-001",
            "created_at": "2026-03-01T10:00:00.000Z",
            "modified_at": "2026-03-15T14:30:00.000Z",
        },
        {
            "gid": TASK_2_GID,
            "name": "Write API documentation",
            "completed": True,
            "completed_at": "2026-03-10T16:00:00.000Z",
            "resource_subtype": "default_task",
            "resource_type": "task",
            "notes": "Document all REST endpoints.",
            "html_notes": "<body>Document all REST endpoints.</body>",
            "due_on": "2026-03-10",
            "due_at": None,
            "start_on": None,
            "start_at": None,
            "custom_fields": [
                {
                    "gid": CF_STATUS_GID,
                    "name": "Status",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": STATUS_DONE_GID, "name": "Done"},
                    "number_value": None,
                },
                {
                    "gid": CF_PRIORITY_GID,
                    "name": "Priority",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": PRIO_MEDIUM_GID, "name": "Medium"},
                    "number_value": None,
                },
                {
                    "gid": CF_STORYPTS_GID,
                    "name": "Story Points",
                    "resource_subtype": "number",
                    "enum_value": None,
                    "number_value": 3,
                },
            ],
            "memberships": [
                {"section": {"gid": SEC_DONE_1, "name": "Done"}},
            ],
            "tags": [],
            "assignee": {
                "gid": USER_GID,
                "email": "test@example.com",
                "name": "Test User",
            },
            "followers": [],
            "parent": None,
            "permalink_url": "https://app.asana.com/0/proj-001/task-002",
            "created_at": "2026-03-02T09:00:00.000Z",
            "modified_at": "2026-03-10T16:00:00.000Z",
        },
    ],
    PROJECT_2_GID: [
        {
            "gid": TASK_3_GID,
            "name": "Set up CI pipeline",
            "completed": False,
            "completed_at": None,
            "resource_subtype": "default_task",
            "resource_type": "task",
            "notes": "Configure GitHub Actions for automated testing.",
            "html_notes": "<body>Configure GitHub Actions for automated testing.</body>",
            "due_on": "2026-04-01",
            "due_at": None,
            "start_on": "2026-03-18",
            "start_at": None,
            "custom_fields": [
                {
                    "gid": CF_STATUS_GID,
                    "name": "Status",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": STATUS_TODO_GID, "name": "To Do"},
                    "number_value": None,
                },
                {
                    "gid": CF_PRIORITY_GID,
                    "name": "Priority",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": PRIO_LOW_GID, "name": "Low"},
                    "number_value": None,
                },
                {
                    "gid": CF_STORYPTS_GID,
                    "name": "Story Points",
                    "resource_subtype": "number",
                    "enum_value": None,
                    "number_value": 8,
                },
            ],
            "memberships": [
                {"section": {"gid": SEC_TODO_2, "name": "To Do"}},
            ],
            "tags": [
                {"gid": TAG_1_GID, "name": "devops"},
            ],
            "assignee": None,
            "followers": [],
            "parent": None,
            "permalink_url": "https://app.asana.com/0/proj-002/task-003",
            "created_at": "2026-03-05T11:00:00.000Z",
            "modified_at": "2026-03-18T09:00:00.000Z",
        },
    ],
}

# Tasks by GID for PATCH lookup
_TASKS_BY_GID: dict[str, dict] = {}
for _task_list in TASKS.values():
    for _t in _task_list:
        _TASKS_BY_GID[_t["gid"]] = _t

# -- Subtasks --------------------------------------------------------------

SUBTASKS = {
    TASK_1_GID: [
        {
            "gid": SUBTASK_1_GID,
            "name": "Draft wireframe sketches",
            "completed": False,
            "completed_at": None,
            "resource_subtype": "default_task",
            "resource_type": "task",
            "notes": "Initial wireframe concepts for the hero section.",
            "html_notes": "<body>Initial wireframe concepts for the hero section.</body>",
            "due_on": "2026-03-25",
            "due_at": None,
            "start_on": None,
            "start_at": None,
            "custom_fields": [
                {
                    "gid": CF_STATUS_GID,
                    "name": "Status",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": STATUS_TODO_GID, "name": "To Do"},
                    "number_value": None,
                },
                {
                    "gid": CF_PRIORITY_GID,
                    "name": "Priority",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": PRIO_MEDIUM_GID, "name": "Medium"},
                    "number_value": None,
                },
                {
                    "gid": CF_STORYPTS_GID,
                    "name": "Story Points",
                    "resource_subtype": "number",
                    "enum_value": None,
                    "number_value": 2,
                },
            ],
            "memberships": [
                {"section": {"gid": SEC_TODO_1, "name": "To Do"}},
            ],
            "tags": [],
            "assignee": {
                "gid": USER_GID,
                "email": "test@example.com",
                "name": "Test User",
            },
            "followers": [],
            "parent": {"gid": TASK_1_GID, "resource_type": "task"},
            "permalink_url": "https://app.asana.com/0/proj-001/subtask-001",
            "created_at": "2026-03-02T10:00:00.000Z",
            "modified_at": "2026-03-15T14:00:00.000Z",
        },
    ],
}

# Add subtask to flat lookup
for _sub_list in SUBTASKS.values():
    for _st in _sub_list:
        _TASKS_BY_GID[_st["gid"]] = _st


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockAsanaHandler(BaseHTTPRequestHandler):
    """Handles GET, POST, and PATCH requests mimicking the Asana REST API v1.0."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        # Health endpoint — no auth, no envelope
        if path == "/health":
            self._send_json({"status": "ok"})
            self._log("GET", self.path, 200)
            return

        if not self._check_auth():
            return

        # GET /api/1.0/users/me
        if path == "/api/1.0/users/me":
            self._send_asana(USER_DATA)
            self._log("GET", self.path, 200)
            return

        # GET /api/1.0/workspaces
        if path == "/api/1.0/workspaces":
            self._send_asana_list([WORKSPACE_DATA])
            self._log("GET", self.path, 200)
            return

        # GET /api/1.0/workspaces/{gid}/projects
        m = re.match(r"^/api/1\.0/workspaces/([^/]+)/projects$", path)
        if m:
            ws_gid = m.group(1)
            if ws_gid != WORKSPACE_GID:
                self._send_asana_list([])
                self._log("GET", self.path, 200)
                return
            projects = list(PROJECTS.values())
            # Filter archived if query param present
            archived_param = query.get("archived", [None])[0]
            if archived_param == "false":
                projects = [p for p in projects if not p.get("archived", False)]
            self._send_asana_list(projects)
            self._log("GET", self.path, 200)
            return

        # GET /api/1.0/projects/{gid}/custom_field_settings
        m = re.match(r"^/api/1\.0/projects/([^/]+)/custom_field_settings$", path)
        if m:
            proj_gid = m.group(1)
            if proj_gid in PROJECTS:
                self._send_asana_list(CUSTOM_FIELD_SETTINGS)
            else:
                self._send_json(
                    {"errors": [{"message": f"project {proj_gid} not found"}]},
                    status=404,
                )
            self._log("GET", self.path, 200 if proj_gid in PROJECTS else 404)
            return

        # GET /api/1.0/projects/{gid}/sections
        m = re.match(r"^/api/1\.0/projects/([^/]+)/sections$", path)
        if m:
            proj_gid = m.group(1)
            sections = SECTIONS.get(proj_gid, [])
            self._send_asana_list(sections)
            self._log("GET", self.path, 200)
            return

        # GET /api/1.0/projects/{gid}/tasks
        m = re.match(r"^/api/1\.0/projects/([^/]+)/tasks$", path)
        if m:
            proj_gid = m.group(1)
            tasks = TASKS.get(proj_gid, [])
            self._send_asana_list(tasks)
            self._log("GET", self.path, 200)
            return

        # GET /api/1.0/projects/{gid} (single project)
        m = re.match(r"^/api/1\.0/projects/([^/]+)$", path)
        if m:
            proj_gid = m.group(1)
            proj = PROJECTS.get(proj_gid)
            if proj:
                self._send_asana(proj)
                self._log("GET", self.path, 200)
            else:
                self._send_json(
                    {"errors": [{"message": f"project {proj_gid} not found"}]},
                    status=404,
                )
                self._log("GET", self.path, 404)
            return

        # GET /api/1.0/tasks/{gid}/subtasks
        m = re.match(r"^/api/1\.0/tasks/([^/]+)/subtasks$", path)
        if m:
            task_gid = m.group(1)
            subtasks = SUBTASKS.get(task_gid, [])
            self._send_asana_list(subtasks)
            self._log("GET", self.path, 200)
            return

        # Fallthrough
        self._send_json(
            {"errors": [{"message": "Not Found"}]}, status=404
        )
        self._log("GET", self.path, 404)

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if not self._check_auth():
            return

        # PATCH /api/1.0/tasks/{gid}
        m = re.match(r"^/api/1\.0/tasks/([^/]+)$", path)
        if m:
            task_gid = m.group(1)
            body = self._read_json_body()
            base = _TASKS_BY_GID.get(task_gid)
            if base is None:
                self._send_json(
                    {"errors": [{"message": f"task {task_gid} not found"}]},
                    status=404,
                )
                self._log("PATCH", self.path, 404)
                return
            # Merge: Asana PATCH wraps updates in {"data": {...}}
            updates = body.get("data", body) if body else {}
            merged = dict(base)
            merged.update(updates)
            self._send_asana(merged)
            self._log("PATCH", self.path, 200)
            return

        self._send_json(
            {"errors": [{"message": "Not Found"}]}, status=404
        )
        self._log("PATCH", self.path, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if not self._check_auth():
            return

        # POST /api/1.0/sections/{gid}/addTask
        m = re.match(r"^/api/1\.0/sections/([^/]+)/addTask$", path)
        if m:
            section_gid = m.group(1)
            body = self._read_json_body()
            # Accept both {"data": {"task": gid}} and {"task": gid}
            if body:
                data = body.get("data", body)
                _task_gid = data.get("task")
            self._send_asana({})
            self._log("POST", self.path, 200)
            return

        self._send_json(
            {"errors": [{"message": "Not Found"}]}, status=404
        )
        self._log("POST", self.path, 404)

    # -- helpers ------------------------------------------------------------

    def _check_auth(self) -> bool:
        """Validate Bearer token. Returns True if valid, sends 401 if not."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != VALID_TOKEN:
            self._send_json(
                {"errors": [{"message": "Not Authorized"}]}, status=401
            )
            self._log(self.command, self.path, 401)
            return False
        return True

    def _read_json_body(self) -> dict | None:
        """Read and parse JSON request body, or return None."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None

    def _send_json(self, body: dict | list, status: int = 200) -> None:
        """Write a JSON response with Content-Type header."""
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_asana(self, data: dict) -> None:
        """Send a single-object Asana response: {"data": obj}."""
        self._send_json({"data": data})

    def _send_asana_list(self, items: list) -> None:
        """Send a list Asana response: {"data": [...], "next_page": null}."""
        self._send_json({"data": items, "next_page": None})

    def _log(self, method: str, path: str, status: int) -> None:
        print(
            f"[mock-asana] {method} {path} → {status}",
            file=sys.stderr, flush=True,
        )

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-asana] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Simulate requests against all endpoints, verify responses, exit."""
    print("[selftest] Starting mock Asana API self-test...")

    passed = 0
    failed = 0

    def check(
        name: str,
        method: str,
        path: str,
        body: bytes | None = None,
        auth: bool = True,
        expect_status: int = 200,
        expect_check=None,
    ):
        nonlocal passed, failed

        handler = _make_fake_handler(method, path, body, auth=auth)
        actual_status = handler._test_status

        if actual_status != expect_status:
            print(f"  FAIL: {name} — expected {expect_status}, got {actual_status}")
            failed += 1
            return

        if expect_check and not expect_check(handler._test_body):
            print(f"  FAIL: {name} — response body check failed")
            print(f"        body: {json.dumps(handler._test_body, indent=2)[:200]}")
            failed += 1
            return

        print(f"  ✓ {name}")
        passed += 1

    # -----------------------------------------------------------------------
    # 1. Health (no auth)
    # -----------------------------------------------------------------------
    check(
        "GET /health (no auth)", "GET", "/health",
        auth=False,
        expect_check=lambda b: b.get("status") == "ok",
    )

    # -----------------------------------------------------------------------
    # 2. Auth rejection
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/users/me without auth → 401",
        "GET", "/api/1.0/users/me",
        auth=False, expect_status=401,
        expect_check=lambda b: "errors" in b,
    )

    # -----------------------------------------------------------------------
    # 3. Users/me
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/users/me", "GET", "/api/1.0/users/me",
        expect_check=lambda b: (
            b.get("data", {}).get("gid") == USER_GID
            and b["data"].get("email") == "test@example.com"
        ),
    )

    # -----------------------------------------------------------------------
    # 4. Workspaces
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/workspaces", "GET", "/api/1.0/workspaces",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 1
            and b["data"][0]["gid"] == WORKSPACE_GID
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 5. Projects in workspace
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/workspaces/{gid}/projects",
        "GET", f"/api/1.0/workspaces/{WORKSPACE_GID}/projects",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 2
            and b["data"][0]["name"] == "Project Alpha"
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 6. Single project with custom_field_settings
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/projects/{gid}",
        "GET", f"/api/1.0/projects/{PROJECT_1_GID}",
        expect_check=lambda b: (
            b.get("data", {}).get("gid") == PROJECT_1_GID
            and len(b["data"].get("custom_field_settings", [])) == 3
        ),
    )

    # -----------------------------------------------------------------------
    # 7. Custom field settings (separate endpoint)
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/projects/{gid}/custom_field_settings",
        "GET", f"/api/1.0/projects/{PROJECT_1_GID}/custom_field_settings",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 3
            and b["data"][0]["custom_field"]["name"] == "Status"
            and b["data"][0]["custom_field"]["resource_subtype"] == "enum"
            and len(b["data"][0]["custom_field"]["enum_options"]) == 3
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 8. Sections
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/projects/{gid}/sections",
        "GET", f"/api/1.0/projects/{PROJECT_1_GID}/sections",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 3
            and b["data"][0]["name"] == "To Do"
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 9. Tasks with all required fields
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/projects/{gid}/tasks",
        "GET", f"/api/1.0/projects/{PROJECT_1_GID}/tasks",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 2
            and b["data"][0]["name"] == "Design landing page"
            and b["data"][0]["resource_subtype"] == "default_task"
            # custom_fields present with enum values
            and len(b["data"][0]["custom_fields"]) == 3
            and b["data"][0]["custom_fields"][0]["enum_value"]["name"] == "In Progress"
            # memberships with section
            and len(b["data"][0]["memberships"]) == 1
            and b["data"][0]["memberships"][0]["section"]["name"] == "In Progress"
            # tags
            and len(b["data"][0]["tags"]) == 2
            # assignee
            and b["data"][0]["assignee"]["email"] == "test@example.com"
            # permalink_url
            and "permalink_url" in b["data"][0]
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 10. Subtasks (task with subtasks)
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/tasks/{gid}/subtasks (has subtask)",
        "GET", f"/api/1.0/tasks/{TASK_1_GID}/subtasks",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 1
            and b["data"][0]["gid"] == SUBTASK_1_GID
            and b["data"][0]["parent"]["gid"] == TASK_1_GID
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 11. Subtasks (task without subtasks)
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/tasks/{gid}/subtasks (no subtasks)",
        "GET", f"/api/1.0/tasks/{TASK_2_GID}/subtasks",
        expect_check=lambda b: (
            isinstance(b.get("data"), list)
            and len(b["data"]) == 0
            and b.get("next_page") is None
        ),
    )

    # -----------------------------------------------------------------------
    # 12. PATCH task
    # -----------------------------------------------------------------------
    patch_body = json.dumps({"data": {"name": "Updated task name"}}).encode()
    check(
        "PATCH /api/1.0/tasks/{gid}",
        "PATCH", f"/api/1.0/tasks/{TASK_1_GID}",
        body=patch_body,
        expect_check=lambda b: (
            b.get("data", {}).get("name") == "Updated task name"
            and b["data"].get("gid") == TASK_1_GID
        ),
    )

    # -----------------------------------------------------------------------
    # 13. POST sections/{gid}/addTask
    # -----------------------------------------------------------------------
    add_body = json.dumps({"data": {"task": TASK_1_GID}}).encode()
    check(
        "POST /api/1.0/sections/{gid}/addTask",
        "POST", f"/api/1.0/sections/{SEC_DONE_1}/addTask",
        body=add_body,
        expect_check=lambda b: "data" in b,
    )

    # -----------------------------------------------------------------------
    # 14. 404 for unknown project
    # -----------------------------------------------------------------------
    check(
        "GET /api/1.0/projects/unknown → 404",
        "GET", "/api/1.0/projects/unknown",
        expect_status=404,
        expect_check=lambda b: "errors" in b,
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n[selftest] {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


# ---------------------------------------------------------------------------
# Selftest plumbing — fake request handler for in-process testing
# ---------------------------------------------------------------------------

class _FakeRequestFile:
    """Minimal file-like object wrapping bytes for rfile simulation."""

    def __init__(self, data: bytes = b"") -> None:
        self._stream = io.BytesIO(data)

    def read(self, n: int = -1) -> bytes:
        return self._stream.read(n)


class _FakeWFile:
    """Captures written bytes for response inspection."""

    def __init__(self) -> None:
        self.data = b""

    def write(self, data: bytes) -> None:
        self.data += data


def _make_fake_handler(
    method: str,
    path: str,
    body: bytes | None = None,
    auth: bool = True,
):
    """Construct a MockAsanaHandler for selftest without a real socket."""
    import email

    class SilentHandler(MockAsanaHandler):
        """Subclass that captures response instead of writing to a socket."""

        def __init__(self):
            self.rfile = _FakeRequestFile(body or b"")
            self.wfile = _FakeWFile()
            self._headers_buffer = []
            self.requestline = f"{method} {path} HTTP/1.1"
            self.request_version = "HTTP/1.1"
            self.command = method
            self.path = path
            self.close_connection = True
            self._test_status = None
            self._test_body = None

            # Build headers
            header_text = "Host: localhost\r\n"
            if auth:
                header_text += f"Authorization: Bearer {VALID_TOKEN}\r\n"
            if body:
                header_text += (
                    f"Content-Length: {len(body)}\r\n"
                    f"Content-Type: application/json\r\n"
                )
            self.headers = email.message_from_string(header_text)

        def send_response(self, code, message=None):
            self._test_status = code

        def send_header(self, keyword, value):
            pass

        def end_headers(self):
            pass

        def _send_json(self, body, status=200):
            self._test_status = status
            self._test_body = body

        def _log(self, method, path, status):
            pass

        def log_message(self, fmt, *args):
            pass

    handler = SilentHandler()

    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()
    elif method == "PATCH":
        handler.do_PATCH()

    return handler


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(
        f"[mock-asana] Starting on port {PORT}...",
        file=sys.stderr, flush=True,
    )
    server = HTTPServer(("0.0.0.0", PORT), MockAsanaHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-asana] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()

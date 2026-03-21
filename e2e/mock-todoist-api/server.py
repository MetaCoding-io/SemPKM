"""Mock Todoist REST API v2 server for E2E testing.

A lightweight HTTP server returning canned REST responses based on URL
path matching.  Designed to run inside Docker alongside the SemPKM test
stack so the TodoistClient can be redirected here via TODOIST_API_URL.

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

PORT = 8080
VALID_TOKEN = "test-todoist-pat-token-abc123"

# ---------------------------------------------------------------------------
# Canned response data
# ---------------------------------------------------------------------------

PROJECTS_RESPONSE = [
    {"id": "100001", "name": "Work", "color": "berry_red"},
    {"id": "100002", "name": "Personal", "color": "blue"},
]

TASKS_RESPONSE = [
    {
        "id": "200001",
        "content": "Review quarterly report",
        "description": "Check all figures before the board meeting",
        "project_id": "100001",
        "priority": 4,
        "is_completed": False,
        "labels": ["urgent", "finance"],
        "due": {"date": "2026-03-25", "is_recurring": False, "string": "Mar 25"},
        "url": "https://todoist.com/showTask?id=200001",
        "created_at": "2026-03-01T10:00:00Z",
        "creator_id": "12345",
    },
    {
        "id": "200002",
        "content": "Buy groceries",
        "description": "",
        "project_id": "100002",
        "priority": 1,
        "is_completed": False,
        "labels": [],
        "due": None,
        "url": "https://todoist.com/showTask?id=200002",
        "created_at": "2026-03-10T08:00:00Z",
        "creator_id": "12345",
    },
]

LABELS_RESPONSE = [
    {"id": "300001", "name": "urgent", "color": "red"},
    {"id": "300002", "name": "finance", "color": "yellow"},
]

# Base task data keyed by task ID for PATCH/update merging.
_TASKS_BY_ID = {task["id"]: dict(task) for task in TASKS_RESPONSE}

# Counter for new task IDs.
_next_task_id = 300001


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockTodoistHandler(BaseHTTPRequestHandler):
    """Handles GET and POST requests mimicking the Todoist REST API v2."""

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        # Health endpoint — no auth required.
        if path == "/health":
            self._json_response(200, {"status": "ok"})
            self._log_request("GET", path, 200)
            return

        if not self._check_auth():
            return

        if path == "/rest/v2/projects":
            self._json_response(200, PROJECTS_RESPONSE)
            self._log_request("GET", path, 200)
        elif path == "/rest/v2/tasks":
            self._json_response(200, TASKS_RESPONSE)
            self._log_request("GET", path, 200)
        elif path == "/rest/v2/labels":
            self._json_response(200, LABELS_RESPONSE)
            self._log_request("GET", path, 200)
        else:
            self._json_response(404, {"message": "Not Found"})
            self._log_request("GET", path, 404)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        if not self._check_auth():
            return

        # POST /rest/v2/tasks/{id}/close
        m = re.match(r"^/rest/v2/tasks/([^/]+)/close$", path)
        if m:
            self.send_response(204)
            self.end_headers()
            self._log_request("POST", path, 204)
            return

        # POST /rest/v2/tasks/{id}/reopen
        m = re.match(r"^/rest/v2/tasks/([^/]+)/reopen$", path)
        if m:
            self.send_response(204)
            self.end_headers()
            self._log_request("POST", path, 204)
            return

        # POST /rest/v2/tasks/{id} — update existing task
        m = re.match(r"^/rest/v2/tasks/([^/]+)$", path)
        if m:
            task_id = m.group(1)
            body = self._read_json_body()

            base = _TASKS_BY_ID.get(task_id)
            if base is None:
                self._json_response(404, {"message": "Not Found"})
                self._log_request("POST", path, 404)
                return

            result = dict(base)
            if body:
                result.update(body)
            self._json_response(200, result)
            self._log_request("POST", path, 200)
            return

        # POST /rest/v2/tasks — create new task
        if path == "/rest/v2/tasks":
            global _next_task_id
            body = self._read_json_body() or {}
            new_task = {
                "id": str(_next_task_id),
                "content": body.get("content", ""),
                "description": body.get("description", ""),
                "project_id": body.get("project_id", "100001"),
                "priority": body.get("priority", 1),
                "is_completed": False,
                "labels": body.get("labels", []),
                "due": body.get("due", None),
                "url": f"https://todoist.com/showTask?id={_next_task_id}",
                "created_at": "2026-03-19T12:00:00Z",
                "creator_id": "12345",
            }
            _next_task_id += 1
            self._json_response(200, new_task)
            self._log_request("POST", path, 200)
            return

        self._json_response(404, {"message": "Not Found"})
        self._log_request("POST", path, 404)

    # -- helpers --

    def _check_auth(self) -> bool:
        """Validate Authorization header. Returns True if valid, sends 401 if not."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != VALID_TOKEN:
            self._json_response(401, {"message": "Unauthorized"})
            self._log_request(self.command, self.path, 401)
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

    def _json_response(self, status: int, body: dict | list) -> None:
        """Write a JSON response with Content-Type header."""
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _log_request(self, method: str, path: str, status: int) -> None:
        print(f"[mock-todoist] {method} {path} → {status}", file=sys.stderr, flush=True)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-todoist] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Simulate requests against all endpoints, verify responses, exit."""
    print("[selftest] Starting mock Todoist API self-test...")

    passed = 0
    failed = 0

    def check(name: str, method: str, path: str, body: bytes | None = None,
              auth: bool = True, expect_status: int = 200,
              expect_check=None):
        nonlocal passed, failed

        handler = _make_fake_handler(method, path, body, auth=auth)
        actual_status = handler._test_status

        if actual_status != expect_status:
            print(f"  [selftest] FAIL: {name} — expected {expect_status}, got {actual_status}")
            failed += 1
            return

        if expect_check and not expect_check(handler._test_body):
            print(f"  [selftest] FAIL: {name} — response body check failed")
            failed += 1
            return

        print(f"  ✓ {name}")
        passed += 1

    # -- GET endpoints --
    check("GET /health (no auth)", "GET", "/health", auth=False,
          expect_check=lambda b: b.get("status") == "ok")

    check("GET /rest/v2/projects", "GET", "/rest/v2/projects",
          expect_check=lambda b: isinstance(b, list) and len(b) == 2
          and b[0]["name"] == "Work")

    check("GET /rest/v2/tasks", "GET", "/rest/v2/tasks",
          expect_check=lambda b: isinstance(b, list) and len(b) == 2
          and b[0]["content"] == "Review quarterly report")

    check("GET /rest/v2/labels", "GET", "/rest/v2/labels",
          expect_check=lambda b: isinstance(b, list) and len(b) == 2
          and b[0]["name"] == "urgent")

    # -- Auth failure --
    check("GET /rest/v2/tasks without auth → 401", "GET", "/rest/v2/tasks",
          auth=False, expect_status=401)

    # -- POST endpoints --
    check("POST /rest/v2/tasks/200001/close → 204", "POST",
          "/rest/v2/tasks/200001/close", expect_status=204)

    check("POST /rest/v2/tasks/200001/reopen → 204", "POST",
          "/rest/v2/tasks/200001/reopen", expect_status=204)

    # -- Update task --
    update_body = json.dumps({"content": "Updated report task"}).encode()
    check("POST /rest/v2/tasks/200001 (update)", "POST",
          "/rest/v2/tasks/200001", body=update_body,
          expect_check=lambda b: b.get("content") == "Updated report task"
          and b.get("id") == "200001")

    # -- Create task --
    create_body = json.dumps({"content": "New task from test", "priority": 3}).encode()
    check("POST /rest/v2/tasks (create)", "POST",
          "/rest/v2/tasks", body=create_body,
          expect_check=lambda b: b.get("content") == "New task from test"
          and b.get("priority") == 3 and "id" in b)

    # -- Projects response content validation --
    check("Projects response has correct IDs", "GET", "/rest/v2/projects",
          expect_check=lambda b: b[0]["id"] == "100001" and b[1]["id"] == "100002")

    # -- Summary --
    print(f"\n[selftest] {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


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


def _make_fake_handler(method: str, path: str, body: bytes | None = None,
                       auth: bool = True):
    """Construct a MockTodoistHandler for selftest without a real socket."""
    import email

    class SilentHandler(MockTodoistHandler):
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
                header_text += f"Content-Length: {len(body)}\r\nContent-Type: application/json\r\n"
            self.headers = email.message_from_string(header_text)

        def send_response(self, code, message=None):
            self._test_status = code

        def send_header(self, keyword, value):
            pass

        def end_headers(self):
            pass

        def _json_response(self, status, body):
            self._test_status = status
            self._test_body = body

        def _log_request(self, method, path, status):
            pass

        def log_message(self, fmt, *args):
            pass

    handler = SilentHandler()

    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()

    return handler


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-todoist] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockTodoistHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-todoist] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()

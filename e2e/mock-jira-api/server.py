"""Mock Jira REST API server for E2E testing.

A lightweight HTTP server returning canned REST responses based on URL
path matching.  Designed to run inside Docker alongside the SemPKM test
stack so the JiraClient can be redirected here via JIRA_API_URL.

Endpoints served (matching ``apps/jira-sync/services/jira_client.py``):
    GET  /health                       → liveness check
    GET  /rest/api/3/myself            → authenticated user profile
    GET  /rest/api/3/project           → list of accessible projects
    POST /rest/api/3/search            → JQL issue search (JSON body)
    GET  /rest/api/3/user?accountId=X  → user lookup by account ID
    GET  /rest/api/3/issue/{key}       → single issue by key
    PUT  /rest/api/3/issue/{key}       → update issue fields (JSON body)

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import copy
import io
import json
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8080

# ---------------------------------------------------------------------------
# Canned response data
# ---------------------------------------------------------------------------

MYSELF_RESPONSE = {
    "accountId": "user-abc-123",
    "displayName": "Test User",
    "emailAddress": "test@example.com",
    "active": True,
}

PROJECTS_RESPONSE = [
    {
        "id": "10000",
        "key": "PROJ",
        "name": "Test Project",
        "projectTypeKey": "software",
    },
    {
        "id": "10001",
        "key": "DESIGN",
        "name": "Design Team",
        "projectTypeKey": "software",
    },
]

USER_RESPONSE = {
    "accountId": "user-abc-123",
    "displayName": "Test User",
    "emailAddress": "test@example.com",
    "active": True,
}

# -- Individual issues (Jira REST API v3 nested fields format) -------------

ISSUE_1 = {
    "id": "10001",
    "key": "PROJ-1",
    "self": "http://localhost:8080/rest/api/3/issue/10001",
    "fields": {
        "summary": "Fix login page crash on mobile",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "The login page throws an error on iOS Safari.",
                        }
                    ],
                }
            ],
        },
        "status": {
            "name": "In Progress",
            "statusCategory": {"key": "indeterminate"},
        },
        "issuetype": {"name": "Bug"},
        "priority": {"name": "High"},
        "assignee": {
            "accountId": "user-abc-123",
            "displayName": "Test User",
        },
        "labels": ["bug", "mobile"],
        "components": [{"name": "Frontend"}],
        "created": "2026-03-01T10:00:00.000+0000",
        "updated": "2026-03-15T14:30:00.000+0000",
        "sprint": {"name": "Sprint 5", "state": "active"},
        "issuelinks": [
            {
                "type": {
                    "name": "Blocks",
                    "inward": "is blocked by",
                    "outward": "blocks",
                },
                "inwardIssue": {
                    "key": "PROJ-3",
                    "id": "10003",
                    "fields": {
                        "summary": "Platform migration epic",
                        "issuetype": {"name": "Epic"},
                    },
                },
            }
        ],
    },
}

ISSUE_2 = {
    "id": "10002",
    "key": "PROJ-2",
    "self": "http://localhost:8080/rest/api/3/issue/10002",
    "fields": {
        "summary": "Add dark mode support",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Users want dark mode.",
                        }
                    ],
                }
            ],
        },
        "status": {
            "name": "To Do",
            "statusCategory": {"key": "new"},
        },
        "issuetype": {"name": "Story"},
        "priority": {"name": "Medium"},
        "assignee": None,
        "labels": [],
        "components": [],
        "created": "2026-03-02T09:00:00.000+0000",
        "updated": "2026-03-14T11:00:00.000+0000",
        "sprint": None,
        "issuelinks": [],
    },
}

ISSUE_3 = {
    "id": "10003",
    "key": "PROJ-3",
    "self": "http://localhost:8080/rest/api/3/issue/10003",
    "fields": {
        "summary": "Platform migration epic",
        "description": None,
        "status": {
            "name": "Done",
            "statusCategory": {"key": "done"},
        },
        "issuetype": {"name": "Epic"},
        "priority": {"name": "Highest"},
        "assignee": {
            "accountId": "user-abc-123",
            "displayName": "Test User",
        },
        "labels": ["epic", "migration"],
        "components": [{"name": "Backend"}],
        "created": "2026-03-01T08:00:00.000+0000",
        "updated": "2026-03-18T10:00:00.000+0000",
        "sprint": None,
        "issuelinks": [],
    },
}

ISSUES_LIST = [ISSUE_1, ISSUE_2, ISSUE_3]

SEARCH_RESPONSE = {
    "startAt": 0,
    "maxResults": 50,
    "total": 3,
    "issues": ISSUES_LIST,
}

# Lookup dicts for GET /issue/{key} and PUT /issue/{key}
_ISSUES_BY_KEY: dict[str, dict] = {issue["key"]: issue for issue in ISSUES_LIST}

# Issue key pattern: /rest/api/3/issue/{KEY}
_ISSUE_PATH_RE = re.compile(r"^/rest/api/3/issue/([A-Z]+-\d+)$")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockJiraHandler(BaseHTTPRequestHandler):
    """Handles GET, POST, and PUT requests mimicking the Jira REST API v3."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._json_response(200, {"status": "ok"})

        elif path == "/rest/api/3/myself":
            self._json_response(200, MYSELF_RESPONSE)

        elif path == "/rest/api/3/project":
            self._json_response(200, PROJECTS_RESPONSE)

        elif path == "/rest/api/3/user":
            account_ids = qs.get("accountId", [])
            if account_ids and account_ids[0] == "user-abc-123":
                self._json_response(200, USER_RESPONSE)
            else:
                self._json_response(404, {"message": "Not Found"})

        else:
            # Check for /rest/api/3/issue/{key}
            match = _ISSUE_PATH_RE.match(path)
            if match:
                issue_key = match.group(1)
                issue = _ISSUES_BY_KEY.get(issue_key)
                if issue:
                    self._json_response(200, issue)
                else:
                    self._json_response(404, {"message": "Not Found"})
            else:
                self._json_response(404, {"message": "Not Found"})

        self._log_request("GET", self.path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/rest/api/3/search":
            # Read and parse JSON body
            content_length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(content_length)
            try:
                body = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, ValueError):
                self._json_response(400, {"message": "Invalid JSON"})
                self._log_request("POST", self.path)
                return

            # Extract pagination params (ignored for mock — always return all)
            _jql = body.get("jql", "")
            _start_at = body.get("startAt", 0)
            _max_results = body.get("maxResults", 50)

            self._json_response(200, SEARCH_RESPONSE)
        else:
            self._json_response(404, {"message": "Not Found"})

        self._log_request("POST", self.path)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        match = _ISSUE_PATH_RE.match(path)
        if not match:
            self._json_response(404, {"message": "Not Found"})
            self._log_request("PUT", self.path)
            return

        issue_key = match.group(1)
        base_issue = _ISSUES_BY_KEY.get(issue_key)
        if base_issue is None:
            self._json_response(404, {"message": "Not Found"})
            self._log_request("PUT", self.path)
            return

        # Read and parse JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)
        try:
            body = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            self._json_response(400, {"message": "Invalid JSON"})
            self._log_request("PUT", self.path)
            return

        # Merge patch fields into a deep copy of the base issue
        result = copy.deepcopy(base_issue)
        patch_fields = body.get("fields", {})
        result["fields"].update(patch_fields)
        result["fields"]["updated"] = "2026-03-19T12:00:00.000+0000"

        self._json_response(200, result)
        self._log_request("PUT", self.path)

    # -- helpers --

    def _json_response(self, status: int, body: dict | list) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _log_request(self, method: str, path: str) -> None:
        print(f"[mock-jira] {method} {path}", file=sys.stderr, flush=True)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-jira] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Simulate requests against all endpoints, verify responses, exit."""
    print("[selftest] Starting mock Jira API self-test...")

    passed = 0
    failed = 0

    def check(
        name: str,
        method: str,
        path: str,
        body: bytes | None = None,
        expect_status: int = 200,
        expect_check=None,
    ):
        nonlocal passed, failed

        handler = _make_fake_handler(method, path, body)
        actual_status = handler._test_status

        if actual_status != expect_status:
            print(f"  ✗ {name}: expected {expect_status}, got {actual_status}")
            failed += 1
            return

        if expect_check and not expect_check(handler._test_body):
            print(f"  ✗ {name}: response body check failed")
            print(f"    body: {json.dumps(handler._test_body, indent=2)[:200]}")
            failed += 1
            return

        print(f"  ✓ {name}")
        passed += 1

    # -- GET endpoints --

    check(
        "GET /health",
        "GET",
        "/health",
        expect_check=lambda b: b.get("status") == "ok",
    )

    check(
        "GET /rest/api/3/myself",
        "GET",
        "/rest/api/3/myself",
        expect_check=lambda b: b.get("accountId") == "user-abc-123",
    )

    check(
        "GET /rest/api/3/project",
        "GET",
        "/rest/api/3/project",
        expect_check=lambda b: isinstance(b, list) and len(b) == 2,
    )

    check(
        "GET /rest/api/3/user?accountId=user-abc-123",
        "GET",
        "/rest/api/3/user?accountId=user-abc-123",
        expect_check=lambda b: b.get("displayName") == "Test User",
    )

    check(
        "GET /rest/api/3/user?accountId=unknown → 404",
        "GET",
        "/rest/api/3/user?accountId=unknown-id",
        expect_status=404,
    )

    check(
        "GET /rest/api/3/issue/PROJ-1",
        "GET",
        "/rest/api/3/issue/PROJ-1",
        expect_check=lambda b: (
            b.get("key") == "PROJ-1"
            and len(b.get("fields", {}).get("issuelinks", [])) == 1
            and b["fields"]["issuelinks"][0]["type"]["name"] == "Blocks"
            and b["fields"]["issuelinks"][0]["inwardIssue"]["key"] == "PROJ-3"
        ),
    )

    check(
        "GET /rest/api/3/issue/PROJ-3 (Epic)",
        "GET",
        "/rest/api/3/issue/PROJ-3",
        expect_check=lambda b: (
            b.get("key") == "PROJ-3"
            and b.get("fields", {}).get("issuetype", {}).get("name") == "Epic"
        ),
    )

    check(
        "GET /rest/api/3/issue/UNKNOWN-99 → 404",
        "GET",
        "/rest/api/3/issue/UNKNOWN-99",
        expect_status=404,
    )

    # -- POST endpoint --

    search_body = json.dumps({
        "jql": "project = PROJ ORDER BY updated DESC",
        "startAt": 0,
        "maxResults": 50,
        "fields": ["*all"],
    }).encode()
    check(
        "POST /rest/api/3/search",
        "POST",
        "/rest/api/3/search",
        body=search_body,
        expect_check=lambda b: (
            b.get("total") == 3
            and len(b.get("issues", [])) == 3
            and b["issues"][0]["key"] == "PROJ-1"
            and b["issues"][1]["key"] == "PROJ-2"
            and b["issues"][2]["key"] == "PROJ-3"
        ),
    )

    # -- PUT endpoint --

    put_body = json.dumps({
        "fields": {"summary": "Updated summary"},
    }).encode()
    check(
        "PUT /rest/api/3/issue/PROJ-1",
        "PUT",
        "/rest/api/3/issue/PROJ-1",
        body=put_body,
        expect_check=lambda b: (
            b.get("key") == "PROJ-1"
            and b.get("fields", {}).get("summary") == "Updated summary"
            and b["fields"].get("updated") == "2026-03-19T12:00:00.000+0000"
            # Verify original fields are preserved
            and b["fields"].get("priority", {}).get("name") == "High"
        ),
    )

    put_body_unknown = json.dumps({"fields": {"summary": "X"}}).encode()
    check(
        "PUT /rest/api/3/issue/UNKNOWN-1 → 404",
        "PUT",
        "/rest/api/3/issue/UNKNOWN-1",
        body=put_body_unknown,
        expect_status=404,
    )

    # -- 404 for unknown path --

    check(
        "GET /unknown → 404",
        "GET",
        "/unknown/path",
        expect_status=404,
    )

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


def _make_fake_handler(method: str, path: str, body: bytes | None = None):
    """Construct a MockJiraHandler for selftest without a real socket."""
    import email

    class SilentHandler(MockJiraHandler):
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

            # Parse headers from the raw request
            header_text = ""
            if body:
                header_text = (
                    f"Content-Length: {len(body)}\r\n"
                    f"Content-Type: application/json\r\n"
                )
            header_text += "Host: localhost\r\n"
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

        def _log_request(self, method, path):
            pass

        def log_message(self, fmt, *args):
            pass

    handler = SilentHandler()

    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()
    elif method == "PUT":
        handler.do_PUT()

    return handler


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-jira] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockJiraHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-jira] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()

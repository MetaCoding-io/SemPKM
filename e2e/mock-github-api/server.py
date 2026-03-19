"""Mock GitHub REST API server for E2E testing.

A lightweight HTTP server returning canned REST responses based on URL
path matching.  Designed to run inside Docker alongside the SemPKM test
stack so the GitHubClient can be redirected here via GITHUB_API_URL.

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import io
import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8080

# ---------------------------------------------------------------------------
# Canned response data
# ---------------------------------------------------------------------------

USER_RESPONSE = {
    "login": "test-user",
    "id": 12345,
    "name": "Test User",
    "email": "test@example.com",
}

REPOS_RESPONSE = [
    {
        "id": 100,
        "full_name": "test-owner/test-repo",
        "name": "test-repo",
        "private": False,
        "has_issues": True,
        "owner": {"login": "test-owner"},
        "html_url": "https://github.com/test-owner/test-repo",
        "updated_at": "2026-03-15T12:00:00Z",
    },
    {
        "id": 101,
        "full_name": "test-owner/empty-repo",
        "name": "empty-repo",
        "private": True,
        "has_issues": True,
        "owner": {"login": "test-owner"},
        "html_url": "https://github.com/test-owner/empty-repo",
        "updated_at": "2026-03-10T08:00:00Z",
    },
]

ISSUES_RESPONSE = [
    {
        "id": 1001,
        "number": 1,
        "title": "Fix login page crash on mobile",
        "body": "The login page throws an unhandled exception on iOS Safari when the keyboard appears.",
        "state": "open",
        "html_url": "https://github.com/test-owner/test-repo/issues/1",
        "user": {"login": "test-user", "id": 12345},
        "assignee": {"login": "test-user", "email": "test@example.com"},
        "assignees": [{"login": "test-user", "email": "test@example.com"}],
        "labels": [
            {"id": 501, "name": "bug"},
            {"id": 502, "name": "priority-high"},
        ],
        "milestone": {"id": 1, "title": "v1.0", "state": "open"},
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-15T14:30:00Z",
        "closed_at": None,
    },
    {
        "id": 1002,
        "number": 2,
        "title": "Add dark mode support",
        "body": "Users have requested a dark mode toggle in settings.",
        "state": "closed",
        "state_reason": "completed",
        "html_url": "https://github.com/test-owner/test-repo/issues/2",
        "user": {"login": "test-user", "id": 12345},
        "assignee": None,
        "assignees": [],
        "labels": [],
        "milestone": None,
        "created_at": "2026-03-02T09:00:00Z",
        "updated_at": "2026-03-14T11:00:00Z",
        "closed_at": "2026-03-14T11:00:00Z",
    },
    {
        "id": 1003,
        "number": 3,
        "title": "Refactor auth module to use JWT",
        "body": "Migrate from session-based auth to JWT tokens for API endpoints.",
        "state": "open",
        "html_url": "https://github.com/test-owner/test-repo/pull/3",
        "user": {"login": "test-user", "id": 12345},
        "assignee": None,
        "assignees": [],
        "labels": [{"id": 503, "name": "enhancement"}],
        "milestone": None,
        "pull_request": {
            "url": "https://api.github.com/repos/test-owner/test-repo/pulls/3",
            "html_url": "https://github.com/test-owner/test-repo/pull/3",
        },
        "created_at": "2026-03-05T08:00:00Z",
        "updated_at": "2026-03-16T16:00:00Z",
        "closed_at": None,
    },
]

# Timeline for issue #1 — cross-referenced by PR #3.
TIMELINE_ISSUE_1 = [
    {
        "id": 9001,
        "event": "cross-referenced",
        "created_at": "2026-03-06T12:00:00Z",
        "source": {
            "type": "issue",
            "issue": {
                "number": 3,
                "title": "Refactor auth module to use JWT",
                "html_url": "https://github.com/test-owner/test-repo/pull/3",
                "pull_request": {
                    "url": "https://api.github.com/repos/test-owner/test-repo/pulls/3",
                    "html_url": "https://github.com/test-owner/test-repo/pull/3",
                },
                "repository": {
                    "full_name": "test-owner/test-repo",
                },
            },
        },
    },
]

# Base issue data for PATCH responses, keyed by issue number.
_ISSUES_BY_NUMBER = {issue["number"]: dict(issue) for issue in ISSUES_RESPONSE}


def _make_rate_limit_headers() -> dict[str, str]:
    """Rate-limit headers that prevent the client from sleeping."""
    return {
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Reset": str(int(time.time()) + 3600),
    }


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockGitHubHandler(BaseHTTPRequestHandler):
    """Handles GET and PATCH requests mimicking the GitHub REST API v3."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._json_response(200, {"status": "ok"})
        elif path == "/user":
            self._json_response(200, USER_RESPONSE)
        elif path == "/user/repos":
            self._json_response(200, REPOS_RESPONSE)
        elif path == "/repos/test-owner/test-repo/issues":
            self._json_response(200, ISSUES_RESPONSE)
        elif path.startswith("/repos/test-owner/test-repo/issues/") and path.endswith("/timeline"):
            # Extract issue number from /repos/{owner}/{repo}/issues/{n}/timeline
            parts = path.split("/")
            try:
                issue_num = int(parts[5])
            except (IndexError, ValueError):
                self._json_response(404, {"message": "Not Found"})
                return
            if issue_num == 1:
                self._json_response(200, TIMELINE_ISSUE_1)
            else:
                self._json_response(200, [])
        else:
            self._json_response(404, {"message": "Not Found"})

        self._log_request("GET", path, 200 if path != "" else 404)

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Match /repos/test-owner/test-repo/issues/{n}
        parts = path.split("/")
        if (
            len(parts) == 6
            and parts[1] == "repos"
            and parts[2] == "test-owner"
            and parts[3] == "test-repo"
            and parts[4] == "issues"
        ):
            try:
                issue_num = int(parts[5])
            except ValueError:
                self._json_response(404, {"message": "Not Found"})
                return

            base = _ISSUES_BY_NUMBER.get(issue_num)
            if base is None:
                self._json_response(404, {"message": "Not Found"})
                return

            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(content_length)
            try:
                patch_data = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, ValueError):
                self._json_response(400, {"message": "Invalid JSON"})
                return

            # Merge patched fields into a copy of the base issue
            result = dict(base)
            result.update(patch_data)
            result["updated_at"] = "2026-03-18T12:00:00Z"

            self._json_response(200, result)
            self._log_request("PATCH", path, 200)
        else:
            self._json_response(404, {"message": "Not Found"})
            self._log_request("PATCH", path, 404)

    # -- helpers --

    def _json_response(self, status: int, body: dict | list) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        # Rate-limit headers on every response
        for key, value in _make_rate_limit_headers().items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def _log_request(self, method: str, path: str, status: int) -> None:
        print(f"[mock-github] {method} {path} → {status}", file=sys.stderr, flush=True)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-github] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Simulate requests against all endpoints, verify responses, exit."""
    print("[selftest] Starting mock GitHub API self-test...")

    passed = 0
    failed = 0

    def check(name: str, method: str, path: str, body: bytes | None = None,
              expect_status: int = 200, expect_check=None):
        nonlocal passed, failed

        # Build a fake request via the handler
        handler = _make_fake_handler(method, path, body)
        actual_status = handler._test_status

        if actual_status != expect_status:
            print(f"  ✗ {name}: expected {expect_status}, got {actual_status}")
            failed += 1
            return

        if expect_check and not expect_check(handler._test_body):
            print(f"  ✗ {name}: response body check failed")
            failed += 1
            return

        print(f"  ✓ {name}")
        passed += 1

    # -- GET endpoints --
    check("GET /health", "GET", "/health",
          expect_check=lambda b: b.get("status") == "ok")

    check("GET /user", "GET", "/user",
          expect_check=lambda b: b.get("login") == "test-user")

    check("GET /user/repos", "GET", "/user/repos",
          expect_check=lambda b: isinstance(b, list) and len(b) == 2)

    check("GET /repos/.../issues", "GET",
          "/repos/test-owner/test-repo/issues?state=all",
          expect_check=lambda b: isinstance(b, list) and len(b) == 3)

    check("GET /repos/.../issues/1/timeline", "GET",
          "/repos/test-owner/test-repo/issues/1/timeline",
          expect_check=lambda b: isinstance(b, list) and len(b) == 1 and b[0]["event"] == "cross-referenced")

    check("GET /repos/.../issues/2/timeline", "GET",
          "/repos/test-owner/test-repo/issues/2/timeline",
          expect_check=lambda b: isinstance(b, list) and len(b) == 0)

    check("GET /repos/.../issues/3/timeline", "GET",
          "/repos/test-owner/test-repo/issues/3/timeline",
          expect_check=lambda b: isinstance(b, list) and len(b) == 0)

    # -- PATCH endpoint --
    patch_body = json.dumps({"title": "Updated title", "state": "closed"}).encode()
    check("PATCH /repos/.../issues/1", "PATCH",
          "/repos/test-owner/test-repo/issues/1",
          body=patch_body,
          expect_check=lambda b: b.get("title") == "Updated title" and b.get("state") == "closed")

    # -- 404 for unknown path --
    check("GET /unknown → 404", "GET", "/unknown/path", expect_status=404)

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
    """Construct a MockGitHubHandler for selftest without a real socket."""
    import email

    # Build a minimal HTTP request line + headers
    raw_request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n"
    if body:
        raw_request += f"Content-Length: {len(body)}\r\nContent-Type: application/json\r\n"
    raw_request += "\r\n"

    rfile_data = raw_request.encode() + (body or b"")

    class SilentHandler(MockGitHubHandler):
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
                header_text = f"Content-Length: {len(body)}\r\nContent-Type: application/json\r\n"
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
            # Still include rate-limit check conceptually, but skip actual header writes
            return

        def _log_request(self, method, path, status):
            pass

        def log_message(self, fmt, *args):
            pass

    handler = SilentHandler()

    if method == "GET":
        handler.do_GET()
    elif method == "PATCH":
        handler.do_PATCH()

    return handler


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-github] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockGitHubHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-github] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()

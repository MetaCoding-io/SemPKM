"""Mock Linear GraphQL API server for E2E testing.

A lightweight HTTP server returning canned GraphQL responses based on
substring matching against the incoming query. Designed to run inside
Docker alongside the SemPKM test stack.

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

# ---------------------------------------------------------------------------
# Canned responses keyed by query substring (checked in order)
# ---------------------------------------------------------------------------

VIEWER_RESPONSE = {
    "data": {
        "viewer": {
            "id": "user-mock-001",
            "name": "Test User",
            "email": "test@example.com",
        }
    }
}

ORGANIZATION_RESPONSE = {
    "data": {
        "organization": {
            "id": "org-mock-001",
            "name": "Test Workspace",
            "urlKey": "test-ws",
        }
    }
}

TEAMS_RESPONSE = {
    "data": {
        "teams": {
            "nodes": [
                {
                    "id": "team-mock-001",
                    "name": "Engineering",
                    "key": "ENG",
                    "description": "Engineering team",
                },
                {
                    "id": "team-mock-002",
                    "name": "Design",
                    "key": "DES",
                    "description": "Design team",
                },
            ]
        }
    }
}

STATES_RESPONSE = {
    "data": {
        "team": {
            "states": {
                "nodes": [
                    {"id": "state-triage", "name": "Triage", "type": "triage"},
                    {"id": "state-backlog", "name": "Backlog", "type": "backlog"},
                    {"id": "state-todo", "name": "Todo", "type": "unstarted"},
                    {"id": "state-progress", "name": "In Progress", "type": "started"},
                    {"id": "state-done", "name": "Done", "type": "completed"},
                    {"id": "state-canceled", "name": "Canceled", "type": "canceled"},
                ]
            }
        }
    }
}

ISSUES_RESPONSE = {
    "data": {
        "issues": {
            "nodes": [
                {
                    "id": "issue-mock-001",
                    "identifier": "ENG-1",
                    "title": "Implement user authentication",
                    "description": "Add login and signup flows to the application.",
                    "priority": 1,
                    "dueDate": "2026-04-15",
                    "url": "https://linear.app/test-ws/issue/ENG-1",
                    "createdAt": "2026-03-01T10:00:00.000Z",
                    "updatedAt": "2026-03-15T14:30:00.000Z",
                    "state": {"id": "state-progress", "name": "In Progress", "type": "started"},
                    "assignee": {"id": "user-mock-001", "name": "Test User", "email": "test@example.com"},
                    "labels": {"nodes": [{"id": "label-1", "name": "feature"}]},
                    "team": {"id": "team-mock-001", "name": "Engineering", "key": "ENG"},
                },
                {
                    "id": "issue-mock-002",
                    "identifier": "ENG-2",
                    "title": "Fix dashboard performance",
                    "description": "Dashboard loads slowly with large datasets.",
                    "priority": 2,
                    "dueDate": "2026-04-01",
                    "url": "https://linear.app/test-ws/issue/ENG-2",
                    "createdAt": "2026-03-02T09:00:00.000Z",
                    "updatedAt": "2026-03-14T11:00:00.000Z",
                    "state": {"id": "state-todo", "name": "Todo", "type": "unstarted"},
                    "assignee": None,
                    "labels": {"nodes": [{"id": "label-2", "name": "bug"}]},
                    "team": {"id": "team-mock-001", "name": "Engineering", "key": "ENG"},
                },
                {
                    "id": "issue-mock-003",
                    "identifier": "ENG-3",
                    "title": "Write API documentation",
                    "description": "Document all REST and GraphQL endpoints.",
                    "priority": 3,
                    "dueDate": None,
                    "url": "https://linear.app/test-ws/issue/ENG-3",
                    "createdAt": "2026-03-05T08:00:00.000Z",
                    "updatedAt": "2026-03-10T16:00:00.000Z",
                    "state": {"id": "state-done", "name": "Done", "type": "completed"},
                    "assignee": {"id": "user-mock-001", "name": "Test User", "email": "test@example.com"},
                    "labels": {"nodes": []},
                    "team": {"id": "team-mock-001", "name": "Engineering", "key": "ENG"},
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "endCursor": None,
            },
        }
    }
}

ISSUE_UPDATE_RESPONSE = {
    "data": {
        "issueUpdate": {
            "success": True,
            "issue": {
                "id": "issue-mock-001",
                "updatedAt": "2026-03-18T12:00:00.000Z",
            },
        }
    }
}

# Order matters — more specific substrings first.
QUERY_MATCHERS: list[tuple[str, str, dict]] = [
    ("issueUpdate", "issueUpdate (mutation)", ISSUE_UPDATE_RESPONSE),
    ("states",      "states",                 STATES_RESPONSE),
    ("issues",      "issues",                 ISSUES_RESPONSE),
    ("teams",       "teams",                  TEAMS_RESPONSE),
    ("organization","organization",           ORGANIZATION_RESPONSE),
    ("viewer",      "viewer",                 VIEWER_RESPONSE),
]

# Default fallback for unrecognised queries
FALLBACK_RESPONSE = {"data": {}}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockLinearHandler(BaseHTTPRequestHandler):
    """Handles POST /graphql and GET /health."""

    def do_GET(self) -> None:  # noqa: N802
        """Health-check endpoint for Docker healthcheck."""
        if self.path in ("/", "/health"):
            self._json_response(200, {"status": "ok"})
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        """GraphQL endpoint — matches query substring to canned response."""
        if self.path not in ("/graphql", "/graphql/"):
            self._json_response(404, {"error": "not found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            self._json_response(400, {"errors": [{"message": "Invalid JSON body"}]})
            return

        query = body.get("query", "")

        for substring, label, response in QUERY_MATCHERS:
            if substring in query:
                print(f"[mock-linear] Matched query type: {label}", flush=True)
                self._json_response(200, response)
                return

        print(f"[mock-linear] Unmatched query (fallback): {query[:120]}", flush=True)
        self._json_response(200, FALLBACK_RESPONSE)

    # -- helpers --

    def _json_response(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs."""
        print(f"[mock-linear] {fmt % args}", flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Verify all canned responses are well-formed JSON, then exit."""
    print("[selftest] Checking canned responses...")
    for substring, label, response in QUERY_MATCHERS:
        # Ensure round-trippable
        encoded = json.dumps(response)
        decoded = json.loads(encoded)
        assert "data" in decoded, f"{label}: missing 'data' key"
        print(f"  ✓ {label}")
    print("[selftest] All responses OK.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-linear] Starting on port {PORT}...", flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockLinearHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-linear] Shutting down.", flush=True)
        server.shutdown()

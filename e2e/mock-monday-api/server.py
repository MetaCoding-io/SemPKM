"""Mock Monday.com GraphQL API server for E2E testing.

A lightweight HTTP server returning canned GraphQL responses based on
substring matching against the incoming query text. Monday.com uses a
single POST endpoint at ``/`` (not ``/graphql``). Auth header is bare
``Authorization: <api_key>`` (no Bearer prefix).

Designed to run inside Docker alongside the SemPKM test stack so the
MondayClient can be redirected here via ``MONDAY_API_URL``.

Endpoints served (matching ``apps/monday-sync/services/monday_client.py``):
    GET  /health                → liveness check
    POST /                      → GraphQL query dispatch (10 query shapes)

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import io
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

# ---------------------------------------------------------------------------
# Canned responses — all wrapped in {"data": {...}}
# ---------------------------------------------------------------------------

# a. me query → user profile
ME_RESPONSE = {
    "data": {
        "me": {
            "id": "12345",
            "name": "Test User",
            "email": "test@example.com",
        }
    }
}

# b. boards(limit → board list
BOARDS_RESPONSE = {
    "data": {
        "boards": [
            {"id": "1001", "name": "Test Board", "state": "active"},
            {"id": "1002", "name": "Design Board", "state": "active"},
        ]
    }
}

# c. boards(ids: with columns → column schema with settings_str
# CRITICAL: settings_str values are JSON *strings* (double-encoded),
# exactly as Monday.com returns them.
BOARD_COLUMNS_RESPONSE = {
    "data": {
        "boards": [
            {
                "columns": [
                    {
                        "id": "status",
                        "title": "Status",
                        "type": "status",
                        "settings_str": '{"labels":{"1":"Working on it","2":"Done","3":"Stuck","4":"Waiting for review"}}',
                    },
                    {
                        "id": "priority",
                        "title": "Priority",
                        "type": "status",
                        "settings_str": '{"labels":{"1":"Critical","2":"High","3":"Medium","4":"Low"}}',
                    },
                    {
                        "id": "date0",
                        "title": "Due Date",
                        "type": "date",
                        "settings_str": "{}",
                    },
                    {
                        "id": "person",
                        "title": "Assignee",
                        "type": "people",
                        "settings_str": "{}",
                    },
                    {
                        "id": "text0",
                        "title": "Notes",
                        "type": "text",
                        "settings_str": "{}",
                    },
                    {
                        "id": "long_text",
                        "title": "Description",
                        "type": "long_text",
                        "settings_str": "{}",
                    },
                    {
                        "id": "numbers0",
                        "title": "Story Points",
                        "type": "numbers",
                        "settings_str": "{}",
                    },
                    {
                        "id": "tags0",
                        "title": "Tags",
                        "type": "tag",
                        "settings_str": "{}",
                    },
                    {
                        "id": "dropdown0",
                        "title": "Category",
                        "type": "dropdown",
                        "settings_str": "{}",
                    },
                    {
                        "id": "dependency0",
                        "title": "Dependencies",
                        "type": "dependency",
                        "settings_str": "{}",
                    },
                ]
            }
        ]
    }
}

# d. boards(ids: with items_page → items with column_values and group
ITEMS_RESPONSE = {
    "data": {
        "boards": [
            {
                "items_page": {
                    "cursor": None,
                    "items": [
                        {
                            "id": "10001",
                            "name": "Fix login page crash",
                            "group": {"id": "sprint_5", "title": "Sprint 5"},
                            "column_values": [
                                {
                                    "id": "status",
                                    "text": "Working on it",
                                    "type": "status",
                                    "value": '{"index":1,"label":"Working on it"}',
                                },
                                {
                                    "id": "priority",
                                    "text": "High",
                                    "type": "status",
                                    "value": '{"index":2,"label":"High"}',
                                },
                                {
                                    "id": "date0",
                                    "text": "2026-04-15",
                                    "type": "date",
                                    "value": '{"date":"2026-04-15"}',
                                },
                                {
                                    "id": "person",
                                    "text": "Test User",
                                    "type": "people",
                                    "value": '{"personsAndTeams":[{"id":12345,"kind":"person"}]}',
                                },
                                {
                                    "id": "tags0",
                                    "text": "",
                                    "type": "tag",
                                    "value": '{"tag_ids":[101]}',
                                },
                                {
                                    "id": "dependency0",
                                    "text": "",
                                    "type": "dependency",
                                    "value": '{"linkedPulseIds":[{"linkedPulseId":10003}]}',
                                },
                                {
                                    "id": "numbers0",
                                    "text": "5",
                                    "type": "numbers",
                                    "value": '"5"',
                                },
                            ],
                        },
                        {
                            "id": "10002",
                            "name": "Add dark mode support",
                            "group": {"id": "sprint_5", "title": "Sprint 5"},
                            "column_values": [
                                {
                                    "id": "status",
                                    "text": "Done",
                                    "type": "status",
                                    "value": '{"index":2,"label":"Done"}',
                                },
                                {
                                    "id": "priority",
                                    "text": "Medium",
                                    "type": "status",
                                    "value": '{"index":3,"label":"Medium"}',
                                },
                            ],
                        },
                        {
                            "id": "10003",
                            "name": "Platform migration",
                            "group": {"id": "backlog", "title": "Backlog"},
                            "column_values": [
                                {
                                    "id": "status",
                                    "text": "Stuck",
                                    "type": "status",
                                    "value": '{"index":3,"label":"Stuck"}',
                                },
                                {
                                    "id": "priority",
                                    "text": "Critical",
                                    "type": "status",
                                    "value": '{"index":1,"label":"Critical"}',
                                },
                                {
                                    "id": "person",
                                    "text": "Test User",
                                    "type": "people",
                                    "value": '{"personsAndTeams":[{"id":12345,"kind":"person"}]}',
                                },
                            ],
                        },
                    ],
                }
            }
        ]
    }
}

# e. items(ids: with subitems → subitems with parent augmentation
SUBITEMS_RESPONSE = {
    "data": {
        "items": [
            {
                "id": "10001",
                "subitems": [
                    {
                        "id": "20001",
                        "name": "Subtask: research login libs",
                        "group": {"id": "subitems_group", "title": "Subitems"},
                        "column_values": [
                            {
                                "id": "status",
                                "text": "Working on it",
                                "type": "status",
                                "value": '{"index":1,"label":"Working on it"}',
                            },
                        ],
                    },
                ],
            },
        ]
    }
}

# f. users(ids: → user details
USERS_RESPONSE = {
    "data": {
        "users": [
            {
                "id": "12345",
                "name": "Test User",
                "email": "test@example.com",
            }
        ]
    }
}

# g. tags(ids: → tag names
TAGS_RESPONSE = {
    "data": {
        "tags": [
            {"id": "101", "name": "frontend"},
        ]
    }
}

# h. change_multiple_column_values mutation → success
MUTATION_RESPONSE = {
    "data": {
        "change_multiple_column_values": {
            "id": "10001",
            "name": "Fix login page crash",
        }
    }
}

# i. create_item mutation → success
CREATE_ITEM_RESPONSE = {
    "data": {
        "create_item": {
            "id": "10099",
            "name": "New item",
        }
    }
}

# j. groups query → board groups
GROUPS_RESPONSE = {
    "data": {
        "boards": [
            {
                "groups": [
                    {"id": "sprint_5", "title": "Sprint 5"},
                    {"id": "backlog", "title": "Backlog"},
                ]
            }
        ]
    }
}


# ---------------------------------------------------------------------------
# Query dispatch — order matters, more specific substrings first
# ---------------------------------------------------------------------------

QUERY_MATCHERS: list[tuple[str, str, dict]] = [
    ("change_multiple_column_values", "mutation: change_column_values", MUTATION_RESPONSE),
    ("create_item",                   "mutation: create_item",          CREATE_ITEM_RESPONSE),
    ("subitems",                      "subitems",                       SUBITEMS_RESPONSE),
    ("items_page",                    "items_page",                     ITEMS_RESPONSE),
    ("columns",                       "columns",                        BOARD_COLUMNS_RESPONSE),
    ("groups",                        "groups",                         GROUPS_RESPONSE),
    ("users",                         "users",                          USERS_RESPONSE),
    ("tags",                          "tags",                           TAGS_RESPONSE),
    ("boards(limit",                  "boards (list)",                  BOARDS_RESPONSE),
    ("boards(ids",                    "boards (by id)",                 BOARD_COLUMNS_RESPONSE),
    ("{ me ",                         "me",                             ME_RESPONSE),
]

# Fallback for unrecognised queries
FALLBACK_RESPONSE: dict = {"data": {}}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockMondayHandler(BaseHTTPRequestHandler):
    """Handles POST / (GraphQL) and GET /health."""

    def do_GET(self) -> None:  # noqa: N802
        """Health-check endpoint for Docker healthcheck."""
        if self.path in ("/health", "/health/"):
            self._json_response(200, {"status": "ok"})
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        """GraphQL endpoint — Monday.com uses POST / (root path)."""
        if self.path not in ("/", ""):
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
                print(f"[mock-monday] Matched query type: {label}", file=sys.stderr, flush=True)
                self._json_response(200, response)
                return

        print(f"[mock-monday] Unmatched query (fallback): {query[:120]}", file=sys.stderr, flush=True)
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
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-monday] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test infrastructure (cloned from mock-jira-api)
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


def _make_fake_handler(method: str, path: str, body: bytes | None = None):
    """Construct a MockMondayHandler for selftest without a real socket."""
    import email

    class SilentHandler(MockMondayHandler):
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

        def log_message(self, fmt, *args):
            pass

    handler = SilentHandler()

    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()

    return handler


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Simulate requests against all endpoints, verify responses, exit."""
    print("[selftest] Starting mock Monday.com API self-test...")

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
            print(f"  \u2717 {name}: expected {expect_status}, got {actual_status}")
            failed += 1
            return

        if expect_check and not expect_check(handler._test_body):
            print(f"  \u2717 {name}: response body check failed")
            print(f"    body: {json.dumps(handler._test_body, indent=2)[:200]}")
            failed += 1
            return

        print(f"  \u2713 {name}")
        passed += 1

    def _gql_body(query: str) -> bytes:
        return json.dumps({"query": query}).encode()

    # 1. Health check
    check(
        "GET /health",
        "GET",
        "/health",
        expect_check=lambda b: b.get("status") == "ok",
    )

    # 2. me query
    check(
        "POST / (me query)",
        "POST",
        "/",
        body=_gql_body("{ me { id name email } }"),
        expect_check=lambda b: (
            b.get("data", {}).get("me", {}).get("id") == "12345"
            and b["data"]["me"].get("name") == "Test User"
            and b["data"]["me"].get("email") == "test@example.com"
        ),
    )

    # 3. boards list
    check(
        "POST / (boards list)",
        "POST",
        "/",
        body=_gql_body("{ boards(limit: 100, state: active) { id name state } }"),
        expect_check=lambda b: (
            isinstance(b.get("data", {}).get("boards"), list)
            and len(b["data"]["boards"]) == 2
        ),
    )

    # 4. columns query
    check(
        "POST / (columns query)",
        "POST",
        "/",
        body=_gql_body("{ boards(ids: [1001]) { columns { id title type settings_str } } }"),
        expect_check=lambda b: (
            len(b.get("data", {}).get("boards", [{}])[0].get("columns", [])) == 10
            and isinstance(
                b["data"]["boards"][0]["columns"][0].get("settings_str"), str
            )
            and "labels" in json.loads(
                b["data"]["boards"][0]["columns"][0]["settings_str"]
            )
        ),
    )

    # 5. items_page query
    check(
        "POST / (items_page query)",
        "POST",
        "/",
        body=_gql_body(
            "{ boards(ids: [1001]) { items_page(limit: 100) "
            "{ cursor items { id name group { id title } column_values { id text type value } } } } }"
        ),
        expect_check=lambda b: (
            len(
                b.get("data", {})
                .get("boards", [{}])[0]
                .get("items_page", {})
                .get("items", [])
            )
            == 3
            and b["data"]["boards"][0]["items_page"]["items"][0].get("group", {}).get("id") == "sprint_5"
            and len(b["data"]["boards"][0]["items_page"]["items"][0].get("column_values", [])) >= 5
        ),
    )

    # 6. subitems query
    check(
        "POST / (subitems query)",
        "POST",
        "/",
        body=_gql_body(
            "{ items(ids: [10001]) { id subitems { id name "
            "group { id title } column_values { id text type value } } } }"
        ),
        expect_check=lambda b: (
            len(b.get("data", {}).get("items", [])) == 1
            and len(b["data"]["items"][0].get("subitems", [])) >= 1
            and b["data"]["items"][0]["subitems"][0].get("id") == "20001"
        ),
    )

    # 7. users query
    check(
        "POST / (users query)",
        "POST",
        "/",
        body=_gql_body("{ users(ids: [12345]) { id name email } }"),
        expect_check=lambda b: (
            isinstance(b.get("data", {}).get("users"), list)
            and len(b["data"]["users"]) == 1
            and b["data"]["users"][0].get("id") == "12345"
        ),
    )

    # 8. tags query
    check(
        "POST / (tags query)",
        "POST",
        "/",
        body=_gql_body("{ tags(ids: [101]) { id name } }"),
        expect_check=lambda b: (
            isinstance(b.get("data", {}).get("tags"), list)
            and len(b["data"]["tags"]) == 1
            and b["data"]["tags"][0].get("name") == "frontend"
        ),
    )

    # 9. groups query
    check(
        "POST / (groups query)",
        "POST",
        "/",
        body=_gql_body("{ boards(ids: [1001]) { groups { id title } } }"),
        expect_check=lambda b: (
            len(b.get("data", {}).get("boards", [{}])[0].get("groups", [])) == 2
        ),
    )

    # 10. change_multiple_column_values mutation
    check(
        "POST / (change_multiple_column_values mutation)",
        "POST",
        "/",
        body=_gql_body(
            'mutation { change_multiple_column_values('
            'board_id: 1001, item_id: 10001, column_values: "{}") { id name } }'
        ),
        expect_check=lambda b: (
            b.get("data", {}).get("change_multiple_column_values", {}).get("id") == "10001"
        ),
    )

    # 11. create_item mutation
    check(
        "POST / (create_item mutation)",
        "POST",
        "/",
        body=_gql_body(
            'mutation { create_item('
            'board_id: 1001, group_id: "sprint_5", item_name: "New item") { id name } }'
        ),
        expect_check=lambda b: (
            b.get("data", {}).get("create_item", {}).get("id") == "10099"
        ),
    )

    # 12. Unknown query → fallback
    check(
        "POST / (unknown query → fallback)",
        "POST",
        "/",
        body=_gql_body("{ somethingUnknown { id } }"),
        expect_check=lambda b: b == {"data": {}},
    )

    # -- Summary --
    print(f"\n[selftest] {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-monday] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockMondayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-monday] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()

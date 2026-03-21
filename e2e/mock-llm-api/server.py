"""Mock OpenAI-compatible LLM API server for E2E testing.

A lightweight HTTP server returning canned responses for the OpenAI
chat completions API.  Designed to run inside Docker alongside the
SemPKM test stack so the AI endpoints can be pointed here via the
Settings API (``PUT /browser/settings/llm/config``).

Endpoints served:
    GET  /health              → liveness check (Docker healthcheck)
    GET  /v1/models           → model list (LLM connection test in Settings)
    POST /v1/chat/completions → chat completion with canned claim JSON

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
# Canned response data
# ---------------------------------------------------------------------------

MODELS_RESPONSE = {
    "object": "list",
    "data": [
        {
            "id": "test-model",
            "object": "model",
            "created": 1700000000,
            "owned_by": "test",
        }
    ],
}

# The claim JSON the mock LLM "generates" — matches _parse_claims_response()
# expectations: {"claims": [{text, confidence, type}, ...]}
CLAIMS_RESPONSE = {
    "claims": [
        {
            "text": "Climate change is accelerating global ice loss",
            "confidence": "likely",
            "type": "factual",
        },
        {
            "text": "Arctic sea ice extent reached a record low in 2023",
            "confidence": "established",
            "type": "statistical",
        },
        {
            "text": "Current models underestimate permafrost thaw rates",
            "confidence": "speculative",
            "type": "analytical",
        },
    ]
}

# Full OpenAI chat completion envelope — content is the JSON-serialized claims
CHAT_COMPLETION_RESPONSE = {
    "id": "chatcmpl-mock-001",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "test-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(CLAIMS_RESPONSE),
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    },
}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockLLMHandler(BaseHTTPRequestHandler):
    """Handles GET and POST requests mimicking the OpenAI API."""

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        if path == "/health":
            self._json_response(200, {"status": "ok"})
        elif path == "/v1/models":
            self._json_response(200, MODELS_RESPONSE)
        else:
            self._json_response(404, {"message": "Not Found"})

        self._log_request("GET", self.path)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        if path == "/v1/chat/completions":
            # Read the request body (ignored — always return canned response)
            content_length = int(self.headers.get("Content-Length", 0))
            _body = self.rfile.read(content_length)
            self._json_response(200, CHAT_COMPLETION_RESPONSE)
        else:
            self._json_response(404, {"message": "Not Found"})

        self._log_request("POST", self.path)

    # -- helpers --

    def _json_response(self, status: int, body: dict | list) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _log_request(self, method: str, path: str) -> None:
        print(f"[mock-llm] {method} {path}", file=sys.stderr, flush=True)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-llm] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Simulate requests against all endpoints, verify responses, exit."""
    print("[mock-llm] selftest: starting...")

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
        "GET /health → 200",
        "GET",
        "/health",
        expect_check=lambda b: b.get("status") == "ok",
    )

    check(
        "GET /v1/models → 200 with test-model",
        "GET",
        "/v1/models",
        expect_check=lambda b: (
            b.get("object") == "list"
            and len(b.get("data", [])) == 1
            and b["data"][0]["id"] == "test-model"
        ),
    )

    # -- POST endpoint --

    chat_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "Extract claims from this text."}],
        "stream": False,
    }).encode()

    def _check_chat_response(b):
        """Verify the chat completion response has valid claim JSON in content."""
        if b.get("id") != "chatcmpl-mock-001":
            return False
        choices = b.get("choices", [])
        if len(choices) != 1:
            return False
        content_str = choices[0].get("message", {}).get("content", "")
        try:
            content = json.loads(content_str)
        except (json.JSONDecodeError, TypeError):
            return False
        claims = content.get("claims", [])
        if len(claims) != 3:
            return False
        # Verify claim structure
        for claim in claims:
            if not all(k in claim for k in ("text", "confidence", "type")):
                return False
        return True

    check(
        "POST /v1/chat/completions → 200 with claims",
        "POST",
        "/v1/chat/completions",
        body=chat_body,
        expect_check=_check_chat_response,
    )

    # -- 404 for unknown paths --

    check(
        "GET /unknown → 404",
        "GET",
        "/unknown/path",
        expect_status=404,
    )

    check(
        "POST /unknown → 404",
        "POST",
        "/unknown/path",
        expect_status=404,
    )

    # -- Summary --
    total = passed + failed
    print(f"\n[mock-llm] selftest: {passed}/{total} checks passed")
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
    """Construct a MockLLMHandler for selftest without a real socket."""
    import email

    class SilentHandler(MockLLMHandler):
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

    return handler


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-llm] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockLLMHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-llm] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()

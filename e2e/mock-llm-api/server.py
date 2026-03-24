"""Mock OpenAI-compatible LLM API server for E2E testing.

A lightweight HTTP server returning canned responses for the OpenAI
chat completions API.  Designed to run inside Docker alongside the
SemPKM test stack so the AI endpoints can be pointed here via the
Settings API (``PUT /browser/settings/llm/config``).

Endpoints served:
    GET  /health              → liveness check (Docker healthcheck)
    GET  /v1/models           → model list (LLM connection test in Settings)
    POST /v1/chat/completions → chat completion with canned responses
                                (streaming SSE or single JSON, pattern-matched)

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
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


# ---------------------------------------------------------------------------
# Copilot canned response content (pattern-matched on user message)
# ---------------------------------------------------------------------------

SPARQL_RESPONSE = (
    "I'll query your knowledge graph to find that information.\n\n"
    "```sparql\n"
    "SELECT (COUNT(?s) AS ?count) WHERE { ?s a <http://example.org/bpkm#Project> }\n"
    "```\n\n"
    "This query counts all Project instances in your graph."
)

CREATE_OBJECT_RESPONSE = (
    "I'll create that task for you.\n\n"
    '```json\n'
    '{"action": "create_object", "type": "http://example.org/bpkm#Task", '
    '"label": "Review Q1 goals", "properties": '
    '{"http://purl.org/dc/terms/title": "Review Q1 goals"}}\n'
    '```\n\n'
    "Once you approve, the task will be added to your knowledge graph."
)

SUMMARIZE_RESPONSE = (
    "Based on the linked Project and its 3 associated Tasks, here's a summary:\n\n"
    "The project has active tasks covering planning, execution, and review phases. "
    "Two tasks are marked as in-progress, and one is completed. The overall "
    "progress indicates the project is approximately 33% complete."
)

GENERIC_RESPONSE = (
    "I can help you explore your knowledge graph. You can ask me to:\n\n"
    "- **Query data**: Ask questions like 'how many projects do I have?'\n"
    "- **Create objects**: Say 'create a new task called ...'\n"
    "- **Summarize**: Ask for a summary of any object's context\n\n"
    "What would you like to do?"
)


def _select_response(user_message: str) -> str:
    """Select a canned response based on the user message content.

    Pattern matching priority (first match wins):
    1. "claim" or "extract" → claims JSON (backward compat with M028)
    2. "how many" or "project" → SPARQL query block
    3. "create" AND "task" → object creation JSON block
    4. "summarize" or "context" → prose summary
    5. default → generic helpful response
    """
    msg = user_message.lower()

    if "claim" in msg or "extract" in msg:
        return json.dumps(CLAIMS_RESPONSE)
    if "how many" in msg or "project" in msg:
        return SPARQL_RESPONSE
    if "create" in msg and "task" in msg:
        return CREATE_OBJECT_RESPONSE
    if "summarize" in msg or "context" in msg:
        return SUMMARIZE_RESPONSE
    return GENERIC_RESPONSE


def _extract_last_user_message(body: dict) -> str:
    """Extract the content of the last user message from the request body."""
    messages = body.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _build_completion_response(content: str) -> dict:
    """Build a non-streaming OpenAI chat completion response envelope."""
    return {
        "id": f"chatcmpl-mock-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": max(1, len(content.split())),
            "total_tokens": 100 + max(1, len(content.split())),
        },
    }


def _build_sse_chunks(content: str) -> list[bytes]:
    """Build SSE-formatted streaming chunks for a response.

    Splits content into words and emits one chunk per word in OpenAI
    streaming format.  Returns a list of encoded SSE lines including
    the final ``data: [DONE]`` sentinel.
    """
    chunks: list[bytes] = []
    words = content.split(" ")

    for i, word in enumerate(words):
        # Add trailing space to all words except the last
        token = word + " " if i < len(words) - 1 else word
        chunk_data = {
            "id": "chatcmpl-mock-stream",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": token},
                    "finish_reason": None,
                }
            ],
        }
        chunks.append(f"data: {json.dumps(chunk_data)}\n\n".encode())

    # Final chunk with finish_reason and [DONE] sentinel
    final_chunk = {
        "id": "chatcmpl-mock-stream",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    chunks.append(f"data: {json.dumps(final_chunk)}\n\n".encode())
    chunks.append(b"data: [DONE]\n\n")
    return chunks


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
            # Parse request body
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)

            try:
                body = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                body = {}

            is_stream = body.get("stream", False)
            user_message = _extract_last_user_message(body)
            response_content = _select_response(user_message)

            self._log_request(
                "POST",
                f"{self.path} stream={str(is_stream).lower()} "
                f"route={'claims' if 'claim' in user_message.lower() or 'extract' in user_message.lower() else 'copilot'}",
            )

            if is_stream:
                self._stream_response(response_content)
            else:
                self._json_response(200, _build_completion_response(response_content))
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

    def _stream_response(self, content: str) -> None:
        """Send an SSE streaming response in OpenAI chunk format."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        for chunk in _build_sse_chunks(content):
            self.wfile.write(chunk)
            self.wfile.flush()

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
        expect_stream: bool = False,
    ):
        nonlocal passed, failed

        handler = _make_fake_handler(method, path, body)
        actual_status = handler._test_status

        if actual_status != expect_status:
            print(f"  ✗ {name}: expected status {expect_status}, got {actual_status}")
            failed += 1
            return

        if expect_stream:
            # Check the raw SSE output
            raw = handler._test_raw_output
            if expect_check and not expect_check(raw):
                print(f"  ✗ {name}: SSE stream check failed")
                print(f"    raw (first 300 chars): {raw[:300]}")
                failed += 1
                return
        else:
            if expect_check and not expect_check(handler._test_body):
                print(f"  ✗ {name}: response body check failed")
                if handler._test_body is not None:
                    print(f"    body: {json.dumps(handler._test_body, indent=2)[:300]}")
                else:
                    print(f"    raw: {handler._test_raw_output[:300]}")
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

    # -- POST /v1/chat/completions: non-streaming claims (backward compat) --

    claims_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "Extract claims from this text."}],
        "stream": False,
    }).encode()

    def _check_claims_response(b):
        """Verify backward-compatible claims response."""
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
        for claim in claims:
            if not all(k in claim for k in ("text", "confidence", "type")):
                return False
        return True

    check(
        "POST claims (non-streaming) → 200 with claims JSON",
        "POST",
        "/v1/chat/completions",
        body=claims_body,
        expect_check=_check_claims_response,
    )

    # -- POST: SPARQL-triggering message (non-streaming) --

    sparql_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "How many projects do I have?"}],
        "stream": False,
    }).encode()

    check(
        "POST SPARQL route (non-streaming) → content contains SELECT",
        "POST",
        "/v1/chat/completions",
        body=sparql_body,
        expect_check=lambda b: "SELECT" in b.get("choices", [{}])[0].get("message", {}).get("content", ""),
    )

    # -- POST: create-task message (non-streaming) --

    create_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "Please create a new task for Q1 review"}],
        "stream": False,
    }).encode()

    check(
        "POST create-task route (non-streaming) → content contains create_object",
        "POST",
        "/v1/chat/completions",
        body=create_body,
        expect_check=lambda b: "create_object" in b.get("choices", [{}])[0].get("message", {}).get("content", ""),
    )

    # -- POST: summarize message (non-streaming) --

    summarize_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "Can you summarize this for me?"}],
        "stream": False,
    }).encode()

    check(
        "POST summarize route (non-streaming) → content contains summary text",
        "POST",
        "/v1/chat/completions",
        body=summarize_body,
        expect_check=lambda b: "Project" in b.get("choices", [{}])[0].get("message", {}).get("content", ""),
    )

    # -- POST: default route (non-streaming) --

    default_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello there"}],
        "stream": False,
    }).encode()

    check(
        "POST default route (non-streaming) → generic helpful response",
        "POST",
        "/v1/chat/completions",
        body=default_body,
        expect_check=lambda b: "knowledge graph" in b.get("choices", [{}])[0].get("message", {}).get("content", ""),
    )

    # -- POST: SSE streaming with SPARQL content --

    stream_sparql_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "How many projects exist?"}],
        "stream": True,
    }).encode()

    def _check_sse_sparql(raw: str):
        """Verify SSE output has correct format and SPARQL content."""
        lines = [l for l in raw.split("\n") if l.startswith("data: ")]
        if len(lines) < 3:
            return False
        # Must end with [DONE]
        if not lines[-1].strip().endswith("[DONE]"):
            return False
        # Reconstruct streamed content
        content = ""
        for line in lines:
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                continue
            try:
                chunk = json.loads(data_str)
                delta_content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                content += delta_content
            except json.JSONDecodeError:
                continue
        return "SELECT" in content and "sparql" in content

    check(
        "POST streaming (SPARQL route) → valid SSE with SPARQL content",
        "POST",
        "/v1/chat/completions",
        body=stream_sparql_body,
        expect_stream=True,
        expect_check=_check_sse_sparql,
    )

    # -- POST: SSE streaming with create-task content --

    stream_create_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "create a task for planning"}],
        "stream": True,
    }).encode()

    def _check_sse_create(raw: str):
        """Verify SSE streaming returns create_object content."""
        lines = [l for l in raw.split("\n") if l.startswith("data: ")]
        if not lines[-1].strip().endswith("[DONE]"):
            return False
        content = ""
        for line in lines:
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                continue
            try:
                chunk = json.loads(data_str)
                delta_content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                content += delta_content
            except json.JSONDecodeError:
                continue
        return "create_object" in content

    check(
        "POST streaming (create-task route) → valid SSE with create_object",
        "POST",
        "/v1/chat/completions",
        body=stream_create_body,
        expect_stream=True,
        expect_check=_check_sse_create,
    )

    # -- POST: SSE streaming default --

    stream_default_body = json.dumps({
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }).encode()

    def _check_sse_default(raw: str):
        """Verify SSE streaming format: data lines + [DONE]."""
        lines = [l for l in raw.split("\n") if l.startswith("data: ")]
        if len(lines) < 2:
            return False
        if not lines[-1].strip().endswith("[DONE]"):
            return False
        # Verify each non-DONE line is valid JSON with expected structure
        for line in lines:
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                continue
            try:
                chunk = json.loads(data_str)
                if chunk.get("object") != "chat.completion.chunk":
                    return False
            except json.JSONDecodeError:
                return False
        return True

    check(
        "POST streaming (default route) → valid SSE chunk format",
        "POST",
        "/v1/chat/completions",
        body=stream_default_body,
        expect_stream=True,
        expect_check=_check_sse_default,
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
        if isinstance(data, str):
            data = data.encode()
        self.data += data

    def flush(self) -> None:
        pass  # no-op for testing


def _make_fake_handler(method: str, path: str, body: bytes | None = None):
    """Construct a MockLLMHandler for selftest without a real socket."""
    import email

    class SilentHandler(MockLLMHandler):
        """Subclass that captures responses instead of writing to a socket."""

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
            self._test_raw_output = ""
            self._test_is_stream = False

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
            if keyword.lower() == "content-type" and "event-stream" in value:
                self._test_is_stream = True

        def end_headers(self):
            pass

        def _json_response(self, status, body):
            self._test_status = status
            self._test_body = body

        def _stream_response(self, content):
            """Capture SSE output as raw text for selftest inspection."""
            self._test_status = 200
            self._test_is_stream = True
            chunks = _build_sse_chunks(content)
            raw = b"".join(chunks)
            self._test_raw_output = raw.decode("utf-8", errors="replace")

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

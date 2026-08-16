"""A local server for the generated page, so its edits have somewhere to go.

The page is a static file, and a static file cannot write to disk. Nothing in
the drawing needs a server — but the link editing does, because a correction
that only lives in one browser is worse than no correction at all.

So: serve `out_dir` over loopback, and accept one POST that merges the page's
edit journal into `overlay/links.yml`. Everything else is a plain file server.
Bound to 127.0.0.1 and refusing to write anywhere but that one file, because a
dev tool that opens a write endpoint on a shared interface is a bug.
"""

from __future__ import annotations

import json
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 4 * 1024 * 1024
ENDPOINT = "/_repolens/links"


def merge_edits(existing: dict, edits: dict) -> dict:
    """Fold a page's journal into the stored overrides.

    The journal is the whole of that browser's pending state, so an item it
    mentions is replaced outright rather than accumulated — otherwise undoing
    an edit in the page could never remove it from the file.
    """
    out = {k: dict(v) for k, v in (existing or {}).items()}
    for page_id, items in (edits or {}).items():
        if not isinstance(items, dict):
            continue
        slot = out.setdefault(page_id, {})
        for item_id, edit in items.items():
            add = [str(x) for x in (edit or {}).get("add", [])]
            remove = [str(x) for x in (edit or {}).get("remove", [])]
            if add or remove:
                slot[item_id] = {k: v for k, v in
                                 (("add", add), ("remove", remove)) if v}
            else:
                slot.pop(item_id, None)
        if not slot:
            out.pop(page_id, None)
    return out


def dump_yaml(data: dict) -> str:
    """Write the overrides without a yaml dependency at serve time."""
    lines = [
        "# repolens link overrides — written by the page, and safe to hand-edit.",
        "# Targets: part:ID, file:PATH, sym:PATH#NAME. A bare id means a part.",
    ]
    for page_id in sorted(data):
        lines.append(f"{page_id}:")
        for item_id in sorted(data[page_id]):
            edit = data[page_id][item_id]
            lines.append(f"  {json.dumps(item_id)}:")
            for field in ("add", "remove"):
                if edit.get(field):
                    inner = ", ".join(json.dumps(x) for x in edit[field])
                    lines.append(f"    {field}: [{inner}]")
    return "\n".join(lines) + "\n"


class Handler(SimpleHTTPRequestHandler):
    overlay_dir: Path = Path(".")

    def do_POST(self) -> None:                                  # noqa: N802
        if self.path.rstrip("/") != ENDPOINT:
            self.send_error(404, "no such endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                raise ValueError("bad content length")
            edits = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(edits, dict):
                raise ValueError("expected an object")
        except Exception as e:
            self.send_error(400, f"bad request: {e}")
            return

        target = self.overlay_dir / "links.yml"
        existing = _read_existing(target)
        merged = merge_edits(existing, edits)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_yaml(merged), encoding="utf-8")

        count = sum(len(v) for v in merged.values())
        print(f"  wrote {target} — {count} item(s) overridden")
        body = json.dumps({"ok": True, "items": count, "path": str(target)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):                          # quieter
        if self.command == "POST":
            super().log_message(fmt, *args)


def _read_existing(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:                                      # pragma: no cover
        print(f"  warning: {path} unreadable ({e}); starting fresh")
        return {}


def serve(out_dir: Path, overlay_dir: Path, port: int = 7171,
          open_browser: bool = True) -> int:
    if not (out_dir / "index.html").exists():
        raise SystemExit(f"no page at {out_dir / 'index.html'} — run `repolens build` first.")
    Handler.overlay_dir = overlay_dir
    handler = partial(Handler, directory=str(out_dir))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/index.html"
    print(f"repolens serve — {url}")
    print(f"  serving  {out_dir}")
    print(f"  writing  {overlay_dir / 'links.yml'} on save")
    print("  ctrl-c to stop")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0

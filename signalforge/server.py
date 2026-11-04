from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .evaluator import evaluate, summarize
from .models import Trace
from .regression import compare
from .store import TraceStore

WEB_ROOT = Path(__file__).parent / "web"


class SignalForgeHandler(BaseHTTPRequestHandler):
    store: TraceStore

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size > 1_000_000:
            raise ValueError("Request body exceeds 1MB limit")
        return json.loads(self.rfile.read(size))

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/summary":
            results = self.store.list()
            self._send_json({"summary": summarize(results), "results": [r.to_dict() for r in results]})
            return
        if route == "/api/traces":
            self._send_json({"traces": [r.to_dict() for r in self.store.list()]})
            return
        if route == "/health":
            self._send_json({"status": "ok"})
            return
        if route in ("/", "/index.html"):
            body = (WEB_ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/compare":
            try:
                payload = self._read_json()
                baseline = [Trace.from_dict(item) for item in payload.get("baseline", [])]
                candidate = [Trace.from_dict(item) for item in payload.get("candidate", [])]
                self._send_json(compare(baseline, candidate, float(payload.get("threshold", 0.1))))
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._send_json({"error": str(error)}, 400)
            return
        if route != "/api/evaluate":
            self._send_json({"error": "Not found"}, 404)
            return
        try:
            payload = self._read_json()
            items = payload if isinstance(payload, list) else payload.get("traces", [payload])
            results = []
            for item in items:
                result = evaluate(Trace.from_dict(item))
                self.store.save(result)
                results.append(result.to_dict())
            self._send_json({"results": results, "summary": summarize([self.store._decode(json.dumps(r)) for r in results])})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, 400)

    def log_message(self, format: str, *args) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000, database: str = "signalforge.db") -> None:
    SignalForgeHandler.store = TraceStore(database)
    server = ThreadingHTTPServer((host, port), SignalForgeHandler)
    print(f"SignalForge listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        SignalForgeHandler.store.close()
        server.server_close()

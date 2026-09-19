"""Dependency-free HTTP service for the Astra-1 research runtime."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .runtime import PersistentRuntime


class AstraRequestHandler(BaseHTTPRequestHandler):
    runtime: PersistentRuntime | None = None

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send(200, {"status": "ok", "service": "astra-1"})
            return

        prefix = "/trace/"
        if parsed.path.startswith(prefix):
            try:
                execution_id = int(parsed.path[len(prefix):])
            except ValueError:
                self._send(400, {"error": "execution id must be an integer"})
                return
            result = self.runtime.store.get_execution(execution_id)
            if result is None:
                self._send(404, {"error": "execution not found"})
            else:
                self._send(200, result)
            return

        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            result = self.runtime.run(body.get("goal", ""))
            self._send(200, result)
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": type(exc).__name__, "message": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8765, database: str = "data/astra.db") -> None:
    AstraRequestHandler.runtime = PersistentRuntime()
    AstraRequestHandler.runtime.store.close()
    AstraRequestHandler.runtime = PersistentRuntime()
    server = ThreadingHTTPServer((host, port), AstraRequestHandler)
    print(f"Astra-1 service listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()

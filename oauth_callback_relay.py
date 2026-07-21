#!/usr/bin/env python3
"""Relay a public OAuth callback to Codex's loopback-only callback server."""

from __future__ import annotations

import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


def build_handler(target_host: str, target_port: int):
    class OAuthCallbackRelay(BaseHTTPRequestHandler):
        server_version = "OAuthCallbackRelay/1.0"

        def do_GET(self) -> None:  # noqa: N802
            query = parse_qs(urlsplit(self.path).query)
            if "code" not in query or "state" not in query:
                self.send_error(404)
                return

            connection = http.client.HTTPConnection(
                target_host,
                target_port,
                timeout=30,
            )
            try:
                connection.request("GET", self.path)
                response = connection.getresponse()
                body = response.read()
            except OSError:
                self.send_error(503, "Codex OAuth callback listener is not ready")
                return
            finally:
                connection.close()

            self.send_response(response.status)
            for header in ("Content-Type", "Location"):
                value = response.getheader(header)
                if value:
                    self.send_header(header, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: object) -> None:
            # OAuth codes live in the query string, so never print request URLs.
            return

    return OAuthCallbackRelay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-port", type=int, default=1455)
    parser.add_argument("--target-port", type=int, default=1456)
    args = parser.parse_args()

    handler = build_handler("127.0.0.1", args.target_port)
    server = ThreadingHTTPServer(("0.0.0.0", args.listen_port), handler)
    print(
        f"OAuth callback relay listening on 0.0.0.0:{args.listen_port} "
        f"and forwarding to 127.0.0.1:{args.target_port}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()

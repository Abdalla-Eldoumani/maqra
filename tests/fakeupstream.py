"""A tiny stand-in for everyayah.com used by the tests.

Serves a directory tree with listing pages in the same HTML shape as the real
CDN (data-order byte counts, <time datetime>), supports Range requests, and can
be told to fail the first N requests for a path so retry and resume paths run.
"""

from __future__ import annotations

import html
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict
from urllib.parse import unquote


def listing_html(dirpath: Path, url_path: str) -> bytes:
    rows = []
    for p in sorted(dirpath.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
        name = html.escape(p.name)
        if p.is_dir():
            rows.append(
                f'<tr class="file"><td></td><td><a href="{url_path}{name}/"><span class="name">{name}</span></a></td>'
                f'<td data-order="-1">\u2014</td><td class="hideable"><time datetime="2023-01-19T22:29:48">Thu Jan 19 22:29:48 2023</time></td><td class="hideable"></td></tr>'
            )
        else:
            size = p.stat().st_size
            rows.append(
                f'<tr class="file"><td></td><td><a href="{url_path}{name}"><span class="name">{name}</span></a></td>'
                f'<td data-order="{size}">{size} bytes</td><td class="hideable"><time datetime="2023-01-17T23:45:33">Tue Jan 17 23:45:33 2023</time></td><td class="hideable"></td></tr>'
            )
    body = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body><h1>x</h1>"
        "<table aria-describedby=\"summary\"><thead><tr><th></th><th>Name</th><th>Size</th><th class=\"hideable\">Modified</th><th class=\"hideable\"></th></tr></thead><tbody>"
        "<tr class=\"clickable\"><td></td><td><a href=\"..\"><span class=\"goup\">..</span></a></td><td>\u2014</td><td class=\"hideable\">\u2014</td><td class=\"hideable\"></td></tr>"
        + "".join(rows) + "</tbody></table></body></html>"
    )
    return body.encode("utf-8")


class FakeUpstream:
    def __init__(self, docroot: Path):
        self.docroot = docroot
        self.fail_first: Dict[str, int] = {}  # url path -> remaining failures
        self.requests: list = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def _serve(self, send_body: bool) -> None:
                path = unquote(self.path.split("?", 1)[0])
                server.requests.append((self.command, path))
                if server.fail_first.get(path, 0) > 0:
                    server.fail_first[path] -= 1
                    self.send_response(503)
                    self.end_headers()
                    return
                fs = docroot / path.lstrip("/")
                if fs.is_dir():
                    body = listing_html(fs, path if path.endswith("/") else path + "/")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    if send_body:
                        self.wfile.write(body)
                    return
                if not fs.is_file():
                    self.send_response(404)
                    self.end_headers()
                    return
                size = fs.stat().st_size
                start = 0
                rng = self.headers.get("Range")
                if rng and rng.startswith("bytes="):
                    start = int(rng[6:].split("-")[0])
                    if start >= size:
                        self.send_response(416)
                        self.end_headers()
                        return
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{size - 1}/{size}")
                else:
                    self.send_response(200)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(size - start))
                self.end_headers()
                if send_body:
                    with open(fs, "rb") as fh:
                        fh.seek(start)
                        self.wfile.write(fh.read())

            def do_GET(self):
                self._serve(True)

            def do_HEAD(self):
                self._serve(False)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> str:
        self.thread.start()
        host, port = self.httpd.server_address
        return f"http://{host}:{port}/"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

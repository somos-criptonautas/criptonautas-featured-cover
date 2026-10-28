"""HTTP service for the internal Docker network. n8n calls it; it is never published to the internet.

POST /cover   Authorization: Bearer <COVER_TOKEN>
              JSON {"category", "title", "format": "png" | "webp", "style": "article" | "community"}
              -> the image, with Content-Disposition cover.<format>
GET  /health  -> 200 ok

The illustration is accepted only by cover.py on the command line: the server never decodes images from outside.
"""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cover import InvalidCoverInput, render_cover

MAX_BODY_BYTES = 4096  # only two short strings travel
MIN_TOKEN_LENGTH = 32


class Handler(BaseHTTPRequestHandler):
    timeout = 10  # a slow client cannot hold a thread forever
    token = b""   # set at startup; empty rejects every request

    def send(self, code, body, content_type="text/plain; charset=utf-8", file_name=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        if file_name:  # Ghost rejects files without an extension; n8n takes the name from this header
            self.send_header("Content-Disposition", f'attachment; filename="{file_name}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.send(200, b"ok")
        self.send(404, b"not found")

    def do_POST(self):
        if self.path != "/cover":
            return self.send(404, b"not found")
        if not self.token or not hmac.compare_digest(self.headers.get("Authorization", "").encode(), b"Bearer " + self.token):
            return self.send(401, b"wrong token")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.send(400, b"missing Content-Length")
        if not 0 < length <= MAX_BODY_BYTES:
            return self.send(413, b"body is empty or over 4 KB")
        try:
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise InvalidCoverInput("expected a JSON object")
            if "image" in request:
                raise InvalidCoverInput("the illustration is accepted only on the command line")
            image_format = request.get("format", "png")
            image = render_cover(str(request.get("category", "")), str(request.get("title", "")), None, image_format,
                                 str(request.get("style", "article")))
        except ValueError as error:  # covers InvalidCoverInput, bad JSON and bad UTF-8
            return self.send(422, str(error).encode())
        self.send(200, image, f"image/{image_format}", f"cover.{image_format}")

    def log_message(self, format, *args):  # keep titles and client addresses out of the logs
        pass


if __name__ == "__main__":
    Handler.token = os.environ.get("COVER_TOKEN", "").encode()
    if len(Handler.token) < MIN_TOKEN_LENGTH:
        sys.exit(f"cover: set COVER_TOKEN to {MIN_TOKEN_LENGTH} or more characters")
    print("cover service listening on :8000", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

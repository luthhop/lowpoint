import json
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, ".")

from lowpoint.tick import TICK_SECRET_HEADER, handle_tick


class handler(BaseHTTPRequestHandler):
    def _respond(self):
        result = handle_tick(self.command, self.headers.get(TICK_SECRET_HEADER))
        status = result.pop("statusCode", 500)
        body = json.dumps(result if status == 200 else {}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _respond

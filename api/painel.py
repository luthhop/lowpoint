import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, ".")

from lowpoint.painel import handle_painel


class handler(BaseHTTPRequestHandler):
    def _respond(self):
        status, headers, body = handle_painel(self.command, self.path)
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _respond

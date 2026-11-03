import json
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, ".")

from lowpoint.telegram.webhook import handle_update


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
        result = handle_update(body, secret)

        status = result.pop("statusCode", 200)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

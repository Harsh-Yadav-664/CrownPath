"""data/demo_target.py -- intentionally weak web app for the live-capture demo
(BUILD_SPEC.md §9 P2, issue #24 / E2). Stdlib only, written fresh for CrownPath.

Rule 6: this is OUR OWN app, and it serves on loopback only -- `serve()` refuses to
bind any non-loopback address. It exists so data/capture_findings.py has something
real to probe. Weaknesses are deliberate:

    /search?q=     reflects q unescaped             -> reflected XSS
    /go?next=      redirects to any URL             -> open redirect
    /.git/HEAD     serves repository metadata       -> source/info exposure
    /item?id=      toy store; a quote leaks a fake SQL error string -> SQL injection
                   (no database is involved; the "store" is a dict)
    /              plain index
"""
import ipaddress
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ITEMS = {"1": "keyboard", "2": "monitor", "3": "mouse"}


def is_loopback_host(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep test/CLI output quiet
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}

        if url.path == "/":
            self._send(200, "<h1>lab shop</h1>")
        elif url.path == "/search":
            # DELIBERATE: q is reflected without HTML escaping.
            self._send(200, f"<p>results for {q.get('q', '')}</p>")
        elif url.path == "/go":
            # DELIBERATE: any destination is accepted.
            self._send(302, "", headers={"Location": q.get("next", "/")})
        elif url.path == "/.git/HEAD":
            self._send(200, "ref: refs/heads/main\n", ctype="text/plain")
        elif url.path == "/item":
            item_id = q.get("id", "")
            if "'" in item_id:
                self._send(500, f"SQL syntax error near '{item_id}' at line 1", ctype="text/plain")
            elif item_id in ITEMS:
                self._send(200, f"<p>{ITEMS[item_id]}</p>")
            else:
                self._send(404, "not found", ctype="text/plain")
        else:
            self._send(404, "not found", ctype="text/plain")


def serve(host="127.0.0.1", port=0):
    """Start the target on a background thread; returns (server, base_url).
    Refuses any non-loopback host."""
    if not is_loopback_host(host):
        raise ValueError(f"demo_target refuses non-loopback host {host!r} (Rule 6)")
    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{host}:{server.server_address[1]}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    srv, base = serve(args.host, args.port)
    print(f"demo target on {base} (Ctrl+C to stop)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()

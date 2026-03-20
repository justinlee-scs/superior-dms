from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--port", type=int, default=8089)
    args = parser.parse_args()

    base = Path(args.dir).resolve()
    if not base.exists():
        raise SystemExit(f"Directory not found: {base}")

    handler = lambda *a, **kw: CORSRequestHandler(*a, directory=str(base), **kw)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(f"Serving {base} on http://localhost:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
import webbrowser


HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)

    url = f"http://{HOST}:{PORT}/index.html"
    server = ThreadingHTTPServer((HOST, PORT), SimpleHTTPRequestHandler)

    print(f"Serving Homework HQ at {url}")
    print("Press Ctrl+C to stop the server.")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

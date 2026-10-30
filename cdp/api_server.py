
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


CDP_DIR = Path(__file__).resolve().parent
CDP_DB = CDP_DIR / "database" / "cdp.db"

HOST = "127.0.0.1"
PORT = 8000


class CustomerSummaryHandler(BaseHTTPRequestHandler):

    def send_json(self, status_code, data):
        """Send a JSON response with the supplied HTTP status code."""
        body = json.dumps(data).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """Handle GET /customers/<customer_id>/summary."""
        path_parts = urlparse(self.path).path.strip("/").split("/")

        if (
            len(path_parts) != 3
            or path_parts[0] != "customers"
            or path_parts[2] != "summary"
        ):
            self.send_json(404, {"error": "Endpoint not found"})
            return

        customer_id = unquote(path_parts[1])

        try:
            with sqlite3.connect(
                f"file:{CDP_DB.as_posix()}?mode=ro",
                uri=True,
            ) as connection:
                connection.row_factory = sqlite3.Row

                row = connection.execute(
                    """
                    SELECT customer_id, customer_name, account_count,
                           transaction_count, total_transaction_amount,
                           last_transaction_date
                    FROM customer_360
                    WHERE customer_id = ?
                    """,
                    (customer_id,),
                ).fetchone()

        except sqlite3.Error:
            self.send_json(500, {"error": "Unable to retrieve customer summary"})
            return

        if row is None:
            self.send_json(404, {"error": "Customer not found"})
            return

        self.send_json(200, dict(row))

    def log_message(self, format_string, *args):
        """Keep routine HTTP access logs concise."""
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), CustomerSummaryHandler)
    print(f"Customer summary API running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping customer summary API.")
    finally:
        server.server_close()

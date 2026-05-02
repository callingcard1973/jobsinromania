#!/usr/bin/env python3
"""
Dashboard Server - Serves scraper dashboard with auto-refresh
Port: 8090
"""

import http.server
import socketserver
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

PORT = 8090
DATA_DIR = Path("/opt/DATA")
DASHBOARD_FILE = DATA_DIR / "scraper_dashboard.html"
JSON_FILE = DATA_DIR / "scraper_status.json"
ORGANIZER_SCRIPT = "/opt/ACTIVE/INFRA/SKILLS/scraper_organizer.py"

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DATA_DIR), **kwargs)

    def do_GET(self):
        # Refresh data on each request
        if self.path in ('/', '/scraper_dashboard.html', '/index.html'):
            try:
                subprocess.run(['python3', ORGANIZER_SCRIPT],
                             capture_output=True, timeout=30)
            except:
                pass
            self.path = '/scraper_dashboard.html'

        elif self.path == '/status':
            # Return JSON status
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                with open(JSON_FILE) as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b'{"error": "No data"}')
            return

        elif self.path == '/refresh':
            # Force refresh and redirect
            try:
                subprocess.run(['python3', ORGANIZER_SCRIPT],
                             capture_output=True, timeout=30)
            except:
                pass
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return

        return super().do_GET()

    def log_message(self, format, *args):
        # Quieter logging
        pass


def main():
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Dashboard server running at http://0.0.0.0:{PORT}")
        print(f"  Dashboard: http://localhost:{PORT}/")
        print(f"  JSON API:  http://localhost:{PORT}/status")
        print(f"  Refresh:   http://localhost:{PORT}/refresh")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == '__main__':
    main()

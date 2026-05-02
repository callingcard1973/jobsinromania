#!/usr/bin/env python3
"""Simple dashboard - serves static HTML, regenerates every minute"""
import subprocess
import threading
import time
from flask import Flask, send_file

app = Flask(__name__)

def regenerate():
    """Regenerate dashboard HTML every 60 seconds"""
    while True:
        try:
            subprocess.run(["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/static_dashboard_pure.py"], 
                         capture_output=True, timeout=30)
        except:
            pass
        time.sleep(60)

@app.route("/")
def index():
    return send_file("/opt/ACTIVE/INFRA/SKILLS/dashboard.html")

if __name__ == "__main__":
    # Start regeneration thread
    t = threading.Thread(target=regenerate, daemon=True)
    t.start()
    # Regenerate once at startup
    subprocess.run(["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/static_dashboard_pure.py"], capture_output=True)
    app.run(host="0.0.0.0", port=8085, debug=False)

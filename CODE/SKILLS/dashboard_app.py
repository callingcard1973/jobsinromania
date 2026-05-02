#!/usr/bin/env python3
"""Campaign Dashboard - Main app. Port 8097. Imports blueprints from modules."""
import sys, os
from flask import Flask, Response

app = Flask(__name__)
app.config["CONFIGS_DIRS"] = [
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs",
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs",
]
app.config["TEMPLATES_BASE"] = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates"
app.config["UPLOADS_DIR"] = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/uploads"
app.config["SENDER_SCRIPT"] = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"
app.config["QUICK_SCRIPT"] = "/opt/ACTIVE/INFRA/SKILLS/quick_campaign.py"
app.config["PYTHON"] = "/opt/ACTIVE/INFRA/venv/bin/python3"
app.config["DB_ANOFM"] = {"dbname": "anofm", "user": "tudor", "password": "tudor", "host": "localhost"}
app.config["DB_SENDER"] = {"dbname": "email_sender", "user": "tudor", "password": "tudor", "host": "localhost"}

from dashboard_campaigns import bp as campaigns_bp
from dashboard_senders import bp as senders_bp
from dashboard_upload import bp as upload_bp
from dashboard_stats import bp as stats_bp

app.register_blueprint(campaigns_bp)
app.register_blueprint(senders_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(stats_bp)

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Campaign Dashboard</title>
<style>
:root{--bg:#0f172a;--sf:#1e293b;--bd:#334155;--tx:#e2e8f0;--tm:#94a3b8;--ac:#38bdf8;--gn:#22c55e;--rd:#ef4444;--yl:#f59e0b}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:var(--bg);color:var(--tx);padding:0}
nav{background:var(--sf);border-bottom:1px solid var(--bd);padding:12px 20px;display:flex;gap:8px;align-items:center;position:sticky;top:0;z-index:10}
nav a{color:var(--tm);text-decoration:none;padding:8px 16px;border-radius:6px;font-size:14px;font-weight:500}
nav a:hover,nav a.active{color:var(--tx);background:var(--bd)}
nav h1{color:var(--ac);font-size:18px;margin-right:20px}
#content{padding:20px;max-width:1400px;margin:0 auto}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin:15px 0}
.card{background:var(--sf);border:1px solid var(--bd);border-radius:10px;padding:15px;text-align:center}
.card .num{font-size:28px;font-weight:bold;color:var(--ac)}.card .lbl{font-size:12px;color:var(--tm)}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}
th,td{padding:6px 10px;border:1px solid var(--bd);text-align:left}th{background:var(--sf);color:var(--tm)}
tr:hover{background:var(--sf)}
select,input[type=number],input[type=text],input[type=file]{background:var(--sf);color:var(--tx);border:1px solid var(--bd);padding:5px 8px;border-radius:4px;font-size:12px}
textarea{background:var(--sf);color:var(--tx);border:1px solid var(--bd);padding:8px;border-radius:4px;width:100%;font-family:monospace;font-size:12px}
button,.btn{background:var(--ac);color:var(--bg);border:none;padding:6px 14px;border-radius:5px;cursor:pointer;font-weight:600;font-size:12px}
button:hover{opacity:0.85}.btn-red{background:var(--rd)}.btn-green{background:var(--gn)}.btn-yellow{background:var(--yl)}
.on{color:var(--gn);font-weight:bold}.off{color:var(--rd)}
.badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:bold}
.badge-brevo{background:#3b82f633;color:#60a5fa}.badge-gmail{background:#ef444433;color:#f87171}
.badge-a2{background:#22c55e33;color:#4ade80}.badge-zoho{background:#a855f733;color:#c084fc}
.msg{padding:10px;margin:10px 0;border-radius:6px;background:#22c55e33;color:var(--gn);display:none}
.tab{display:none}.tab.active{display:block}
h2{color:var(--ac);margin:20px 0 10px;font-size:16px;border-bottom:1px solid var(--bd);padding-bottom:6px}
</style></head><body>
<nav>
<h1>📧 Campaign Dashboard</h1>
<a href="#" onclick="show('campaigns')" class="active" id="nav-campaigns">Campaigns</a>
<a href="#" onclick="show('upload')" id="nav-upload">Upload CSV</a>
<a href="#" onclick="show('senders')" id="nav-senders">Senders</a>
<a href="#" onclick="show('stats')" id="nav-stats">Stats</a>
</nav>
<div id="content">
<div id="msg" class="msg"></div>
<div id="campaigns" class="tab active"></div>
<div id="upload" class="tab"></div>
<div id="senders" class="tab"></div>
<div id="stats" class="tab"></div>
</div>
<script>
function show(tab){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('nav a').forEach(a=>a.classList.remove('active'));
  document.getElementById(tab).classList.add('active');
  document.getElementById('nav-'+tab).classList.add('active');
  if(window['load_'+tab]) window['load_'+tab]();
}
function msg(txt,err){const e=document.getElementById('msg');e.textContent=txt;e.style.display='block';
  e.style.background=err?'#ef444433':'#22c55e33';e.style.color=err?'var(--rd)':'var(--gn)';
  setTimeout(()=>e.style.display='none',4000);}
const BASE=window.location.pathname.replace(/\/$/,'');
async function api(url,opts){const r=await fetch(BASE+url,opts);return r.json();}
async function post(url,data){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
window.onload=()=>show('campaigns');
</script>
<script>const _b=window.location.pathname.replace(/\/$/,'');</script>
<script src="static/campaigns.js"></script>
<script src="static/upload.js"></script>
<script src="static/senders.js"></script>
<script src="static/stats.js"></script>
</body></html>"""

@app.route("/")
def index():
    return Response(HTML, content_type="text/html")

# Serve inline JS as static files
from dashboard_shared import JS_FILES

@app.route("/static/<name>")
def static_js(name):
    if name not in JS_FILES:
        return Response("", content_type="application/javascript")
    return Response(JS_FILES[name], content_type="application/javascript")

if __name__ == "__main__":
    os.makedirs(app.config["UPLOADS_DIR"], exist_ok=True)
    port = int(sys.argv[sys.argv.index("--port")+1]) if "--port" in sys.argv else 8097
    ssl_ctx = None
    cert = "/opt/ACTIVE/INFRA/ssl/dashboard.crt"
    key = "/opt/ACTIVE/INFRA/ssl/dashboard.key"
    if os.path.exists(cert) and os.path.exists(key) and "--no-ssl" not in sys.argv:
        ssl_ctx = (cert, key)
        print(f"HTTPS enabled on port {port}")
    app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, debug=False)

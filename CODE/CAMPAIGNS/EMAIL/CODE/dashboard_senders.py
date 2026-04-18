"""Sender inventory blueprint - all senders with utilization."""
import psycopg2
from datetime import date
from flask import Blueprint, jsonify, current_app

bp = Blueprint("senders", __name__)

BREVO = [
    ("buildjobs.eu","BREVO_BUILDJOBS_API_KEY",290),("factoryjobs.eu","BREVO_FACTORYJOBS_API_KEY",290),
    ("warehouseworkers.eu","BREVO_WAREHOUSEWORKERS_API_KEY",290),("interjob.ro","BREVO_INTERJOB_API_KEY",290),
    ("mivromania.info","BREVO_MIVROMANIA_API_KEY",290),("mivromania.online","BREVO_MIVROMANIA_ONLINE_API_KEY",290),
    ("careworkers.eu","BREVO_CAREWORKERS_API_KEY",290),("nepalezi.com","BREVO_NEPALEZI_API_KEY",290),
    ("expatsinromania.org","BREVO_EXPATSINROMANIA_API_KEY",290),
    ("horecaworkers2026.eu","BREVO_HORECAWORKERS2026_EU_API_KEY",290),
    ("horecaworkers2026.com","BREVO_HORECAWORKERS2026_COM_API_KEY",290),
    ("electricjobs.eu","BREVO_ELECTRICJOBS_API_KEY",290),("meatworkers.eu","BREVO_MEATWORKERS_API_KEY",290),
    ("cumparlegume.com","BREVO_CUMPARLEGUME_API_KEY",290),("agroevolution.com","BREVO_AGROEVOLUTION_API_KEY",290),
    ("seicarescu.com","BREVO_SEICARESCU_API_KEY",280),("bppltd.co.uk","BREVO_BPPLTD_API_KEY",289),
    ("farmworkers.eu","BREVO_FARMWORKERS_API_KEY",290),("mechanicjobs.eu","BREVO_MECHANICJOBS_API_KEY",290),
    ("horecaworkers.eu","BREVO_HORECAWORKERS_API_KEY",290),
]
A2 = [d for d,_,_ in BREVO] + ["aluminumrecyclehub.com","internaltransfers.eu"]
GMAIL = [
    ("manpowersearchromania@gmail.com","GMAIL_MANPOWERSEARCH",40),
    ("pamintstrabun@gmail.com","GMAIL_PAMINTSTRABUN",40),
    ("casafaurbucuresti@gmail.com","GMAIL_CASAFAUR",40),
    ("elena.manpower.dristor@gmail.com","GMAIL_ELENA",40),
    ("cumparlegume@gmail.com","GMAIL_CUMPARLEGUME",40),
    ("fructexportromania@gmail.com","GMAIL_FRUCTEXPORT",40),
    ("carteledeapel@gmail.com","GMAIL_CARTELEDEAPEL",40),
    ("vegetablesbucharest@gmail.com","GMAIL_VEGETABLES",40),
    ("expatsinromania@gmail.com","GMAIL_EXPATS",40),
    ("icralbucuresti@gmail.com","GMAIL_ICRALBUCURESTI",40),
]
ZOHO = [
    ("transport.work@zohomail.com","ZOHO_SMTP_PASSWORD",30),
    ("workers.europe@zohomail.eu","ZOHO_PASSWORD_2",5),
]

def get_today_sends():
    """Get today's send counts per sender from send_log."""
    try:
        conn = psycopg2.connect(**current_app.config["DB_ANOFM"])
        cur = conn.cursor()
        cur.execute("SELECT sender, count(*) FROM send_log WHERE sent_at::date = %s GROUP BY sender", (date.today(),))
        result = {r[0]: r[1] for r in cur.fetchall()}
        conn.close()
        return result
    except:
        return {}

@bp.route("/api/senders")
def list_senders():
    usage = get_today_sends()
    senders = []
    for domain, key, limit in BREVO:
        email = f"office@{domain}"
        senders.append({"type": "brevo", "email": email, "key": key, "max": limit,
            "used": usage.get(email, 0), "domain": domain})
    for domain in A2:
        email = f"office@{domain}"
        senders.append({"type": "a2", "email": email, "key": f"A2_{domain}", "max": 50,
            "used": usage.get(email, 0), "domain": domain})
    for email, key, limit in GMAIL:
        senders.append({"type": "gmail", "email": email, "key": key, "max": limit,
            "used": usage.get(email, 0), "domain": email})
    for email, key, limit in ZOHO:
        senders.append({"type": "zoho", "email": email, "key": key, "max": limit,
            "used": usage.get(email, 0), "domain": email})
    return jsonify({"senders": senders})

from dashboard_shared import register_js
register_js("senders.js", """
async function load_senders(){
  const d=await api('/api/senders');
  let h='<h2>Senders</h2>';
  const types=['brevo','a2','gmail','zoho'];
  types.forEach(t=>{
    const s=d.senders.filter(x=>x.type==t);if(!s.length)return;
    h+='<h2><span class="badge badge-'+t+'">'+t.toUpperCase()+'</span> ('+s.length+')</h2>';
    h+='<table><thead><tr><th>Sender</th><th>Key</th><th>Max/day</th><th>Used today</th><th>Available</th><th>%</th></tr></thead><tbody>';
    s.forEach(x=>{
      const pct=x.max>0?Math.round(x.used/x.max*100):0;
      const bar='<div style="background:var(--bd);border-radius:3px;height:14px;width:80px;display:inline-block"><div style="background:'+(pct>80?'var(--rd)':pct>50?'var(--yl)':'var(--gn)')+';height:100%;width:'+pct+'%;border-radius:3px"></div></div>';
      h+='<tr><td>'+x.email+'</td><td style="font-size:10px;color:var(--tm)">'+x.key+'</td><td>'+x.max+'</td><td>'+x.used+'</td><td>'+(x.max-x.used)+'</td><td>'+bar+' '+pct+'%</td></tr>';
    });
    h+='</tbody></table>';
  });
  document.getElementById('senders').innerHTML=h;
}
""")

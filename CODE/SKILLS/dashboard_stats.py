"""Stats/analytics blueprint - sends per day, campaign, method, bounce rates."""
import psycopg2
from datetime import date, timedelta
from flask import Blueprint, jsonify, current_app

bp = Blueprint("stats", __name__)

def query(db_key, sql, params=None):
    try:
        conn = psycopg2.connect(**current_app.config[db_key])
        cur = conn.cursor()
        cur.execute(sql, params or ())
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        return [{"error": str(e)}]

@bp.route("/api/stats/summary")
def summary():
    today = date.today()
    week_ago = today - timedelta(days=7)
    # Today from global_sends (covers ALL campaigns, ALL DBs)
    today_sends = query("DB_SENDER", "SELECT count(*) as cnt FROM global_sends WHERE sent_date = %s", (today,))
    total_today = today_sends[0].get("cnt", 0) if today_sends else 0
    # Also add anofm.send_log sends not in global_sends
    anofm_today = query("DB_ANOFM", "SELECT count(*) as cnt FROM send_log WHERE sent_at::date = %s", (today,))
    anofm_cnt = anofm_today[0].get("cnt", 0) if anofm_today else 0
    total_today = max(total_today, anofm_cnt)  # take the higher count
    # 7-day trend from global_sends
    trend = query("DB_SENDER", """SELECT sent_date as day, count(*) as cnt
        FROM global_sends WHERE sent_date >= %s GROUP BY sent_date ORDER BY sent_date""", (week_ago,))
    # By campaign today from global_sends
    campaigns = query("DB_SENDER", """SELECT campaign, count(*) as cnt
        FROM global_sends WHERE sent_date = %s GROUP BY campaign ORDER BY cnt DESC LIMIT 15""", (today,))
    # By sender today from global_sends
    methods = query("DB_SENDER", """SELECT sender, count(*) as cnt
        FROM global_sends WHERE sent_date = %s GROUP BY sender ORDER BY cnt DESC LIMIT 15""", (today,))
    # Total all time
    global_sends = query("DB_SENDER", "SELECT count(*) as cnt FROM global_sends")
    total_all = query("DB_ANOFM", "SELECT count(*) as cnt FROM send_log")
    # DNC count
    dnc = query("DB_ANOFM", "SELECT count(*) as cnt FROM dnc")
    return jsonify({
        "today": total_today,
        "total": global_sends[0].get("cnt", 0) if global_sends else 0,
        "global_sends": global_sends[0].get("cnt", 0) if global_sends else 0,
        "anofm_sends": total_all[0].get("cnt", 0) if total_all else 0,
        "dnc": dnc[0].get("cnt", 0) if dnc else 0,
        "trend": trend, "methods": methods, "campaigns": campaigns
    })

@bp.route("/api/stats/senders")
def sender_stats():
    today = date.today()
    data = query("DB_ANOFM", """SELECT sender, method, count(*) as cnt
        FROM send_log WHERE sent_at::date = %s AND sender IS NOT NULL
        GROUP BY sender, method ORDER BY cnt DESC""", (today,))
    return jsonify({"sender_stats": data})

@bp.route("/api/stats/bounces")
def bounce_stats():
    data = query("DB_SENDER", """SELECT sender, count(*) as total,
        count(*) FILTER (WHERE campaign = 'bounce') as bounced
        FROM global_sends GROUP BY sender ORDER BY total DESC LIMIT 20""")
    return jsonify({"bounce_stats": data})

@bp.route("/api/stats/campaign/<name>")
def campaign_stats(name):
    trend = query("DB_ANOFM", """SELECT sent_at::date as day, count(*) as cnt
        FROM send_log WHERE campaign ILIKE %s GROUP BY day ORDER BY day DESC LIMIT 30""", (f"%{name}%",))
    by_sender = query("DB_ANOFM", """SELECT sender, count(*) as cnt
        FROM send_log WHERE campaign ILIKE %s GROUP BY sender ORDER BY cnt DESC""", (f"%{name}%",))
    total = query("DB_ANOFM", "SELECT count(*) as cnt FROM send_log WHERE campaign ILIKE %s", (f"%{name}%",))
    return jsonify({"name": name, "total": total[0].get("cnt", 0) if total else 0,
        "trend": trend, "by_sender": by_sender})

from dashboard_shared import register_js
register_js("stats.js", """
async function load_stats(){
  const d=await api('/api/stats/summary');
  let h='<h2>Stats Overview</h2>';
  h+='<div class="cards">';
  h+='<div class="card"><div class="num">'+d.today+'</div><div class="lbl">Sent Today</div></div>';
  h+='<div class="card"><div class="num">'+d.total+'</div><div class="lbl">Total (DB)</div></div>';
  h+='<div class="card"><div class="num">'+d.global_sends+'</div><div class="lbl">Global Sends</div></div>';
  h+='<div class="card"><div class="num" style="color:var(--rd)">'+d.dnc+'</div><div class="lbl">DNC</div></div>';
  h+='</div>';
  // 7-day trend
  if(d.trend.length){
    h+='<h2>7-Day Trend</h2><table><thead><tr><th>Date</th><th>Sent</th><th>Bar</th></tr></thead><tbody>';
    const mx=Math.max(...d.trend.map(t=>t.cnt));
    d.trend.forEach(t=>{
      const w=Math.round(t.cnt/mx*200);
      h+='<tr><td>'+t.day+'</td><td>'+t.cnt+'</td><td><div style="background:var(--ac);height:16px;width:'+w+'px;border-radius:3px"></div></td></tr>';
    });
    h+='</tbody></table>';
  }
  // By method
  if(d.methods.length){
    h+='<h2>Today by Sender</h2><table><thead><tr><th>Sender</th><th>Count</th></tr></thead><tbody>';
    d.methods.forEach(m=>h+='<tr><td>'+(m.sender||'?')+'</td><td>'+m.cnt+'</td></tr>');
    h+='</tbody></table>';
  }
  // By campaign
  if(d.campaigns.length){
    h+='<h2>Today by Campaign</h2><table><thead><tr><th>Campaign</th><th>Count</th></tr></thead><tbody>';
    d.campaigns.forEach(c=>h+='<tr><td>'+c.campaign+'</td><td>'+c.cnt+'</td></tr>');
    h+='</tbody></table>';
  }
  document.getElementById('stats').innerHTML=h;
}
""")

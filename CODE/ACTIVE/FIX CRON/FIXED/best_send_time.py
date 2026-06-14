#!/usr/bin/env python3
"""F3: Recompute send_time_stats from send_log + reply detection. Cron weekly Sun 02:00."""
import sys, psycopg2
sys.path.insert(0, "/opt/ACTIVE/INFRA/SKILLS")
from email_pipeline_db import DB_CFG

def main():
    conn = psycopg2.connect(**DB_CFG); cur = conn.cursor()
    cur.execute("TRUNCATE send_time_stats")
    cur.execute("""INSERT INTO send_time_stats (country, sector, hour_of_day, day_of_week, sends_count, replies_count)
        SELECT COALESCE(me.country_detected,'XX') AS country,
               COALESCE(SUBSTRING(me.industry,1,40),'general') AS sector,
               EXTRACT(HOUR FROM sl.sent_at)::SMALLINT AS hour,
               EXTRACT(DOW FROM sl.sent_at)::SMALLINT AS dow,
               COUNT(*) AS sends,
               SUM(CASE WHEN me.campaign_status IN ('replied','comanda','interesat','partener') THEN 1 ELSE 0 END) AS replies
        FROM send_log sl
        LEFT JOIN master_emails me ON LOWER(me.email)=LOWER(sl.email)
        WHERE sl.sent_at > NOW() - INTERVAL '180 days'
        GROUP BY COALESCE(me.country_detected,'XX'), COALESCE(SUBSTRING(me.industry,1,40),'general'), EXTRACT(HOUR FROM sl.sent_at)::SMALLINT, EXTRACT(DOW FROM sl.sent_at)::SMALLINT""")
    n = cur.rowcount; conn.commit()
    cur.execute("""SELECT country, hour_of_day, day_of_week,
        ROUND(100.0*replies_count/NULLIF(sends_count,0),2) AS rate
        FROM send_time_stats WHERE sends_count >= 20
        ORDER BY rate DESC NULLS LAST LIMIT 5""")
    print(f"Aggregated {n} rows. Top 5 (country, hour, dow, reply%):")
    for r in cur.fetchall(): print(f"  {r}")
    conn.close()

if __name__ == "__main__": main()

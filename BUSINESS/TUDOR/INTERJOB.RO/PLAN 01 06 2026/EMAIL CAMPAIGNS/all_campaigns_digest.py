#!/usr/bin/env python3
"""Unified daily digest for ALL email campaigns -> one email to Tudor.
Data-driven: campaigns.json (enabled) x each SENT_FILE + Brevo aggregated per account."""
import json,urllib.request,urllib.parse
from pathlib import Path
from datetime import date
DIR=Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
ENV={}
for ln in open(DIR/'.env'):
    if '=' in ln and not ln.lstrip().startswith('#'):
        k,_,v=ln.partition('='); ENV[k.strip()]=v.strip()
today=str(date.today())
camps=json.load(open(DIR/'campaigns.json')).get('campaigns',[])
rows=[]; tot_today=tot_all=0
for c in camps:
    if not c.get('enabled'): continue
    sf=(c.get('env') or {}).get('SENT_FILE')
    n_t=n_a=0
    if sf and Path(sf).exists():
        try:
            s=json.load(open(sf)); n_a=s.get('total',0); n_t=len(s.get('by_date',{}).get(today,[]))
        except Exception: pass
    tot_today+=n_t; tot_all+=n_a
    rows.append((c['name'], c.get('brevo_account','-'), n_t, n_a, c.get('daily_cap',c.get('daily_limit','-'))))
# EURES outreach tracks sends in DB (eures_send_log), not a SENT_FILE -> read directly
try:
    import psycopg2
    _cn=psycopg2.connect(host="/var/run/postgresql",dbname="interjob_master",user="tudor"); _cu=_cn.cursor()
    _cu.execute("select count(*) filter(where sent_at::date=current_date and status=%s), count(*) filter(where status=%s) from eures_send_log",("sent","sent"))
    _et,_ea=_cu.fetchone(); _cn.close()
    tot_today+=_et or 0; tot_all+=_ea or 0
    rows.append(("EURES_OUTREACH","BPPLTD",_et or 0,_ea or 0,150))
except Exception as _e:
    rows.append(("EURES_OUTREACH","BPPLTD",0,0,150))

rows.sort(key=lambda r:-r[2])
def agg(key):
    if not key: return {}
    try:
        r=urllib.request.Request('https://api.brevo.com/v3/smtp/statistics/aggregatedReport?days=1',headers={'api-key':key})
        return json.load(urllib.request.urlopen(r,timeout=20))
    except Exception: return {}
# brevo per distinct account key in .env
accs={}
for c in camps:
    a=c.get('brevo_account')
    if a and a not in accs:
        k=ENV.get(f'BREVO_{a}_API_KEY','')
        if k: accs[a]=agg(k)
if "BPPLTD" not in accs:
    _bk=""
    try:
        for _ln in open("/opt/ACTIVE/EURES/.env"):
            if _ln.startswith("BREVO_BPPLTD_API_KEY="): _bk=_ln.split("=",1)[1].strip(); break
    except Exception: pass
    if _bk: accs["BPPLTD"]=agg(_bk)

lines=[f'EMAIL CAMPAIGNS digest {today}','',f'Enabled campaigns: {len(rows)} | sent today: {tot_today} | sent total: {tot_all}','',
       f'{"CAMPAIGN":24} {"ACCT":12} {"TODAY":>5} {"TOTAL":>7} {"CAP":>5}']
for nm,ac,nt,na,cap in rows:
    lines.append(f'{nm[:24]:24} {str(ac)[:12]:12} {nt:>5} {na:>7} {str(cap):>5}')
lines+=['','Brevo (last 1d) per account:']
for a,d in accs.items():
    lines.append(f'  {a:12} deliv {d.get("delivered","?")} hardB {d.get("hardBounces","?")} softB {d.get("softBounces","?")} opens {d.get("uniqueOpens","?")} unsub {d.get("unsubscribed","?")}')
body='\n'.join(lines)
KEY=ENV.get('BREVO_CUMPARLEGUME_API_KEY','')
payload={'sender':{'email':'office@cumparlegume.com','name':'Campaigns Digest'},'to':[{'email':'fruitnature4@gmail.com'}],'subject':f'Email campaigns digest {today} - {tot_today} sent today','textContent':body}
try:
    r=urllib.request.urlopen(urllib.request.Request('https://api.brevo.com/v3/smtp/email',data=json.dumps(payload).encode(),headers={'api-key':KEY,'Content-Type':'application/json'},method='POST'),timeout=30); print('SENT HTTP',r.status)
except Exception as e: print('FAIL',e)
print(body)

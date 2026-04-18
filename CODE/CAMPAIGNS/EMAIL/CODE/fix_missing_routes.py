#!/usr/bin/env python3
"""Add missing page routes to bp_pages.py: index, overview, edit, template."""
import os

OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
path = os.path.join(OUT, "bp_pages.py")

with open(path) as f:
    content = f.read()

# Check what's already there
if "def index" in content and "def campaign_template" in content:
    print("Routes already present")
    exit(0)

# Append missing routes
append = '''

@pages_bp.route('/')
def index():
    tudor_campaigns, lucian_campaigns, raspi_campaigns = {}, {}, {}
    for prefix, cfg in CAMPAIGNS.items():
        owner = get_owner(cfg)
        if owner == 'lucian': lucian_campaigns[prefix] = cfg
        elif owner == 'raspi': raspi_campaigns[prefix] = cfg
        else: tudor_campaigns[prefix] = cfg
    return render_template_string(INDEX_HTML, styles=STYLES,
        total_count=len(CAMPAIGNS), tudor_count=len(tudor_campaigns),
        lucian_count=len(lucian_campaigns), raspi_count=len(raspi_campaigns),
        tudor_campaigns=tudor_campaigns, lucian_campaigns=lucian_campaigns,
        raspi_campaigns=raspi_campaigns)


@pages_bp.route('/<prefix>/')
def campaign_overview(prefix):
    cfg = CAMPAIGNS.get(prefix)
    if not cfg: return "Campaign not found", 404
    stats = campaign_stats(cfg)
    return render_template_string(CAMPAIGN_HTML, styles=STYLES,
        cfg=cfg, stats=stats, prefix=prefix, owner=get_owner(cfg),
        nav=nav_html(prefix, 'overview'))


@pages_bp.route('/<prefix>/edit')
def campaign_edit(prefix):
    cfg = CAMPAIGNS.get(prefix)
    if not cfg: return "Campaign not found", 404
    msg = request.args.get('msg', '')
    msg_type = request.args.get('msg_type', 'success')
    return render_template_string(EDIT_HTML, styles=STYLES,
        cfg=cfg, prefix=prefix, senders=SENDERS,
        msg=msg, msg_type=msg_type, nav=nav_html(prefix, 'edit'))


@pages_bp.route('/<prefix>/template')
def campaign_template(prefix):
    cfg = CAMPAIGNS.get(prefix)
    if not cfg: return "Campaign not found", 404
    template_path = get_template_path(cfg)
    content = ''
    if template_path and os.path.exists(template_path):
        try:
            with open(template_path) as f:
                content = f.read()
        except Exception as e:
            content = str(e)
    msg = request.args.get('msg', '')
    msg_type = request.args.get('msg_type', 'success')
    db_columns = []
    try:
        db_cfg = cfg.get('db', {})
        tbl_cfg = cfg.get('tables', {})
        contacts_tbl = tbl_cfg.get('contacts', 'contacts')
        conn = psycopg2.connect(host=db_cfg.get('host', 'localhost'),
            dbname=db_cfg.get('dbname', 'interjob_master'),
            user=db_cfg.get('user', 'tudor'), password=db_cfg.get('password', 'tudor'))
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", (contacts_tbl,))
        db_columns = [r[0] for r in cur.fetchall() if r[0] not in ('id', 'campaign_status', 'last_contacted')]
        cur.close(); conn.close()
    except Exception:
        pass
    return render_template_string(TEMPLATE_HTML, styles=STYLES,
        cfg=cfg, prefix=prefix, template_path=template_path, content=content,
        msg=msg, msg_type=msg_type, db_columns=db_columns,
        nav=nav_html(prefix, 'template'))
'''

with open(path, "a") as f:
    f.write(append)

n = sum(1 for _ in open(path))
print("bp_pages.py: " + str(n) + " lines")

#!/usr/bin/env python3
"""
Odoo Helper - Direct database operations for Odoo CRM
"""

import subprocess
import json
from typing import Optional, List, Dict, Any

DOCKER_CMD = ["docker", "exec", "odoo-db", "psql", "-U", "odoo", "-d", "master_odoo", "-t", "-A"]

def run_sql(query: str) -> str:
    """Execute SQL query on Odoo database"""
    cmd = DOCKER_CMD + ["-c", query]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"SQL Error: {result.stderr}")
    return result.stdout.strip()

def run_sql_json(query: str) -> List[Dict]:
    """Execute SQL and return as JSON"""
    # Wrap query to return JSON
    json_query = f"SELECT json_agg(t) FROM ({query}) t"
    result = run_sql(json_query)
    if result and result != '':
        return json.loads(result) or []
    return []

# =============================================================================
# Lead Operations
# =============================================================================

def create_lead(
    name: str,
    contact_name: str = None,
    email: str = None,
    phone: str = None,
    description: str = None,
    source_id: int = None,
    campaign_id: int = None,
    company: str = None
) -> int:
    """Create a new lead in Odoo CRM"""
    fields = ["name", "type", "create_uid", "write_uid", "create_date", "write_date"]
    values = [f"'{name}'", "'lead'", "2", "2", "NOW()", "NOW()"]

    if contact_name:
        fields.append("contact_name")
        values.append(f"'{contact_name}'")
    if email:
        fields.append("email_from")
        values.append(f"'{email}'")
    if phone:
        fields.append("phone")
        values.append(f"'{phone}'")
    if description:
        fields.append("description")
        values.append(f"'{description.replace(chr(39), chr(39)+chr(39))}'")
    if source_id:
        fields.append("source_id")
        values.append(str(source_id))
    if campaign_id:
        fields.append("campaign_id")
        values.append(str(campaign_id))
    if company:
        fields.append("partner_name")
        values.append(f"'{company}'")

    query = f"INSERT INTO crm_lead ({', '.join(fields)}) VALUES ({', '.join(values)}) RETURNING id"
    result = run_sql(query)
    # Parse ID from result (may have extra lines)
    return int(result.split('\n')[0].strip())

def get_leads(limit: int = 20, stage_id: int = None) -> List[Dict]:
    """Get leads from CRM"""
    where = f"WHERE stage_id = {stage_id}" if stage_id else ""
    query = f"""
        SELECT l.id, l.name, l.contact_name, l.email_from, l.phone,
               s.name as stage_name, src.name as source_name,
               l.create_date
        FROM crm_lead l
        LEFT JOIN crm_stage s ON l.stage_id = s.id
        LEFT JOIN utm_source src ON l.source_id = src.id
        {where}
        ORDER BY l.create_date DESC
        LIMIT {limit}
    """
    return run_sql_json(query)

def update_lead_stage(lead_id: int, stage_id: int) -> bool:
    """Move lead to different stage"""
    query = f"UPDATE crm_lead SET stage_id = {stage_id}, write_date = NOW() WHERE id = {lead_id}"
    run_sql(query)
    return True

def search_lead_by_email(email: str) -> Optional[Dict]:
    """Find lead by email"""
    query = f"""
        SELECT l.id, l.name, l.contact_name, l.email_from, l.stage_id
        FROM crm_lead l
        WHERE l.email_from = '{email}'
        ORDER BY l.create_date DESC
        LIMIT 1
    """
    results = run_sql_json(query)
    return results[0] if results else None

# =============================================================================
# Stage Operations
# =============================================================================

def get_stages() -> List[Dict]:
    """Get all pipeline stages"""
    query = "SELECT id, name, sequence, is_won, fold FROM crm_stage ORDER BY sequence"
    return run_sql_json(query)

def get_stage_id(name: str) -> Optional[int]:
    """Get stage ID by name"""
    query = f"SELECT id FROM crm_stage WHERE name::text ILIKE '%{name}%' LIMIT 1"
    result = run_sql(query)
    return int(result) if result else None

# =============================================================================
# Source Operations
# =============================================================================

def get_sources() -> List[Dict]:
    """Get all UTM sources"""
    query = "SELECT id, name FROM utm_source ORDER BY name"
    return run_sql_json(query)

def get_source_id(name: str) -> Optional[int]:
    """Get source ID by name"""
    query = f"SELECT id FROM utm_source WHERE name = '{name}' LIMIT 1"
    result = run_sql(query)
    return int(result) if result else None

# =============================================================================
# Statistics
# =============================================================================

def get_pipeline_stats() -> List[Dict]:
    """Get lead count by stage"""
    query = """
        SELECT s.name, s.sequence, COUNT(l.id) as count
        FROM crm_stage s
        LEFT JOIN crm_lead l ON l.stage_id = s.id
        GROUP BY s.id, s.name, s.sequence
        ORDER BY s.sequence
    """
    return run_sql_json(query)

def get_leads_by_source() -> List[Dict]:
    """Get lead count by source"""
    query = """
        SELECT src.name as source, COUNT(l.id) as count
        FROM crm_lead l
        LEFT JOIN utm_source src ON l.source_id = src.id
        GROUP BY src.name
        ORDER BY count DESC
    """
    return run_sql_json(query)

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: odoo_helper.py <command> [args]")
        print("Commands:")
        print("  stages        - List pipeline stages")
        print("  sources       - List UTM sources")
        print("  leads [n]     - List recent leads")
        print("  stats         - Pipeline statistics")
        print("  create <name> <email> [phone] [source] - Create lead")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "stages":
        for s in get_stages():
            name = s['name'] if isinstance(s['name'], str) else s['name'].get('en_US', str(s['name']))
            print(f"{s['id']:3} | {name:30} | seq={s['sequence']}")

    elif cmd == "sources":
        for s in get_sources():
            print(f"{s['id']:3} | {s['name']}")

    elif cmd == "leads":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        for l in get_leads(limit):
            stage = l.get('stage_name', '')
            if isinstance(stage, dict):
                stage = stage.get('en_US', str(stage))
            print(f"{l['id']:5} | {str(l['name'])[:30]:30} | {l['email_from'] or '':30} | {stage}")

    elif cmd == "stats":
        print("\n=== Pipeline Stats ===")
        for s in get_pipeline_stats():
            name = s['name'] if isinstance(s['name'], str) else s['name'].get('en_US', str(s['name']))
            print(f"{name:30} | {s['count']:5} leads")

    elif cmd == "create":
        if len(sys.argv) < 4:
            print("Usage: create <name> <email> [phone] [source]")
            sys.exit(1)
        name = sys.argv[2]
        email = sys.argv[3]
        phone = sys.argv[4] if len(sys.argv) > 4 else None
        source = sys.argv[5] if len(sys.argv) > 5 else None
        source_id = get_source_id(source) if source else None

        lead_id = create_lead(name=name, email=email, phone=phone, source_id=source_id)
        print(f"Created lead ID: {lead_id}")

    else:
        print(f"Unknown command: {cmd}")

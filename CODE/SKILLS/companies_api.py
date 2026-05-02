#!/usr/bin/env python3
"""
B2B Contact Search API - REST API on PostgreSQL opendata.

Copy this file to: /opt/ACTIVE/INFRA/SKILLS/companies_api.py

Endpoints:
    GET /api/search?country=RO&caen=8220&city=Bucuresti&has_email=true&limit=100
    GET /api/company/{id}
    GET /api/sectors
    GET /api/export?country=RO&caen=55*
    GET /api/stats
    GET /api/health

Port: 8090
"""

import csv
import io
from flask import Flask, request, jsonify, Response
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Rate limiting (simple in-memory)
rate_limits = defaultdict(list)
RATE_LIMIT = 100  # requests per hour


def get_db():
    """Get PostgreSQL connection to opendata database."""
    return psycopg2.connect(
        dbname='opendata',
        user='tudor',
        host='',  # Unix socket for peer auth
        port=5432
    )


def rate_limit(f):
    """Simple rate limiting decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        rate_limits[ip] = [t for t in rate_limits[ip] if t > hour_ago]
        if len(rate_limits[ip]) >= RATE_LIMIT:
            return jsonify({'error': 'Rate limit exceeded', 'limit': RATE_LIMIT}), 429
        rate_limits[ip].append(now)
        return f(*args, **kwargs)
    return decorated


@app.route('/api/health')
def health():
    """Health check endpoint."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return jsonify({'status': 'healthy'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/api/stats')
@rate_limit
def stats():
    """Database statistics."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM companies")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM companies WHERE country = 'RO'")
    romanian = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM companies WHERE caen_code IS NOT NULL")
    with_caen = cur.fetchone()[0]

    cur.execute("SELECT contact_type, COUNT(*) FROM contacts GROUP BY contact_type")
    contacts = dict(cur.fetchall())

    conn.close()

    return jsonify({
        'companies': {'total': total, 'romanian': romanian, 'with_caen': with_caen},
        'contacts': contacts
    })


@app.route('/api/sectors')
@rate_limit
def sectors():
    """CAEN codes with company counts."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT caen_code, caen_description, COUNT(*) as count
        FROM companies
        WHERE caen_code IS NOT NULL AND country = 'RO'
        GROUP BY caen_code, caen_description
        ORDER BY count DESC
        LIMIT 100
    """)

    results = [{'code': r[0], 'description': r[1], 'count': r[2]} for r in cur.fetchall()]
    conn.close()

    return jsonify({'sectors': results})


@app.route('/api/search')
@rate_limit
def search():
    """Search companies with filters."""
    country = request.args.get('country', 'RO')
    caen = request.args.get('caen')
    city = request.args.get('city')
    name = request.args.get('name')
    has_email = request.args.get('has_email', '').lower() == 'true'
    has_phone = request.args.get('has_phone', '').lower() == 'true'
    limit = min(int(request.args.get('limit', 100)), 1000)
    offset = int(request.args.get('offset', 0))

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    conditions = ["country = %s"]
    params = [country]

    if caen:
        if '*' in caen:
            conditions.append("caen_code LIKE %s")
            params.append(caen.replace('*', '%'))
        else:
            codes = [c.strip() for c in caen.split(',')]
            if len(codes) == 1:
                conditions.append("caen_code = %s")
                params.append(codes[0])
            else:
                conditions.append("caen_code IN %s")
                params.append(tuple(codes))

    if city:
        conditions.append("city ILIKE %s")
        params.append(f"%{city}%")

    if name:
        conditions.append("name ILIKE %s")
        params.append(f"%{name}%")

    if has_email:
        conditions.append("""EXISTS (
            SELECT 1 FROM contacts WHERE company_id = companies.id AND contact_type = 'email'
        )""")

    if has_phone:
        conditions.append("""EXISTS (
            SELECT 1 FROM contacts WHERE company_id = companies.id AND contact_type = 'phone'
        )""")

    where = " AND ".join(conditions)

    # Count
    cur.execute(f"SELECT COUNT(*) FROM companies WHERE {where}", params)
    total = cur.fetchone()['count']

    # Results
    cur.execute(f"""
        SELECT id, name, company_number, city, region, caen_code, caen_description
        FROM companies
        WHERE {where}
        ORDER BY name
        LIMIT %s OFFSET %s
    """, params + [limit, offset])

    companies = [dict(row) for row in cur.fetchall()]

    # Get contacts for each company
    for c in companies:
        cur.execute("""
            SELECT contact_type, contact_value FROM contacts WHERE company_id = %s
        """, (c['id'],))
        c['contacts'] = [{'type': r['contact_type'], 'value': r['contact_value']} for r in cur.fetchall()]

    conn.close()

    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'results': companies
    })


@app.route('/api/company/<int:company_id>')
@rate_limit
def company(company_id):
    """Get single company with all details."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
    company = cur.fetchone()

    if not company:
        conn.close()
        return jsonify({'error': 'Company not found'}), 404

    company = dict(company)
    cur.execute("""
        SELECT contact_type, contact_value, contact_name FROM contacts WHERE company_id = %s
    """, (company_id,))
    company['contacts'] = [dict(r) for r in cur.fetchall()]

    conn.close()
    return jsonify(company)


@app.route('/api/export')
@rate_limit
def export():
    """Export search results as CSV."""
    country = request.args.get('country', 'RO')
    caen = request.args.get('caen')
    has_email = request.args.get('has_email', '').lower() == 'true'
    limit = min(int(request.args.get('limit', 1000)), 10000)

    if not caen:
        return jsonify({'error': 'caen parameter required'}), 400

    conn = get_db()
    cur = conn.cursor()

    conditions = ["c.country = %s"]
    params = [country]

    if '*' in caen:
        conditions.append("c.caen_code LIKE %s")
        params.append(caen.replace('*', '%'))
    else:
        codes = [c.strip() for c in caen.split(',')]
        if len(codes) == 1:
            conditions.append("c.caen_code = %s")
            params.append(codes[0])
        else:
            conditions.append("c.caen_code IN %s")
            params.append(tuple(codes))

    if has_email:
        conditions.append("""EXISTS (
            SELECT 1 FROM contacts WHERE company_id = c.id AND contact_type = 'email'
        )""")

    where = " AND ".join(conditions)

    cur.execute(f"""
        SELECT DISTINCT c.name, c.company_number, c.city, c.caen_code, c.caen_description,
               (SELECT contact_value FROM contacts WHERE company_id = c.id AND contact_type = 'email' LIMIT 1) as email,
               (SELECT contact_value FROM contacts WHERE company_id = c.id AND contact_type = 'phone' LIMIT 1) as phone
        FROM companies c
        WHERE {where}
        LIMIT %s
    """, params + [limit])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['company_name', 'cui', 'city', 'caen_code', 'caen_description', 'email', 'phone'])
    for row in cur:
        writer.writerow(row)

    conn.close()

    filename = f"export_{caen.replace('*', 'x')}_{country}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


if __name__ == '__main__':
    print("Starting B2B Companies API on port 8090...")
    app.run(host='0.0.0.0', port=8090, debug=False)

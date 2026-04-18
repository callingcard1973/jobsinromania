#!/usr/bin/env python3
"""CSV upload blueprint for campaign dashboard. Handles upload, preview, column mapping, import."""
import io
import csv as csvmod
import json
import psycopg2
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify

csv_bp = Blueprint('csv', __name__)
CSV_UPLOAD_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/csv_uploads")
CSV_UPLOAD_DIR.mkdir(exist_ok=True)

DB_CSV = "campaign_csv"


def _decode(raw):
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return None


def _detect_delim(text):
    for d in (",", ";", "\t", "|"):
        reader = csvmod.reader(io.StringIO(text), delimiter=d)
        header = next(reader)
        if len(header) > 1:
            return d, header
    return ",", next(csvmod.reader(io.StringIO(text)))


@csv_bp.route("/api/csv-preview", methods=["POST"])
def csv_preview():
    """Upload CSV, return columns + sample rows for mapping."""
    f = request.files.get("csv_file")
    if not f:
        return jsonify({"error": "No file"}), 400
    raw = f.read()
    text = _decode(raw)
    if text is None:
        return jsonify({"error": "Cannot decode file"}), 400
    delim, header = _detect_delim(text)
    fname = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + f.filename
    (CSV_UPLOAD_DIR / fname).write_bytes(raw)
    # Count + sample
    reader = csvmod.reader(io.StringIO(text), delimiter=delim)
    next(reader)
    sample, count = [], 0
    for row in reader:
        count += 1
        if len(sample) < 5:
            sample.append(row[:len(header)])
    return jsonify({"columns": header, "rows": count, "file": fname,
                     "delimiter": delim, "sample": sample})


@csv_bp.route("/api/csv-import", methods=["POST"])
def csv_import():
    """Import uploaded CSV into PostgreSQL campaign_csv database."""
    data = request.json
    fname = data.get("file", "")
    table_name = data.get("table_name", "").strip().lower()
    table_name = "".join(c if c.isalnum() or c == "_" else "_" for c in table_name)
    col_map = data.get("col_map", {})
    delimiter = data.get("delimiter", ",")
    if not fname or not table_name:
        return jsonify({"error": "Missing file or table name"}), 400
    path = CSV_UPLOAD_DIR / fname
    if not path.exists():
        return jsonify({"error": "File not found"}), 404
    text = _decode(path.read_bytes())
    if text is None:
        return jsonify({"error": "Cannot decode"}), 400
    reader = csvmod.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader)
    rows = list(reader)
    # Map columns
    db_cols = []
    for h in header:
        mapped = col_map.get(h, h)
        c = mapped.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        c = "".join(ch for ch in c if ch.isalnum() or ch == "_") or f"col_{len(db_cols)}"
        db_cols.append(c)
    if "campaign_status" not in db_cols:
        db_cols.append("campaign_status")
    if "last_contacted" not in db_cols:
        db_cols.append("last_contacted")
    # Create table + insert
    conn = psycopg2.connect(host="localhost", dbname=DB_CSV, user="tudor", password="tudor")
    cur = conn.cursor()
    col_defs = ", ".join('"' + c + '" TEXT' for c in db_cols)
    cur.execute('DROP TABLE IF EXISTS "' + table_name + '"')
    cur.execute('CREATE TABLE "' + table_name + '" (id SERIAL PRIMARY KEY, ' + col_defs + ')')
    cur.execute("""CREATE TABLE IF NOT EXISTS send_log (
        id SERIAL PRIMARY KEY, email TEXT, campaign TEXT, sector TEXT,
        sent_at TIMESTAMP DEFAULT NOW(), template TEXT, status TEXT DEFAULT 'sent')""")
    cur.execute("""CREATE TABLE IF NOT EXISTS dnc (
        id SERIAL PRIMARY KEY, email TEXT UNIQUE, reason TEXT,
        added_at TIMESTAMP DEFAULT NOW())""")
    n = len(header)
    insert_cols = db_cols[:n]
    ph = ",".join(["%s"] * n)
    col_list = ",".join('"' + c + '"' for c in insert_cols)
    inserted = 0
    for row in rows:
        if len(row) < n:
            row.extend([""] * (n - len(row)))
        try:
            cur.execute('INSERT INTO "' + table_name + '" (' + col_list + ') VALUES (' + ph + ')', row[:n])
            inserted += 1
        except Exception:
            pass
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True, "table": table_name, "db": DB_CSV,
                     "rows": inserted, "columns": db_cols})

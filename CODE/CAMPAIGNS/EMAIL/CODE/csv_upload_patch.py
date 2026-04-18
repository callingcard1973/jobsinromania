
# ── CSV Upload Support ────────────────────────────────────
import io, csv as csvmod

CSV_UPLOAD_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/csv_uploads")
CSV_UPLOAD_DIR.mkdir(exist_ok=True)

@app.route("/api/csv-preview", methods=["POST"])
def csv_preview():
    """Upload CSV, return column names for mapping."""
    f = request.files.get("csv_file")
    if not f:
        return jsonify({"error": "No file"}), 400
    raw = f.read()
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        return jsonify({"error": "Cannot decode file"}), 400
    # Detect delimiter
    delim = ","
    for d in (",", ";", "\t", "|"):
        reader = csvmod.reader(io.StringIO(text), delimiter=d)
        header = next(reader)
        if len(header) > 1:
            delim = d
            break
    # Save temp file
    fname = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + f.filename
    path = CSV_UPLOAD_DIR / fname
    path.write_bytes(raw)
    # Count rows
    row_count = sum(1 for _ in csvmod.reader(io.StringIO(text), delimiter=delim))
    return jsonify({"columns": header, "rows": row_count - 1, "file": fname, "delimiter": delim})


@app.route("/api/csv-import", methods=["POST"])
def csv_import():
    """Import uploaded CSV into PostgreSQL as a campaign table."""
    data = request.json
    fname = data.get("file", "")
    table_name = data.get("table_name", "").strip().lower().replace("-", "_").replace(" ", "_")
    col_map = data.get("col_map", {})
    delimiter = data.get("delimiter", ",")

    if not fname or not table_name:
        return jsonify({"error": "Missing file or table name"}), 400

    path = CSV_UPLOAD_DIR / fname
    if not path.exists():
        return jsonify({"error": "File not found"}), 404

    raw = path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        return jsonify({"error": "Cannot decode"}), 400

    reader = csvmod.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader)
    rows = list(reader)

    # Map column names: user can rename CSV columns
    db_cols = []
    for h in header:
        mapped = col_map.get(h, h)
        clean_col = mapped.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        clean_col = "".join(c for c in clean_col if c.isalnum() or c == "_")
        if not clean_col:
            clean_col = "col_" + str(len(db_cols))
        db_cols.append(clean_col)

    # Add campaign tracking columns if missing
    if "campaign_status" not in db_cols:
        db_cols.append("campaign_status")
    if "last_contacted" not in db_cols:
        db_cols.append("last_contacted")

    db_name = "campaign_csv"
    conn = psycopg2.connect(host="localhost", dbname=db_name, user="tudor", password="tudor")
    cur = conn.cursor()

    # Create table
    col_defs = ", ".join('"' + c + '" TEXT' for c in db_cols)
    cur.execute('DROP TABLE IF EXISTS "' + table_name + '"')
    cur.execute('CREATE TABLE "' + table_name + '" (id SERIAL PRIMARY KEY, ' + col_defs + ')')

    # Also create send_log and dnc if not exist
    cur.execute("""CREATE TABLE IF NOT EXISTS send_log (
        id SERIAL PRIMARY KEY, email TEXT, campaign TEXT, sector TEXT,
        sent_at TIMESTAMP DEFAULT NOW(), template TEXT, status TEXT DEFAULT 'sent')""")
    cur.execute("""CREATE TABLE IF NOT EXISTS dnc (
        id SERIAL PRIMARY KEY, email TEXT UNIQUE, reason TEXT, added_at TIMESTAMP DEFAULT NOW())""")

    # Insert rows
    n_csv_cols = len(header)
    insert_cols = db_cols[:n_csv_cols]
    placeholders = ",".join(["%s"] * n_csv_cols)
    col_list = ",".join('"' + c + '"' for c in insert_cols)
    inserted = 0
    for row in rows:
        if len(row) < n_csv_cols:
            row.extend([""] * (n_csv_cols - len(row)))
        vals = row[:n_csv_cols]
        try:
            cur.execute('INSERT INTO "' + table_name + '" (' + col_list + ') VALUES (' + placeholders + ')', vals)
            inserted += 1
        except Exception:
            pass

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True, "table": table_name, "db": db_name, "rows": inserted, "columns": db_cols})

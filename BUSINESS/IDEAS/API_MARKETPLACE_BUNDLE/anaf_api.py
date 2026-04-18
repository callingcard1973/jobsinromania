"""ANAF Company Lookup API — FastAPI on raspi, DB on raspibig."""
import os
import psycopg2
import psycopg2.extras
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Romania Company API",
    description="Company lookup by CUI: ANAF + financials + insolvency + risk score",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_HOST = os.getenv("DB_HOST", "192.168.100.21")
DB_NAME = os.getenv("DB_NAME", "interjob_master")
DB_USER = os.getenv("DB_USER", "tudor")
DB_PASS = os.getenv("DB_PASS", "tudor")


def get_conn():
    return psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


def safe_cui(val):
    s = str(val).strip().upper().replace("RO", "").replace(" ", "")
    return int(s) if s.isdigit() else None


def calc_risk(company, insolvency, financials):
    score = 0
    if insolvency:
        score += 50
    if company and company.get("status") in ("INACTIV", "RADIAT"):
        score += 30
    if financials:
        profits = [f.get("profit_net") or 0 for f in financials]
        if profits and profits[0] < 0:
            score += 15
        revs = [f.get("cifra_afaceri") or 0 for f in financials]
        if len(revs) >= 2 and revs[0] < revs[1] * 0.7:
            score += 15
        emps = [f.get("nr_angajati") or 0 for f in financials]
        if len(emps) >= 2 and emps[0] < emps[1]:
            score += 10
    level = "LOW" if score <= 20 else "MEDIUM" if score <= 50 else "HIGH" if score <= 75 else "CRITICAL"
    return {"score": min(score, 100), "level": level}


@app.get("/")
def root():
    return {"status": "ok", "endpoints": ["/company", "/search", "/health"]}


@app.get("/health")
def health():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "db": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "db": str(e)}


@app.get("/company")
def company(cui: str = Query(..., description="Company CUI (tax ID), e.g. 12345678")):
    parsed = safe_cui(cui)
    if not parsed:
        raise HTTPException(400, "Invalid CUI format")
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Company from master_romania_companies
    cur.execute(
        "SELECT * FROM master_romania_companies WHERE cui = %s LIMIT 1",
        (str(parsed),),
    )
    company_row = cur.fetchone()

    # Insolvency
    cur.execute(
        "SELECT * FROM insolvency WHERE cui = %s LIMIT 5",
        (str(parsed),),
    )
    insolvency_rows = cur.fetchall()

    # Financials
    cur.execute(
        "SELECT * FROM bilant_years WHERE cui = %s ORDER BY year DESC LIMIT 3",
        (str(parsed),),
    )
    financial_rows = cur.fetchall()

    conn.close()

    # Live ANAF lookup if not in DB
    anaf_data = None
    try:
        r = requests.post(
            "https://webservicesp.anaf.ro/api/v9/ws/tva",
            json=[{"cui": parsed, "data": "2026-04-14"}],
            timeout=5,
        )
        if r.status_code == 200:
            body = r.json()
            if body.get("found") and len(body["found"]) > 0:
                anaf_data = body["found"][0]
    except Exception:
        pass

    if not company_row and not anaf_data:
        raise HTTPException(404, f"CUI {parsed} not found")

    risk = calc_risk(
        company_row,
        bool(insolvency_rows),
        [dict(f) for f in financial_rows] if financial_rows else [],
    )

    return {
        "cui": parsed,
        "company": dict(company_row) if company_row else None,
        "anaf_live": anaf_data,
        "financials": [dict(f) for f in financial_rows],
        "insolvency": [dict(i) for i in insolvency_rows],
        "risk": risk,
    }


@app.get("/search")
def search(
    name: str = Query(..., min_length=3, description="Company name to search"),
    limit: int = Query(10, ge=1, le=50),
):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT cui, name, city, county, caen_description, email, phone FROM master_romania_companies "
        "WHERE name ILIKE %s LIMIT %s",
        (f"%{name}%", limit),
    )
    rows = cur.fetchall()
    conn.close()
    return {"query": name, "count": len(rows), "results": [dict(r) for r in rows]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

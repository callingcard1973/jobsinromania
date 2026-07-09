"""
bid_api.py — FastAPI on port 5077 for the SEAP Bidding Assistant.
Endpoints:
  POST /analyze   {cpv_code?, keyword?}   -> market analysis JSON
  POST /write     {title, cpv_code, buyer, value_ron, keyword?} -> proposal text
  GET  /health
"""
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

sys.path.insert(0, os.path.dirname(__file__))
from bid_analyzer import analyze_cpv, format_summary
from bid_writer import write_proposal

app = FastAPI(
    title="SEAP Bidding Assistant API",
    description="Genereaza oferte castigatoare pentru licitatii publice din Romania",
    version="1.0.0",
)


# ── Models ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    cpv_code: Optional[str] = None
    keyword: Optional[str] = None


class WriteRequest(BaseModel):
    title: str
    cpv_code: str
    buyer: str
    value_ron: float
    keyword: Optional[str] = None


class AnalyzeResponse(BaseModel):
    cpv_code: Optional[str]
    cpv_name: Optional[str]
    summary_text: str
    stats: dict
    top_winners: list
    top_buyers: list
    yearly_trend: list
    countries: list


class WriteResponse(BaseModel):
    title: str
    cpv_code: str
    buyer: str
    value_ron: float
    proposal: str
    saved_to: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "SEAP Bidding Assistant", "port": 5077}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest):
    if not req.cpv_code and not req.keyword:
        raise HTTPException(status_code=400, detail="Furnizeaza cpv_code sau keyword")

    data = analyze_cpv(cpv_code=req.cpv_code, keyword=req.keyword)

    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])

    return AnalyzeResponse(
        cpv_code=data.get("cpv_code"),
        cpv_name=data.get("cpv_name"),
        summary_text=format_summary(data),
        stats=data.get("stats", {}),
        top_winners=data.get("top_winners", []),
        top_buyers=data.get("top_buyers", []),
        yearly_trend=data.get("yearly_trend", []),
        countries=data.get("countries", []),
    )


@app.post("/write", response_model=WriteResponse)
def write_endpoint(req: WriteRequest):
    if req.value_ron <= 0:
        raise HTTPException(status_code=400, detail="value_ron trebuie sa fie pozitiv")
    if not req.cpv_code:
        raise HTTPException(status_code=400, detail="cpv_code este obligatoriu")

    proposal_text = write_proposal(
        title=req.title,
        cpv_code=req.cpv_code,
        buyer=req.buyer,
        value_ron=req.value_ron,
        keyword=req.keyword,
    )

    # Determine saved filepath
    from datetime import date
    proposals_dir = os.path.join(os.path.dirname(__file__), "proposals")
    safe_cpv = req.cpv_code.replace("/", "-")
    filename = f"{safe_cpv}_{date.today().isoformat()}.txt"
    filepath = os.path.join(proposals_dir, filename)

    return WriteResponse(
        title=req.title,
        cpv_code=req.cpv_code,
        buyer=req.buyer,
        value_ron=req.value_ron,
        proposal=proposal_text,
        saved_to=filepath,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("bid_api:app", host="0.0.0.0", port=5077, reload=False)

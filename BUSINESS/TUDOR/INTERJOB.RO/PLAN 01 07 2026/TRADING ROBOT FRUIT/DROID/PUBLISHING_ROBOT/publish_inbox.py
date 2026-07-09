#!/usr/bin/env python3
"""FastAPI inbox — primeste continut de la AI si il pune in queue.

POST /inbox  {title, body, channels}

Ruleaza: uvicorn publish_inbox:app --host 0.0.0.0 --port 8777
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from publish_db import init_db, add_item

try:
    from fastapi import FastAPI, Request
    from pydantic import BaseModel
except ImportError:
    print("Instaleaza: pip install fastapi uvicorn pydantic")
    sys.exit(1)

app = FastAPI(title="Publishing Robot Inbox")


class InboxItem(BaseModel):
    title: str
    body: str
    channels: list[str] = ["tg", "wp", "fb"]


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/inbox")
async def inbox(item: InboxItem, request: Request):
    item_id = add_item(item.title, item.body, item.channels)
    return {
        "status": "queued",
        "id": item_id,
        "title": item.title,
        "channels": item.channels,
        "message": "Continut primit. Se trimite la aprobare in Telegram.",
    }


@app.get("/queue")
def queue_status():
    from publish_db import count_status
    return {
        "pending": count_status("pending"),
        "approved": count_status("approved"),
        "published": count_status("published"),
        "rejected": count_status("rejected"),
        "failed": count_status("failed"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8777)

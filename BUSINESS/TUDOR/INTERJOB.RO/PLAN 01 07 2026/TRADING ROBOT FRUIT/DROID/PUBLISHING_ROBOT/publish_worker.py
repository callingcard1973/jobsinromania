#!/usr/bin/env python3
"""Worker — preia itemi approved/scheduled din DB si publica pe canalele selectate.

Moduri:
  python publish_worker.py           # daemon: loop la fiecare 5 sec
  python publish_worker.py --once    # run o singura data (pentru cron)
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from publish_db import (
    init_db,
    get_approved,
    get_ready_scheduled,
    get_item,
    update_status,
    set_urls,
    add_log,
)
from connectors import REGISTRY

LOG = Path(__file__).parent / "worker.log"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def publish_item(item):
    item_id = item["id"]
    title = item["title"]
    body = item["body"]
    channels = json.loads(item["channels"])
    log(f"PUBLIC {item_id} ({title[:50]}) pe {channels}")

    urls = {}
    all_ok = True

    for ch in channels:
        connector = REGISTRY.get(ch)
        if not connector:
            log(f"  [{ch}] NU EXISTA connector")
            add_log(item_id, ch, "error", error="connector inexistent")
            all_ok = False
            continue

        try:
            ok, result = connector(title, body)
            if ok:
                urls[ch] = result
                add_log(item_id, ch, "ok", url=result)
                log(f"  [{ch}] OK -> {result}")
            else:
                urls[ch] = f"FAIL: {result[:100]}"
                add_log(item_id, ch, "fail", error=result)
                log(f"  [{ch}] FAIL -> {result[:100]}")
                all_ok = False
        except Exception as e:
            err = str(e)[:200]
            urls[ch] = f"FAIL: {err}"
            add_log(item_id, ch, "error", error=err)
            log(f"  [{ch}] EXCEPTION -> {err}")
            all_ok = False

    set_urls(item_id, urls)
    if all_ok:
        update_status(item_id, "published")
        log(f"DONE {item_id} -> published")
    else:
        update_status(item_id, "failed", error=json.dumps(urls))
        log(f"DONE {item_id} -> failed (partial: {urls})")


def process_queue():
    items = get_approved()
    for item in items:
        publish_item(item)

    ready = get_ready_scheduled()
    for item in ready:
        update_status(item["id"], "approved")
        publish_item(item)

    return len(items) + len(ready)


def daemon_loop():
    init_db()
    log("Worker daemon pornit")
    while True:
        try:
            n = process_queue()
            if n:
                log(f"Procesate {n} itemi")
            time.sleep(5)
        except KeyboardInterrupt:
            log("Oprit manual")
            break
        except Exception as e:
            log(f"Eroare: {e}")
            time.sleep(10)
    log("Worker oprit")


def main():
    init_db()
    if "--once" in sys.argv:
        n = process_queue()
        log(f"Run one-shot: {n} itemi procesati")
    else:
        daemon_loop()


if __name__ == "__main__":
    main()

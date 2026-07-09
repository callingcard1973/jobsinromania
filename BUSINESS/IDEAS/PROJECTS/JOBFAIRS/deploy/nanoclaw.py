#!/usr/bin/env python3
"""
NANOCLAW — Operations Agent with LLM diagnosis.
Monitors scrapers, TED data, disk, missed runs.
Uses Ollama (qwen2.5:1.5b / qwen3-4b) for error diagnosis and morning digest.
"""
import os
import sys
import time
import json
import signal
import logging
import requests
from datetime import datetime
from dataclasses import asdict
from nanoclaw_core import (
    GOVERNOR_DIR, NANOCLAW_STATE, LOG_DIR, LOCK_DIR, SCRAPER_LOG_DIR,
    HEARTBEAT_DIR, SCRAPER_SCHEDULE, OLLAMA_URL, OLLAMA_FAST_MODEL,
    OLLAMA_SMART_MODEL, LockManager, HeartbeatMonitor
)
from nanoclaw_monitors import (
    orchestrate_scrapers, monitor_running_tasks, check_missed_scrapers,
    enforce_campaign_priority, watch_log_completion, monitor_ted_data,
    check_disk, get_running_scrapers, is_campaign_window, is_system_healthy
)


class NanoClaw:
    def __init__(self):
        self.running = True
        self.logger = self._setup_logging()
        self.locks = LockManager(LOCK_DIR)
        self.heartbeats = HeartbeatMonitor(HEARTBEAT_DIR)
        self.tasks = {}
        self.watched_logs = set()
        self._missed_alerted = set()
        self._disk_alerted = False
        self._digest_sent_today = None
        self._ensure_dirs()
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _setup_logging(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("nanoclaw")
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(LOG_DIR / "nanoclaw.log")
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('[NANOCLAW] %(message)s'))
        logger.addHandler(ch)
        return logger

    def _ensure_dirs(self):
        GOVERNOR_DIR.mkdir(parents=True, exist_ok=True)
        SCRAPER_LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _handle_signal(self, signum, frame):
        self.logger.info(f"Signal {signum}, shutting down...")
        self.running = False

    def send_telegram(self, message, level="info"):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not token or not chat_id:
            return False
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🔴", "critical": "🚨"}.get(level, "ℹ️")
        try:
            resp = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": f"{emoji} *NANOCLAW*\n{message}", "parse_mode": "Markdown"},
                timeout=10)
            if resp.status_code == 200:
                return True
            self.logger.error(f"Telegram HTTP {resp.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"Telegram failed: {e}")
            return False

    def diagnose_error(self, log_tail):
        try:
            lines = log_tail.strip().split('\n')[-50:]
            prompt = "Analyze this scraper log. In 2 sentences: what went wrong and likely fix.\n\n" + "\n".join(lines)
            r = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_FAST_MODEL, "prompt": prompt, "stream": False
            }, timeout=15)
            if r.status_code == 200:
                return r.json().get("response", "")[:300]
        except Exception:
            pass
        return "Check logs manually."

    def morning_digest(self):
        now = datetime.now()
        if now.hour != 7 or self._digest_sent_today == now.date():
            return
        self._digest_sent_today = now.date()
        ted = monitor_ted_data()
        running = get_running_scrapers(self.locks)
        failed = [n for n, t in self.tasks.items() if t.status == "failed"]
        data = f"Scrapers running: {running or 'none'}. Failed: {failed or 'none'}. TED: {ted['total_winners']:,} winners, {len(ted['files'])} files. Issues: {ted['issues'] or 'none'}."
        try:
            r = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_SMART_MODEL,
                "prompt": f"Summarize this ops data in 3 bullet points for a morning briefing:\n{data}",
                "stream": False
            }, timeout=30)
            if r.status_code == 200:
                summary = r.json().get("response", data)[:500]
                self.send_telegram(f"📋 *Morning Digest*\n{summary}")
                return
        except Exception:
            pass
        self.send_telegram(f"📋 *Morning Digest*\n{data}")

    def write_state(self):
        ted = monitor_ted_data()
        state = {
            "timestamp": datetime.now().isoformat(),
            "running_scrapers": get_running_scrapers(self.locks),
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "campaign_window": is_campaign_window(),
            "system_healthy": is_system_healthy(),
            "ted_data": {"healthy": ted["healthy"], "total_winners": ted["total_winners"],
                         "files": len(ted["files"]), "issues": ted["issues"]},
        }
        tmp = NANOCLAW_STATE.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(NANOCLAW_STATE)

    def run(self, interval=60):
        self.logger.info("=" * 40)
        self.logger.info(f"NANOCLAW STARTING — {len(SCRAPER_SCHEDULE)} scrapers, Ollama LLM")
        self.logger.info("=" * 40)
        last_cleanup = datetime.now()
        while self.running:
            try:
                self.heartbeats.beat("nanoclaw")
                orchestrate_scrapers(self.locks, self.logger)
                monitor_running_tasks(self.locks, self.tasks, self.logger,
                                      self.diagnose_error, self.send_telegram)
                check_missed_scrapers(self.locks, self.tasks, self.logger,
                                      self.send_telegram, self._missed_alerted)
                enforce_campaign_priority(self.locks, self.logger)
                watch_log_completion(self.watched_logs)
                _, self._disk_alerted, disk_msg = check_disk(self._disk_alerted)
                if disk_msg:
                    self.send_telegram(disk_msg, "warning")
                self.morning_digest()
                if (datetime.now() - last_cleanup).seconds > 600:
                    self.locks.cleanup_stale()
                    last_cleanup = datetime.now()
                    if datetime.now().hour == 0:
                        self._missed_alerted.clear()
                if datetime.now().minute % 30 == 0 and datetime.now().second < interval:
                    ted = monitor_ted_data()
                    if not ted["healthy"] and any("empty" in i for i in ted["issues"]):
                        self.send_telegram(f"TED alert\n" + "\n".join(ted["issues"]), "warning")
                self.write_state()
                if datetime.now().minute % 5 == 0 and datetime.now().second < interval:
                    running = get_running_scrapers(self.locks)
                    ted = monitor_ted_data()
                    self.logger.info(f"Status: {len(running)} scrapers: {running or 'none'} | TED: {ted['total_winners']:,}")
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
            time.sleep(interval)
        self.logger.info("NanoClaw shutdown complete")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NanoClaw Operations Agent")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--running", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    nano = NanoClaw()
    if args.status:
        from nanoclaw_monitors import check_governor
        state = check_governor()
        print(f"Healthy: {state.get('health', {}).get('all_healthy', '?')}")
        print(f"Campaign window: {is_campaign_window()}")
        print(f"Running scrapers: {get_running_scrapers(nano.locks)}")
        ted = monitor_ted_data()
        print(f"TED: {ted['total_winners']:,} winners, {len(ted['files'])} files")
        if ted['issues']:
            print(f"Issues: {ted['issues']}")
        sys.exit(0)
    if args.running:
        for name in get_running_scrapers(nano.locks):
            print(f"{name}: PID {nano.locks.get_lock_holder(f'scraper_{name}')}")
        sys.exit(0)
    nano.run(interval=args.interval)


if __name__ == "__main__":
    main()

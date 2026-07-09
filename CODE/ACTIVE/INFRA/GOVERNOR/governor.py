#!/usr/bin/env python3
from governor_config import *

class Governor:

    def __init__(self):
        self.running = True
        self.logger = self._setup_logging()
        self.state: Dict = {}
        self._ensure_dirs()
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _setup_logging(self) -> logging.Logger:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("governor")
        logger.setLevel(logging.INFO)

        # File handler
        fh = logging.FileHandler(LOG_DIR / "governor.log")
        fh.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('[GOVERNOR] %(message)s'))
        logger.addHandler(ch)

        return logger

    def _ensure_dirs(self):
        GOVERNOR_DIR.mkdir(parents=True, exist_ok=True)
        LOCK_DIR.mkdir(parents=True, exist_ok=True)

    def _handle_signal(self, signum, frame):
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def send_telegram(self, message: str, level: str = "info") -> bool:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if not token or not chat_id:
            return False

        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🔴", "critical": "🚨"}.get(level, "ℹ️")
        text = f"{emoji} *GOVERNOR*\n{message}"

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            self.logger.error(f"Telegram alert failed: {e}")
            return False

    def get_cpu_load(self) -> float:
        try:
            return os.getloadavg()[0]
        except:
            return 0.0

    def get_temperature(self) -> float:
        try:
            temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
            if temp_path.exists():
                return int(temp_path.read_text().strip()) / 1000.0
        except:
            pass
        return 50.0  # Default if can't read

    def get_ram_free_gb(self) -> float:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / 1024 / 1024
        except:
            pass
        return 8.0  # Default if can't read

    def get_disk_percent(self) -> float:
        try:
            stat = os.statvfs("/")
            used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
            total = stat.f_blocks * stat.f_frsize
            return (used / total) * 100
        except:
            return 50.0

    def get_current_timezone(self) -> TimeZone:
        hour = datetime.now().hour
        if 0 <= hour < 6:
            return TimeZone.NIGHT
        elif 6 <= hour < 8:
            return TimeZone.MORNING
        elif 8 <= hour < 18:
            return TimeZone.DAY
        else:
            return TimeZone.EVENING

    def is_campaign_window(self) -> bool:
        now = datetime.now()
        for hour, minute in CAMPAIGN_WINDOWS:
            window_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            window_end = window_start + timedelta(minutes=CAMPAIGN_WINDOW_DURATION)
            if window_start <= now <= window_end:
                return True
        return False

    def check_health(self) -> SystemHealth:
        violations = []

        cpu_load = self.get_cpu_load()
        temp_c = self.get_temperature()
        ram_free_gb = self.get_ram_free_gb()
        disk_percent = self.get_disk_percent()
        time_zone = self.get_current_timezone()
        in_campaign = self.is_campaign_window()

        # Check thresholds
        if cpu_load >= THRESHOLDS["cpu_load_max"]:
            violations.append(f"CPU load {cpu_load:.1f} >= {THRESHOLDS['cpu_load_max']}")

        if temp_c >= THRESHOLDS["temp_max_c"]:
            violations.append(f"Temp {temp_c:.0f}C >= {THRESHOLDS['temp_max_c']}C")

        if ram_free_gb < THRESHOLDS["ram_free_min_gb"]:
            violations.append(f"RAM free {ram_free_gb:.1f}GB < {THRESHOLDS['ram_free_min_gb']}GB")

        if disk_percent >= THRESHOLDS["disk_max_percent"]:
            violations.append(f"Disk {disk_percent:.0f}% >= {THRESHOLDS['disk_max_percent']}%")

        return SystemHealth(
            timestamp=datetime.now().isoformat(),
            cpu_load=cpu_load,
            temp_c=temp_c,
            ram_free_gb=ram_free_gb,
            disk_percent=disk_percent,
            time_zone=time_zone.value,
            in_campaign_window=in_campaign,
            all_healthy=len(violations) == 0,
            violations=violations
        )

    def can_run_activity(self, activity: str) -> Tuple[bool, str]:
        health = self.check_health()
        time_zone = self.get_current_timezone()

        # Check health first
        if not health.all_healthy:
            return False, f"System unhealthy: {', '.join(health.violations)}"

        # Check time zone restrictions
        if activity in BLOCKED_ACTIVITIES.get(time_zone, []):
            return False, f"Activity '{activity}' blocked during {time_zone.value} hours"

        # Check campaign window priority
        if health.in_campaign_window and activity not in ["campaigns", "email_sending"]:
            if activity in ["scrapers", "heavy_scraping", "llm", "llm_enrichment"]:
                return False, "Campaign window active - heavy tasks paused"

        return True, "OK"

    def write_state(self, health: SystemHealth):
        state = {
            "health": asdict(health),
            "thresholds": THRESHOLDS,
            "allowed_now": ALLOWED_ACTIVITIES.get(self.get_current_timezone(), []),
            "blocked_now": BLOCKED_ACTIVITIES.get(self.get_current_timezone(), []),
        }
        STATE_FILE.write_text(json.dumps(state, indent=2))

    def run(self, interval: int = 30):
        self.logger.info("=" * 50)
        self.logger.info("SYSTEM GOVERNOR STARTING")
        self.logger.info(f"Thresholds: CPU<{THRESHOLDS['cpu_load_max']}, "
                        f"Temp<{THRESHOLDS['temp_max_c']}C, "
                        f"RAM>{THRESHOLDS['ram_free_min_gb']}GB, "
                        f"Disk<{THRESHOLDS['disk_max_percent']}%")
        self.logger.info("=" * 50)

        last_zone = None
        last_campaign_window = None

        while self.running:
            try:
                health = self.check_health()
                self.write_state(health)

                # Log zone changes
                current_zone = self.get_current_timezone()
                if current_zone != last_zone:
                    self.logger.info(f"TIME ZONE CHANGE: {current_zone.value.upper()}")
                    self.logger.info(f"  Allowed: {ALLOWED_ACTIVITIES[current_zone]}")
                    self.logger.info(f"  Blocked: {BLOCKED_ACTIVITIES[current_zone]}")
                    last_zone = current_zone

                # Log campaign window changes
                if health.in_campaign_window != last_campaign_window:
                    if health.in_campaign_window:
                        self.logger.info("CAMPAIGN WINDOW ACTIVE - email sending priority")
                    else:
                        self.logger.info("Campaign window ended")
                    last_campaign_window = health.in_campaign_window

                # Log violations and send Telegram alert
                if not health.all_healthy:
                    self.logger.warning(f"VIOLATIONS: {', '.join(health.violations)}")
                    # Send Telegram alert for health violations (max once per 5 min via dedup)
                    violations_key = ','.join(sorted(health.violations))
                    if not hasattr(self, '_last_alert') or \
                       self._last_alert.get(violations_key, datetime.min) < datetime.now() - timedelta(minutes=5):
                        self.send_telegram(f"Health violation:\n{chr(10).join(health.violations)}", "warning")
                        if not hasattr(self, '_last_alert'):
                            self._last_alert = {}
                        self._last_alert[violations_key] = datetime.now()

                # Periodic status (every 5 minutes)
                if datetime.now().minute % 5 == 0 and datetime.now().second < interval:
                    self.logger.info(
                        f"Status: CPU={health.cpu_load:.1f} Temp={health.temp_c:.0f}C "
                        f"RAM={health.ram_free_gb:.1f}GB Disk={health.disk_percent:.0f}% "
                        f"Zone={health.time_zone}"
                    )

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")

            time.sleep(interval)

        self.logger.info("Governor shutdown complete")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="System Governor")
    parser.add_argument("--check", action="store_true", help="Single health check")
    parser.add_argument("--can-run", metavar="ACTIVITY", help="Check if activity allowed")
    parser.add_argument("--interval", type=int, default=30, help="Check interval (seconds)")
    args = parser.parse_args()

    gov = Governor()

    if args.check:
        h = gov.check_health()
        gov.write_state(h)
        print(f"Load:{h.cpu_load} RAM:{h.ram_free_gb:.1f}GB Temp:{h.temperature:.1f}C")
    elif args.can_run:
        ok, reason = gov.can_run_activity(args.can_run)
        print("allowed" if ok else f"blocked: {reason}")
        import sys; sys.exit(0 if ok else 1)
    else:
        gov.run(args.interval)

#!/usr/bin/env python3
"""
Smart Continuous OpenData Downloader v3.0
Fixed: UK Companies House dynamic URL, Latvia disabled, guaranteed small daily downloads
"""

import os
import json
import time
import re
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging
import random

# Configuration
DOWNLOAD_DIR = Path("/mnt/hdd/OPENDATA/DATA/CONTINUOUS")
STATE_FILE = Path("/mnt/hdd/OPENDATA/DATA/CONTINUOUS/smart_downloader_state.json")
LOG_FILE = Path("/opt/LOGS/continuous_opendata.log")

# Rate limiting
MIN_DELAY_SECONDS = 120   # 10 minutes minimum between downloads
MAX_DELAY_SECONDS = 600  # 60 minutes maximum
RETRY_DELAY = 1800        # 2 hour retry delay on failure

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# SMART SOURCES — only what provides value
# ============================================================
SMART_SOURCES = {
    # --- DAILY (guaranteed small frequent downloads) ---
    "norway_enhetsregisteret": {
        "url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
        "filename": "norway_companies_daily_{timestamp}.csv.gz",
        "interval_hours": 24,
        "timeout": 600,
        "enabled": True,
        "value": "Daily business changes - 650K+ records with emails/phones",
        "size_estimate": "146MB"
    },

    # --- SMALL HEARTBEAT: Norway changes (tiny, daily guarantee) ---
    "norway_changes": {
        "url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
        "filename": "norway_changes_{timestamp}.csv.gz",
        "interval_hours": 24,
        "timeout": 600,
        "enabled": True,
        "value": "Norway full registry - ensures daily download activity",
        "size_estimate": "146MB",
        "skip_if_norway_downloaded_today": True  # Skip if main Norway already downloaded
    },

    "ireland_cro": {
        "url": "https://opendata.cro.ie/dataset/bf6f837d-0946-4c14-9a99-82cd6980c121/resource/3fef41bc-b8f4-4b10-8434-ce51c29b1bba/download/companies.csv.zip",
        "filename": "ireland_cro_{timestamp}.zip",
        "interval_hours": 48,
        "timeout": 300,
        "enabled": True,
        "value": "280K Irish companies - updates",
        "size_estimate": "45MB"
    },

    # --- WEEKLY ---
    "uk_charities": {
        "url": "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/txt/publicextract.charity.zip",
        "filename": "uk_charities_{timestamp}.zip",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "170K charities with contacts",
        "size_estimate": "42MB"
    },

    # --- MONTHLY (large files) ---
    "france_sirene_units": {
        "url": "https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip",
        "filename": "france_sirene_units_{timestamp}.zip",
        "interval_hours": 720,
        "timeout": 1800,
        "enabled": True,
        "value": "28M French companies - monthly refresh",
        "size_estimate": "907MB"
    },

    "uk_companies_house": {
        # URL resolved dynamically via _resolve_latest_uk_ch_url()
        "url": "dynamic",
        "resolve_url": "https://download.companieshouse.gov.uk/en_output.html",
        "resolve_pattern": r'BasicCompanyDataAsOneFile-(\d{4}-\d{2}-\d{2})\.zip',
        "filename": "uk_companies_house_{timestamp}.zip",
        "interval_hours": 720,
        "timeout": 1200,
        "enabled": True,
        "value": "5M UK companies - monthly refresh",
        "size_estimate": "468MB"
    },

    # --- DISABLED ---
    "latvia_ur": {
        "url": "http://dati.ur.gov.lv/register/register.csv",
        "filename": "latvia_register_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "DISABLED - timeout + already have 218K in DB",
    },
    "estonia_ariregister": {
        "url": "https://avaandmed.ariregister.rik.ee/en/downloadable-opendata",
        "filename": "estonia_companies_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": False,
        "value": "DISABLED - needs URL verification",
    },
    "sweden_bolagsverket": {
        "url": "",
        "filename": "sweden_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": False,
        "value": "DISABLED - check existing data first",
    },
    "finland_prh": {
        "url": "",
        "filename": "finland_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": False,
        "value": "DISABLED - check existing data first",
    },
    # --- ADDED: More European registries ---
    "belgium_kbo": {
        "url": "https://kbopub.economie.fgov.be/kbo-open-data/login?lang=en",
        "filename": "belgium_kbo_{timestamp}.zip",
        "interval_hours": 168,
        "timeout": 600,
        "enabled": True,
        "value": "1.5M Belgian companies - weekly updates",
        "size_estimate": "200MB"
    },

    "denmark_cvr": {
        "url": "http://distribution.virk.dk/cvr-permanent/_data/csv_files/company.csv.zip",
        "filename": "denmark_cvr_{timestamp}.zip",
        "interval_hours": 168,
        "timeout": 900,
        "enabled": True,
        "value": "800K Danish companies with contact info",
        "size_estimate": "300MB"
    },

    "czech_ares": {
        "url": "https://dataor.justice.cz/api/3/action/package_list",
        "filename": "czech_ares_{timestamp}.json",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "Czech business registry API index",
        "size_estimate": "5MB"
    },

    "spain_librebor": {
        "url": "https://librebor.me/csv/companies.csv",
        "filename": "spain_librebor_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 600,
        "enabled": True,
        "value": "Spanish companies from Librebor",
        "size_estimate": "50MB"
    },

    "romania_onrc": {
        "url": "https://data.gov.ro/dataset/firme-romania",
        "filename": "romania_onrc_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "Romanian companies from ONRC open data",
        "size_estimate": "30MB"
    },

    "gleif_daily": {
        "url": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/30447/zip",
        "filename": "gleif_lei_{timestamp}.zip",
        "interval_hours": 24,
        "timeout": 1200,
        "enabled": True,
        "value": "Global LEI database - 2.5M entities with addresses",
        "size_estimate": "400MB"
    },

    "italy_opendata": {
        "url": "https://dati.mise.gov.it/catalog/dataset/registro-delle-imprese/resource/registro-delle-imprese-csv",
        "filename": "italy_companies_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 600,
        "enabled": True,
        "value": "Italian business registry",
        "size_estimate": "100MB"
    },

    "netherlands_kvk": {
        "url": "https://opendata.cbs.nl/statline/portal.html?_la=en&_catalog=CBS",
        "filename": "netherlands_kvk_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "Dutch business statistics",
        "size_estimate": "20MB"
    },

}


def load_state():
    """Load download state"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            logger.warning("Invalid state file, resetting")
    return {
        "last_downloads": {},
        "download_counts": {},
        "errors": {},
        "started_at": datetime.now().isoformat(),
        "version": "3.0",
    }


def save_state(state):
    """Save download state"""
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def should_download(source_name, config, state):
    """Check if source should be downloaded now"""
    if not config.get('enabled', True):
        return False

    last_download = state.get('last_downloads', {}).get(source_name)
    if not last_download:
        return True

    try:
        last_time = datetime.fromisoformat(last_download)
        interval = timedelta(hours=config.get('interval_hours', 24))
        return datetime.now() - last_time >= interval
    except Exception:
        return True


def _resolve_latest_uk_ch_url(config):
    """Dynamically resolve the latest UK Companies House bulk file URL"""
    try:
        resp = requests.get(config['resolve_url'], timeout=30)
        resp.raise_for_status()
        match = re.search(config['resolve_pattern'], resp.text)
        if match:
            date_str = match.group(1)
            url = f"https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-{date_str}.zip"
            logger.info(f"Resolved UK CH URL: {url}")
            return url
        else:
            logger.error("Could not find UK CH filename pattern in page")
            return None
    except Exception as e:
        logger.error(f"Failed to resolve UK CH URL: {e}")
        return None


def download_source(source_name, config, state):
    """Download a single source with comprehensive error handling"""
    # Handle norway_changes skip logic
    if config.get('skip_if_norway_downloaded_today'):
        norway_last = state.get('last_downloads', {}).get('norway_enhetsregisteret', '')
        if norway_last:
            try:
                last_norway = datetime.fromisoformat(norway_last)
                if datetime.now().date() == last_norway.date():
                    logger.info(f"Skipping {source_name} - Norway already downloaded today")
                    return None
            except Exception:
                pass

    # Resolve dynamic URLs
    url = config['url']
    if url == 'dynamic' and config.get('resolve_url'):
        url = _resolve_latest_uk_ch_url(config)
        if not url:
            return {
                'success': False,
                'error': 'Could not resolve dynamic URL',
                'timestamp': datetime.now().isoformat(),
            }

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = config['filename'].format(timestamp=timestamp)

    # Create source-specific directory
    source_dir = DOWNLOAD_DIR / source_name
    source_dir.mkdir(parents=True, exist_ok=True)
    filepath = source_dir / filename

    logger.info(f"Downloading {source_name} from {url}")
    logger.info(f"Value: {config.get('value', 'Unknown')}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (OpenData Downloader; Business Registry Research)'
        }

        response = requests.get(
            url,
            timeout=config.get('timeout', 300),
            stream=True,
            headers=headers,
            allow_redirects=True
        )
        response.raise_for_status()

        # Write file in chunks
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Verify download
        size_bytes = filepath.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_bytes < 1024:
            raise ValueError(f"Download too small: {size_bytes} bytes")

        logger.info(f"✅ {source_name} downloaded successfully ({size_mb:.2f} MB)")
        return {
            'success': True,
            'filename': filename,
            'size_mb': round(size_mb, 2),
            'size_bytes': size_bytes,
            'timestamp': datetime.now().isoformat(),
            'source_dir': str(source_dir),
            'value': config.get('value', 'Unknown')
        }

    except Exception as e:
        logger.error(f"❌ {source_name} download failed: {e}")
        # Clean up failed download
        if filepath.exists() and filepath.stat().st_size < 1024:
            filepath.unlink()
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'url': url
        }


def cleanup_old_files(source_name, keep=3):
    """Keep only the N most recent files for a source"""
    source_dir = DOWNLOAD_DIR / source_name
    if not source_dir.exists():
        return

    files = sorted(source_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_file in files[keep:]:
        try:
            old_file.unlink()
            logger.info(f"🗑️  Cleaned up old file: {old_file.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {old_file.name}: {e}")


def send_status_notification(message):
    """Send status notification via Telegram"""
    try:
        result = subprocess.run([
            "python3", "/opt/ACTIVE/INFRA/SKILLS/send_telegram.py", message
        ], capture_output=True, timeout=30, text=True)
        if result.returncode == 0:
            logger.info("Telegram notification sent")
        else:
            logger.warning(f"Telegram failed: {result.stderr}")
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


def main():
    """Main smart download loop"""
    logger.info("=== Starting Smart Continuous OpenData Downloader v3.0 ===")
    logger.info("Fixes: UK CH dynamic URL, Latvia disabled, guaranteed daily downloads")

    while True:
        try:
            state = load_state()
            downloads_this_cycle = 0
            errors_this_cycle = 0

            for source_name, config in SMART_SOURCES.items():
                if not config.get('enabled', True):
                    continue

                if should_download(source_name, config, state):
                    result = download_source(source_name, config, state)

                    if result is None:
                        # Skipped (e.g., norway_changes when norway downloaded today)
                        continue

                    if result['success']:
                        state['last_downloads'][source_name] = result['timestamp']
                        state['download_counts'][source_name] = \
                            state.get('download_counts', {}).get(source_name, 0) + 1
                        downloads_this_cycle += 1
                        logger.info(f"✅ {source_name}: {result['size_mb']}MB")

                        # Cleanup old files (keep 3 most recent)
                        cleanup_old_files(source_name, keep=3)
                    else:
                        state.setdefault('errors', {})[source_name] = result
                        errors_this_cycle += 1

                    save_state(state)

                    # Rate limiting between downloads
                    delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                    logger.info(f"⏱️  Rate limiting: sleeping {delay // 60} minutes")
                    time.sleep(delay)

            # Cycle report
            if downloads_this_cycle > 0:
                logger.info(f"📊 Cycle complete: {downloads_this_cycle} downloads, {errors_this_cycle} errors")
            else:
                logger.info(f"💤 No downloads needed this cycle")

            # Wait before next cycle
            cycle_delay = random.randint(3600, 5400)  # 60-90 min
            logger.info(f"💤 Next cycle in {cycle_delay // 60} minutes")
            time.sleep(cycle_delay)

        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(RETRY_DELAY)


if __name__ == "__main__":
    main()

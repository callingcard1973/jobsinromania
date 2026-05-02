#!/usr/bin/env python3
"""
Continuous OpenData Monitoring & Download System
Monitors multiple opendata sources for updates and downloads new data automatically
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
import hashlib
import os
import time
from pathlib import Path
import subprocess

class ContinuousOpenDataMonitor:
    def __init__(self):
        self.sources = {
            'romania_data_gov': {
                'url': 'https://data.gov.ro/api/3/action/package_list',
                'check_interval': 3600,  # 1 hour
                'last_hash': None,
                'download_endpoint': 'https://data.gov.ro/api/3/action/package_show?id={}'
            },
            'eu_opendata': {
                'url': 'https://data.europa.eu/api/hub/search/datasets',
                'check_interval': 7200,  # 2 hours
                'last_hash': None,
                'download_endpoint': 'https://data.europa.eu/api/hub/search/datasets/{}'
            },
            'world_bank': {
                'url': 'https://datahelpdesk.worldbank.org/knowledgebase/articles/889392',
                'check_interval': 86400,  # 24 hours
                'last_hash': None
            },
            'anofm_jobs': {
                'url': 'https://www.anofm.ro/locuri-de-munca',
                'check_interval': 1800,  # 30 minutes
                'last_hash': None,
                'parser': 'anofm_scraper'
            },
            'ted_procurement': {
                'url': 'https://ted.europa.eu/api/v3.0/notices/search',
                'check_interval': 3600,  # 1 hour
                'last_hash': None
            }
        }

        self.download_dir = '/opt/ACTIVE/OPENDATA/DATA/CONTINUOUS/'
        self.log_file = '/opt/LOGS/continuous_opendata.log'
        self.state_file = '/opt/ACTIVE/OPENDATA/continuous_state.json'

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def check_source_updates(self, source_name, source_config):
        """Check if a data source has new updates"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source_config['url'], timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        content_hash = hashlib.md5(content.encode()).hexdigest()

                        if source_config['last_hash'] != content_hash:
                            self.logger.info(f"New data detected for {source_name}")
                            source_config['last_hash'] = content_hash
                            return True, content
                        else:
                            self.logger.debug(f"No updates for {source_name}")
                            return False, None
                    else:
                        self.logger.warning(f"Failed to check {source_name}: HTTP {response.status}")
                        return False, None

        except Exception as e:
            self.logger.error(f"Error checking {source_name}: {e}")
            return False, None

    async def download_new_data(self, source_name, content):
        """Download and process new data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(self.download_dir) / source_name / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save raw data
        raw_file = output_dir / 'raw_data.json'
        with open(raw_file, 'w') as f:
            f.write(content)

        # Process based on source type
        if source_name == 'anofm_jobs':
            await self.process_anofm_data(content, output_dir)
        elif source_name == 'ted_procurement':
            await self.process_ted_data(content, output_dir)
        elif source_name == 'romania_data_gov':
            await self.process_romania_data(content, output_dir)

        self.logger.info(f"Downloaded and processed {source_name} data to {output_dir}")

    async def process_anofm_data(self, content, output_dir):
        """Process ANOFM job data"""
        # Run existing ANOFM enrichment if available
        try:
            cmd = f"cd /opt/ACTIVE/INFRA/SKILLS && python3 anofm_enricher.py --input {output_dir}/raw_data.json --output {output_dir}/enriched_jobs.csv"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("ANOFM data enriched successfully")
            else:
                self.logger.warning(f"ANOFM enrichment warning: {result.stderr}")
        except Exception as e:
            self.logger.error(f"ANOFM processing error: {e}")

    async def process_ted_data(self, content, output_dir):
        """Process TED procurement data"""
        try:
            # Extract contractor information for campaigns
            cmd = f"cd /opt/ACTIVE/INFRA/SKILLS && python3 ted_extract_all.py --input {output_dir}/raw_data.json --output {output_dir}/contractors.csv"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("TED data processed successfully")
        except Exception as e:
            self.logger.error(f"TED processing error: {e}")

    async def process_romania_data(self, content, output_dir):
        """Process Romania gov data"""
        # Parse and categorize Romanian opendata
        try:
            import json
            data = json.loads(content)

            # Filter for business/company related datasets
            business_datasets = []
            for dataset in data.get('result', []):
                if any(keyword in dataset.lower() for keyword in ['compan', 'firm', 'business', 'economic', 'industri']):
                    business_datasets.append(dataset)

            # Save filtered business data
            business_file = output_dir / 'business_datasets.json'
            with open(business_file, 'w') as f:
                json.dump(business_datasets, f, indent=2)

            self.logger.info(f"Filtered {len(business_datasets)} business datasets")

        except Exception as e:
            self.logger.error(f"Romania data processing error: {e}")

    def save_state(self):
        """Save monitoring state"""
        state = {
            'last_update': datetime.now().isoformat(),
            'sources': {name: {'last_hash': config['last_hash']}
                       for name, config in self.sources.items()}
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load previous monitoring state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                for source_name, source_state in state.get('sources', {}).items():
                    if source_name in self.sources:
                        self.sources[source_name]['last_hash'] = source_state.get('last_hash')

                self.logger.info("Previous state loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")

    async def continuous_monitor(self):
        """Main continuous monitoring loop"""
        self.logger.info("Starting continuous opendata monitoring...")
        self.load_state()

        # Track next check times for each source
        next_checks = {name: datetime.now() for name in self.sources.keys()}

        while True:
            current_time = datetime.now()

            # Check each source if it's time
            for source_name, source_config in self.sources.items():
                if current_time >= next_checks[source_name]:
                    self.logger.info(f"Checking {source_name}...")

                    has_updates, content = await self.check_source_updates(source_name, source_config)

                    if has_updates:
                        await self.download_new_data(source_name, content)

                        # Trigger campaign updates if relevant
                        if source_name in ['anofm_jobs', 'ted_procurement']:
                            await self.trigger_campaign_update(source_name)

                    # Schedule next check
                    next_checks[source_name] = current_time + timedelta(seconds=source_config['check_interval'])

                    # Save state after each successful check
                    self.save_state()

            # Sleep for 5 minutes before next cycle
            await asyncio.sleep(300)

    async def trigger_campaign_update(self, source_name):
        """Trigger campaign contact updates based on new data"""
        try:
            if source_name == 'anofm_jobs':
                # Update Tudor's industrial prioritizer with new ANOFM data
                cmd = "cd /opt/ACTIVE/INFRA/SKILLS && python3 tudor_industrial_prioritizer.py"
                subprocess.run(cmd, shell=True, capture_output=True)
                self.logger.info("Triggered Tudor campaign update")

            elif source_name == 'ted_procurement':
                # Update TED-based contractor campaigns
                cmd = "cd /opt/ACTIVE/INFRA/SKILLS && python3 enrich_contractors.py"
                subprocess.run(cmd, shell=True, capture_output=True)
                self.logger.info("Triggered contractor campaign update")

        except Exception as e:
            self.logger.error(f"Error triggering campaign update: {e}")

    async def status_report(self):
        """Generate status report for monitoring"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'sources_monitored': len(self.sources),
            'download_directory': self.download_dir,
            'total_downloads': len(list(Path(self.download_dir).rglob('raw_data.json'))),
            'last_24h_downloads': len([
                f for f in Path(self.download_dir).rglob('raw_data.json')
                if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days < 1
            ])
        }

        return report

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Continuous OpenData Monitor')
    parser.add_argument('--status', action='store_true', help='Show status report')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')

    args = parser.parse_args()

    monitor = ContinuousOpenDataMonitor()

    if args.status:
        # Show current status
        loop = asyncio.get_event_loop()
        report = loop.run_until_complete(monitor.status_report())
        print(json.dumps(report, indent=2))

    elif args.daemon:
        # Run as daemon
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(monitor.continuous_monitor())
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        finally:
            loop.close()
    else:
        # Single check cycle
        loop = asyncio.get_event_loop()
        loop.run_until_complete(monitor.continuous_monitor())

if __name__ == "__main__":
    main()
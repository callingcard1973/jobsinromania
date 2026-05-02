#!/usr/bin/env python3
"""
Simple Continuous OpenData Monitor
Uses home directory for data storage
"""

import asyncio
import aiohttp
import json
import logging
import hashlib
import os
from datetime import datetime
from pathlib import Path

class SimpleOpenDataMonitor:
    def __init__(self):
        self.sources = {
            'anofm_jobs': {
                'url': 'https://www.anofm.ro/locuri-de-munca-vacante',
                'check_interval': 1800,  # 30 minutes
                'last_hash': None
            },
            'romania_data': {
                'url': 'https://data.gov.ro/api/3/action/package_list',
                'check_interval': 7200,  # 2 hours
                'last_hash': None
            }
        }

        self.download_dir = Path.home() / 'OPENDATA' / 'CONTINUOUS'
        self.log_file = Path.home() / 'LOGS' / 'opendata_monitor.log'
        self.state_file = Path.home() / 'OPENDATA' / 'monitor_state.json'

        # Create directories
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

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

    async def check_source(self, source_name, source_config):
        """Check if a source has updates"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(source_config['url']) as response:
                    if response.status == 200:
                        content = await response.text()
                        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

                        if source_config['last_hash'] != content_hash:
                            self.logger.info(f"✅ New data detected for {source_name} (hash: {content_hash})")
                            source_config['last_hash'] = content_hash

                            # Save data
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                            output_file = self.download_dir / f"{source_name}_{timestamp}.json"

                            with open(output_file, 'w') as f:
                                json.dump({
                                    'timestamp': datetime.now().isoformat(),
                                    'source': source_name,
                                    'url': source_config['url'],
                                    'hash': content_hash,
                                    'content_length': len(content)
                                }, f, indent=2)

                            self.logger.info(f"💾 Data saved to {output_file}")
                            return True
                        else:
                            self.logger.info(f"📊 No updates for {source_name}")
                            return False
                    else:
                        self.logger.warning(f"⚠️ HTTP {response.status} for {source_name}")
                        return False

        except Exception as e:
            self.logger.error(f"❌ Error checking {source_name}: {e}")
            return False

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
        """Load previous state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                for source_name, source_state in state.get('sources', {}).items():
                    if source_name in self.sources:
                        self.sources[source_name]['last_hash'] = source_state.get('last_hash')

                self.logger.info("📁 Previous state loaded")
        except Exception as e:
            self.logger.error(f"⚠️ Error loading state: {e}")

    async def monitor_cycle(self):
        """Single monitoring cycle"""
        self.logger.info("🔄 Starting monitoring cycle...")
        self.load_state()

        updates_found = 0
        for source_name, source_config in self.sources.items():
            self.logger.info(f"🔍 Checking {source_name}...")

            if await self.check_source(source_name, source_config):
                updates_found += 1

        self.save_state()

        # Status summary
        total_files = len(list(self.download_dir.glob('*.json')))
        self.logger.info(f"📈 Cycle complete: {updates_found} updates, {total_files} total files")

        return updates_found

    def get_status(self):
        """Get monitoring status"""
        total_files = len(list(self.download_dir.glob('*.json')))
        recent_files = len([f for f in self.download_dir.glob('*.json')
                           if (datetime.now().timestamp() - f.stat().st_mtime) < 86400])

        return {
            'timestamp': datetime.now().isoformat(),
            'sources_monitored': len(self.sources),
            'download_directory': str(self.download_dir),
            'total_files': total_files,
            'recent_files_24h': recent_files,
            'state_file': str(self.state_file),
            'log_file': str(self.log_file)
        }

async def main():
    import sys

    monitor = SimpleOpenDataMonitor()

    if '--status' in sys.argv:
        status = monitor.get_status()
        print(json.dumps(status, indent=2))
    elif '--cycle' in sys.argv:
        updates = await monitor.monitor_cycle()
        print(f"Monitoring cycle complete: {updates} updates found")
    else:
        # Continuous monitoring
        monitor.logger.info("🚀 Starting continuous opendata monitoring...")

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                monitor.logger.info(f"📊 Starting cycle {cycle_count}")

                await monitor.monitor_cycle()

                # Sleep for 5 minutes between cycles
                monitor.logger.info("😴 Sleeping 5 minutes until next cycle...")
                await asyncio.sleep(300)

            except KeyboardInterrupt:
                monitor.logger.info("⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                monitor.logger.error(f"❌ Cycle error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    asyncio.run(main())
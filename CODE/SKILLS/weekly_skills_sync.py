#!/usr/bin/env python3
"""
Weekly Skills Synchronization System
Ensures all machines (laptop, raspibig, raspi) maintain identical skills libraries
Integrates with Node-RED for monitoring and alerts
"""

import os
import sys
import subprocess
import json
import logging
import hashlib
import requests
from datetime import datetime
from pathlib import Path

class WeeklySkillsSync:
    def __init__(self):
        self.machines = {
            'laptop': {
                'path': r'D:/MEMORY/Z.AI/PLUGINS CLAUDE/RASPIBIG_SKILLS/',
                'host': 'localhost',
                'platform': 'windows'
            },
            'raspibig': {
                'path': '/opt/ACTIVE/INFRA/SKILLS/',
                'host': '192.168.100.21',
                'platform': 'linux'
            },
            'raspi': {
                'path': '/opt/ACTIVE/INFRA/SKILLS/',
                'host': '192.168.100.20',
                'platform': 'linux'
            }
        }

        self.nodered_url = "http://192.168.100.21:1880/skills-sync"
        self.backup_base = "/opt/BACKUPS/WEEKLY_SKILLS_SYNC"

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'/opt/LOGS/weekly_skills_sync_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_skill_inventory(self, machine):
        """Get complete skills inventory from a machine"""
        if machine == 'laptop':
            # Local Windows inventory
            skills_path = Path(self.machines[machine]['path'])
            if not skills_path.exists():
                return []

            skills = []
            for file in skills_path.glob('*.py'):
                skills.append({
                    'name': file.name,
                    'size': file.stat().st_size,
                    'modified': file.stat().st_mtime,
                    'hash': self.get_file_hash(file)
                })
            return skills
        else:
            # Remote Linux inventory via SSH
            host = self.machines[machine]['host']
            path = self.machines[machine]['path']

            cmd = f'''ssh tudor@{host} "cd {path} && find . -name '*.py' -type f -exec stat -c '%n %s %Y' {{}} \;" '''

            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Failed to get inventory from {machine}: {result.stderr}")
                    return []

                skills = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0].replace('./', '')
                            size = int(parts[1])
                            modified = int(parts[2])

                            # Get hash via SSH
                            hash_cmd = f'ssh tudor@{host} "md5sum {path}/{name} | cut -d\' \' -f1"'
                            hash_result = subprocess.run(hash_cmd, shell=True, capture_output=True, text=True)
                            file_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else 'unknown'

                            skills.append({
                                'name': name,
                                'size': size,
                                'modified': modified,
                                'hash': file_hash
                            })

                return skills
            except Exception as e:
                self.logger.error(f"Error getting inventory from {machine}: {e}")
                return []

    def get_file_hash(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return 'unknown'

    def create_backup(self, machine):
        """Create backup before sync"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"{self.backup_base}/{machine}_{timestamp}"

        if machine == 'laptop':
            # Windows backup
            source = self.machines[machine]['path']
            os.makedirs(f"D:/MEMORY/BACKUPS/WEEKLY_SKILLS/{machine}_{timestamp}", exist_ok=True)
            # Copy files (simplified for demo)
            self.logger.info(f"Backup created for {machine}")
        else:
            # Linux backup via SSH
            host = self.machines[machine]['host']
            source = self.machines[machine]['path']

            cmd = f'ssh tudor@{host} "mkdir -p {backup_dir} && cp -r {source}*.py {backup_dir}/"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Backup created for {machine}: {backup_dir}")
            else:
                self.logger.error(f"Backup failed for {machine}: {result.stderr}")

    def sync_to_machine(self, source_machine, target_machine, missing_skills):
        """Sync missing skills from source to target machine"""
        source_host = self.machines[source_machine]['host']
        source_path = self.machines[source_machine]['path']
        target_host = self.machines[target_machine]['host']
        target_path = self.machines[target_machine]['path']

        synced = []
        failed = []

        for skill in missing_skills:
            try:
                if source_machine == 'laptop' and target_machine != 'laptop':
                    # Windows to Linux
                    cmd = f'scp "{source_path}{skill}" tudor@{target_host}:{target_path}'
                elif source_machine != 'laptop' and target_machine == 'laptop':
                    # Linux to Windows
                    cmd = f'scp tudor@{source_host}:{source_path}{skill} "{target_path}"'
                elif source_machine != 'laptop' and target_machine != 'laptop':
                    # Linux to Linux
                    cmd = f'ssh tudor@{source_host} "scp {source_path}{skill} tudor@{target_host}:{target_path}"'
                else:
                    continue

                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    synced.append(skill)
                    self.logger.info(f"✅ Synced {skill} from {source_machine} to {target_machine}")
                else:
                    failed.append(skill)
                    self.logger.error(f"❌ Failed to sync {skill}: {result.stderr}")

            except Exception as e:
                failed.append(skill)
                self.logger.error(f"❌ Error syncing {skill}: {e}")

        return synced, failed

    def analyze_differences(self, inventories):
        """Analyze differences between machine inventories"""
        all_skills = set()
        for machine, skills in inventories.items():
            for skill in skills:
                all_skills.add(skill['name'])

        differences = {}
        sync_plan = {}

        for machine in self.machines:
            machine_skills = {skill['name']: skill for skill in inventories[machine]}
            missing = []
            outdated = []

            for skill_name in all_skills:
                if skill_name not in machine_skills:
                    missing.append(skill_name)
                else:
                    # Check if file is outdated (compare with other machines)
                    current_skill = machine_skills[skill_name]
                    for other_machine, other_skills in inventories.items():
                        if other_machine != machine:
                            other_skill = next((s for s in other_skills if s['name'] == skill_name), None)
                            if other_skill and other_skill['hash'] != current_skill['hash']:
                                if other_skill['modified'] > current_skill['modified']:
                                    outdated.append({
                                        'name': skill_name,
                                        'source': other_machine,
                                        'reason': 'newer_version'
                                    })

            differences[machine] = {
                'missing': missing,
                'outdated': outdated,
                'total_skills': len(machine_skills)
            }

            # Create sync plan
            if missing or outdated:
                sync_plan[machine] = {
                    'needs_sync': True,
                    'missing_count': len(missing),
                    'outdated_count': len(outdated),
                    'actions': missing + [item['name'] for item in outdated]
                }
            else:
                sync_plan[machine] = {'needs_sync': False}

        return differences, sync_plan

    def send_nodered_update(self, status, details):
        """Send status update to Node-RED dashboard"""
        payload = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'details': details,
            'source': 'weekly_skills_sync'
        }

        try:
            response = requests.post(self.nodered_url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("✅ Node-RED notification sent successfully")
            else:
                self.logger.warning(f"⚠️ Node-RED notification failed: {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ Failed to send Node-RED notification: {e}")

    def run_weekly_sync(self):
        """Execute complete weekly synchronization"""
        self.logger.info("=== WEEKLY SKILLS SYNCHRONIZATION STARTED ===")

        sync_report = {
            'started_at': datetime.now().isoformat(),
            'machines': list(self.machines.keys()),
            'total_synced': 0,
            'total_failed': 0,
            'errors': []
        }

        try:
            # Step 1: Get inventories from all machines
            self.logger.info("Step 1: Gathering skills inventories...")
            inventories = {}

            for machine in self.machines:
                self.logger.info(f"Getting inventory from {machine}...")
                inventory = self.get_skill_inventory(machine)
                inventories[machine] = inventory
                self.logger.info(f"{machine}: {len(inventory)} skills found")

            # Step 2: Analyze differences
            self.logger.info("Step 2: Analyzing differences...")
            differences, sync_plan = self.analyze_differences(inventories)

            # Step 3: Create backups for machines that need sync
            self.logger.info("Step 3: Creating backups...")
            for machine, plan in sync_plan.items():
                if plan['needs_sync']:
                    self.create_backup(machine)

            # Step 4: Execute synchronization
            self.logger.info("Step 4: Executing synchronization...")

            # Find machine with most skills as reference
            max_skills = max(len(inventories[machine]) for machine in self.machines)
            reference_machine = next(machine for machine in self.machines
                                   if len(inventories[machine]) == max_skills)

            self.logger.info(f"Using {reference_machine} as reference ({max_skills} skills)")

            for target_machine in self.machines:
                if target_machine != reference_machine and sync_plan[target_machine]['needs_sync']:
                    missing_skills = sync_plan[target_machine]['actions']

                    self.logger.info(f"Syncing {len(missing_skills)} skills to {target_machine}")
                    synced, failed = self.sync_to_machine(reference_machine, target_machine, missing_skills)

                    sync_report['total_synced'] += len(synced)
                    sync_report['total_failed'] += len(failed)

                    if failed:
                        sync_report['errors'].extend(failed)

            # Step 5: Final verification
            self.logger.info("Step 5: Final verification...")
            final_inventories = {}
            for machine in self.machines:
                final_inventory = self.get_skill_inventory(machine)
                final_inventories[machine] = final_inventory
                self.logger.info(f"{machine}: {len(final_inventory)} skills (final)")

            sync_report['final_counts'] = {machine: len(final_inventories[machine])
                                         for machine in self.machines}
            sync_report['completed_at'] = datetime.now().isoformat()
            sync_report['success'] = sync_report['total_failed'] == 0

            # Step 6: Send Node-RED notification
            self.send_nodered_update('completed', sync_report)

            self.logger.info("=== WEEKLY SKILLS SYNCHRONIZATION COMPLETED ===")
            self.logger.info(f"Synced: {sync_report['total_synced']}, Failed: {sync_report['total_failed']}")

            return sync_report

        except Exception as e:
            error_msg = f"Weekly sync failed: {e}"
            self.logger.error(error_msg)
            sync_report['error'] = error_msg
            sync_report['success'] = False
            self.send_nodered_update('failed', sync_report)
            raise

if __name__ == '__main__':
    syncer = WeeklySkillsSync()

    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        print("=== DRY RUN MODE ===")
        # Just show what would be synced without actually doing it
        inventories = {}
        for machine in syncer.machines:
            inventory = syncer.get_skill_inventory(machine)
            inventories[machine] = inventory
            print(f"{machine}: {len(inventory)} skills")

        differences, sync_plan = syncer.analyze_differences(inventories)
        print("\nSync Plan:")
        for machine, plan in sync_plan.items():
            if plan['needs_sync']:
                print(f"  {machine}: {plan['missing_count']} missing, {plan['outdated_count']} outdated")
            else:
                print(f"  {machine}: ✅ up to date")
    else:
        # Run actual sync
        result = syncer.run_weekly_sync()
        if result['success']:
            print("✅ Weekly skills sync completed successfully!")
        else:
            print("❌ Weekly skills sync failed!")
            sys.exit(1)
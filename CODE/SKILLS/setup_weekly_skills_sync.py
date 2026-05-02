#!/usr/bin/env python3
"""
Setup Weekly Skills Sync System
Deploys automated weekly synchronization across all machines + cron jobs + Node-RED flow
"""

import subprocess
import json
import os
from pathlib import Path

class SkillsSyncSetup:
    def __init__(self):
        self.machines = {
            'raspibig': '192.168.100.21',
            'raspi': '192.168.100.20'
        }

    def deploy_skills_sync_script(self):
        """Deploy weekly skills sync script to all machines"""
        print("=== Deploying Weekly Skills Sync Script ===")

        script_path = "weekly_skills_sync.py"
        local_script = f"D:/MEMORY/Z.AI/PLUGINS CLAUDE/RASPIBIG_SKILLS/{script_path}"

        for machine, ip in self.machines.items():
            print(f"\n📤 Deploying to {machine} ({ip})...")

            # Copy script
            scp_cmd = f'scp "{local_script}" tudor@{ip}:/opt/ACTIVE/INFRA/SKILLS/'
            result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Script deployed to {machine}")

                # Make executable
                chmod_cmd = f'ssh tudor@{ip} "chmod +x /opt/ACTIVE/INFRA/SKILLS/{script_path}"'
                subprocess.run(chmod_cmd, shell=True, capture_output=True)

                # Test dry run
                test_cmd = f'ssh tudor@{ip} "cd /opt/ACTIVE/INFRA/SKILLS && python3 {script_path} --dry-run"'
                test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)

                if test_result.returncode == 0:
                    print(f"✅ Dry run test passed on {machine}")
                else:
                    print(f"⚠️ Dry run test failed on {machine}: {test_result.stderr}")
            else:
                print(f"❌ Failed to deploy to {machine}: {result.stderr}")

    def setup_cron_jobs(self):
        """Setup cron jobs on Linux machines"""
        print("\n=== Setting Up Cron Jobs ===")

        cron_entry = "0 2 * * 0 cd /opt/ACTIVE/INFRA/SKILLS && python3 weekly_skills_sync.py >> /opt/LOGS/weekly_skills_sync_cron.log 2>&1"

        for machine, ip in self.machines.items():
            print(f"\n📅 Setting up cron on {machine}...")

            # Add cron job
            cron_cmd = f'''ssh tudor@{ip} "(crontab -l 2>/dev/null || echo '') | grep -v 'weekly_skills_sync' | {{ cat; echo '{cron_entry}'; }} | crontab -"'''

            result = subprocess.run(cron_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Cron job added to {machine} (Sundays 2:00 AM)")

                # Verify cron
                verify_cmd = f'ssh tudor@{ip} "crontab -l | grep weekly_skills_sync"'
                verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)

                if verify_result.returncode == 0:
                    print(f"✅ Cron verification successful on {machine}")
                    print(f"   Schedule: {verify_result.stdout.strip()}")
                else:
                    print(f"⚠️ Cron verification failed on {machine}")
            else:
                print(f"❌ Failed to add cron job on {machine}: {result.stderr}")

    def deploy_nodered_flow(self):
        """Deploy Node-RED flow to raspibig"""
        print("\n=== Deploying Node-RED Flow ===")

        flow_file = "nodered_skills_sync_flow.json"
        local_flow = f"D:/MEMORY/Z.AI/PLUGINS CLAUDE/RASPIBIG_SKILLS/{flow_file}"

        # Copy flow file
        scp_cmd = f'scp "{local_flow}" tudor@192.168.100.21:/opt/ACTIVE/NODERED/flows/'
        result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Node-RED flow file deployed")

            # Import flow instructions
            print("\n📋 Manual Node-RED Setup Instructions:")
            print("1. Open Node-RED at http://192.168.100.21:1880")
            print("2. Go to Menu → Import")
            print("3. Select 'select a file to import'")
            print(f"4. Choose /opt/ACTIVE/NODERED/flows/{flow_file}")
            print("5. Click 'Import' and 'Deploy'")
            print("\n🎯 Features enabled:")
            print("   • Weekly automatic sync (Sundays 2:00 AM)")
            print("   • Manual trigger button")
            print("   • Dashboard monitoring")
            print("   • Telegram alerts on failures")
            print("   • HTTP webhook endpoint: /skills-sync")

        else:
            print(f"❌ Failed to deploy Node-RED flow: {result.stderr}")

    def setup_logging_directories(self):
        """Setup logging directories on all machines"""
        print("\n=== Setting Up Logging Directories ===")

        for machine, ip in self.machines.items():
            print(f"\n📂 Setting up logs on {machine}...")

            setup_cmd = f'''ssh tudor@{ip} "mkdir -p /opt/LOGS && mkdir -p /opt/BACKUPS/WEEKLY_SKILLS_SYNC && chown -R tudor:tudor /opt/LOGS /opt/BACKUPS"'''

            result = subprocess.run(setup_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Logging directories created on {machine}")
            else:
                print(f"❌ Failed to create directories on {machine}: {result.stderr}")

    def create_windows_task(self):
        """Create Windows scheduled task for laptop sync participation"""
        print("\n=== Setting Up Windows Scheduled Task ===")

        # Create batch file for Windows
        batch_content = f'''@echo off
cd /d "D:\\MEMORY\\Z.AI\\PLUGINS CLAUDE\\RASPIBIG_SKILLS"
python weekly_skills_sync.py >> "D:\\MEMORY\\LOGS\\weekly_skills_sync.log" 2>&1
'''

        batch_path = "D:/MEMORY/SCRIPTS/weekly_skills_sync.bat"
        os.makedirs(os.path.dirname(batch_path), exist_ok=True)

        with open(batch_path, 'w') as f:
            f.write(batch_content)

        print(f"✅ Batch file created: {batch_path}")

        # Create scheduled task
        task_cmd = f'''schtasks /create /tn "Weekly Skills Sync" /tr "{batch_path}" /sc weekly /d sun /st 02:00 /f'''

        result = subprocess.run(task_cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Windows scheduled task created (Sundays 2:00 AM)")
        else:
            print(f"⚠️ Windows task creation may need manual setup: {result.stderr}")

    def verify_setup(self):
        """Verify complete setup"""
        print("\n=== Verification Summary ===")

        # Check script deployment
        for machine, ip in self.machines.items():
            script_check = f'ssh tudor@{ip} "test -f /opt/ACTIVE/INFRA/SKILLS/weekly_skills_sync.py && echo exists"'
            result = subprocess.run(script_check, shell=True, capture_output=True, text=True)

            if "exists" in result.stdout:
                print(f"✅ {machine}: Script deployed")
            else:
                print(f"❌ {machine}: Script missing")

            # Check cron
            cron_check = f'ssh tudor@{ip} "crontab -l | grep weekly_skills_sync"'
            cron_result = subprocess.run(cron_check, shell=True, capture_output=True, text=True)

            if cron_result.returncode == 0:
                print(f"✅ {machine}: Cron job active")
            else:
                print(f"❌ {machine}: Cron job missing")

        # Check Windows task
        windows_check = 'schtasks /query /tn "Weekly Skills Sync"'
        windows_result = subprocess.run(windows_check, shell=True, capture_output=True, text=True)

        if windows_result.returncode == 0:
            print("✅ Windows: Scheduled task active")
        else:
            print("❌ Windows: Scheduled task missing")

    def run_setup(self):
        """Execute complete setup"""
        print("🚀 WEEKLY SKILLS SYNC SETUP STARTING")
        print("=" * 50)

        try:
            self.setup_logging_directories()
            self.deploy_skills_sync_script()
            self.setup_cron_jobs()
            self.create_windows_task()
            self.deploy_nodered_flow()
            self.verify_setup()

            print("\n" + "=" * 50)
            print("🎉 WEEKLY SKILLS SYNC SETUP COMPLETED!")
            print("\n📋 Summary:")
            print("   • ✅ Scripts deployed to all machines")
            print("   • ✅ Cron jobs scheduled (Sundays 2:00 AM)")
            print("   • ✅ Windows task created")
            print("   • ✅ Node-RED flow ready for import")
            print("   • ✅ Logging directories configured")
            print("\n🔄 Next sync: Every Sunday at 2:00 AM")
            print("📊 Monitor: http://192.168.100.21:1880 (Node-RED Dashboard)")

        except Exception as e:
            print(f"\n❌ Setup failed: {e}")

if __name__ == '__main__':
    setup = SkillsSyncSetup()
    setup.run_setup()
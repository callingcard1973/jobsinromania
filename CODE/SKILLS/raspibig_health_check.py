#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime

class HealthCheck:
    def __init__(self):
        self.log_file = "/home/tudor/.logs/raspibig_health.log"
        self.critical_services = ["postgresql", "node-red", "netdata"]
    
    def check_service(self, service):
        try:
            result = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def check_disk(self):
        result = subprocess.run(["df", "/"], capture_output=True, text=True)
        for line in result.stdout.split("\n")[1:]:
            if line:
                parts = line.split()
                usage = int(parts[4].rstrip("%"))
                return usage < 80
        return True
    
    def check_swap(self):
        result = subprocess.run(["free", "-b"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if "Swap:" in line:
                parts = line.split()
                swap_used_mb = int(parts[2]) / 1024 / 1024
                return swap_used_mb < 1000
        return True
    
    def run(self):
        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "disk_ok": self.check_disk(),
            "swap_ok": self.check_swap(),
        }
        
        for service in self.critical_services:
            status["services"][service] = self.check_service(service)
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(status) + "\n")
        
        issues = []
        for service, ok in status["services"].items():
            if not ok:
                issues.append(service + " DOWN")
        if not status["disk_ok"]:
            issues.append("Disk > 80%")
        if not status["swap_ok"]:
            issues.append("Swap > 1GB")
        
        if issues:
            print("WARNING: " + ", ".join(issues))
        else:
            print("OK - All systems healthy")

if __name__ == "__main__":
    HealthCheck().run()

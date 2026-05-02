#!/usr/bin/env python3
"""
OpenClaw Management Skill
=========================
Manage OpenClaw gateway and nodes across raspi, raspibig, and laptop-hp.

Architecture:
- raspibig (192.168.100.21): Gateway + Node (central)
- raspi (192.168.100.20): Node
- laptop-hp (100.81.18.34 via Tailscale): Node (Windows)

Gateway URL: http://192.168.100.21:18789
Gateway Token: 4449b568a1b297bc1cb4dae368c889fe0f0f4a2735bb228e
"""

import subprocess
import json
import sys

GATEWAY_TOKEN = "4449b568a1b297bc1cb4dae368c889fe0f0f4a2735bb228e"
GATEWAY_URL = "192.168.100.21:18789"

def run_cmd(cmd, timeout=30):
    """Run command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "Timeout", 1

def status():
    """Show all nodes status."""
    print("=== OpenClaw Status ===\n")
    
    # Gateway
    out, _ = run_cmd("curl -s http://192.168.100.21:18789/ | head -1")
    print(f"Gateway: {'✓ Running' if 'doctype' in out.lower() else '✗ Down'}")
    
    # Presence
    out, _ = run_cmd(f'openclaw system presence 2>/dev/null')
    if out:
        try:
            presence = json.loads(out)
            print(f"\nConnected nodes: {len(presence)}")
            for node in presence:
                print(f"  - {node.get('host', 'unknown')} ({node.get('ip', '?')}) - {node.get('reason', '?')}")
        except:
            print("Could not parse presence")
    
    # Devices
    print("\n=== Paired Devices ===")
    run_cmd(f'openclaw devices list')

def restart_all():
    """Restart all nodes."""
    print("Restarting all nodes...")
    
    # raspibig node
    print("  raspibig node...", end=" ")
    out, rc = run_cmd("systemctl --user restart openclaw-node")
    print("✓" if rc == 0 else "✗")
    
    # raspi node
    print("  raspi node...", end=" ")
    out, rc = run_cmd("ssh raspi 'systemctl --user restart openclaw-node'")
    print("✓" if rc == 0 else "✗")
    
    # laptop-hp node
    print("  laptop-hp node...", end=" ")
    out, rc = run_cmd("ssh apami@192.168.100.27 'openclaw node restart'")
    print("✓" if rc == 0 else "✗")
    
    print("\nWaiting for connections...")
    import time
    time.sleep(5)
    status()

def run_on_node(node, command):
    """Run command on a node via system.run."""
    cmd = f'''openclaw nodes invoke --node {node} --command system.run --params '{{"command": {json.dumps(command.split())}}}' --token "{GATEWAY_TOKEN}" 2>&1'''
    out, rc = run_cmd(cmd, timeout=15)
    
    if rc == 0:
        try:
            result = json.loads(out)
            if result.get('ok'):
                payload = result.get('payload', {})
                print(f"Exit code: {payload.get('exitCode', '?')}")
                print(f"Stdout: {payload.get('stdout', '').strip()}")
                if payload.get('stderr'):
                    print(f"Stderr: {payload.get('stderr', '').strip()}")
                return payload.get('exitCode', 1)
        except json.JSONDecodeError:
            pass
    
    print(f"Error: {out}")
    return 1

def allowlist_add(node, pattern):
    """Add command pattern to allowlist."""
    cmd = f'openclaw approvals allowlist add --agent "*" --node {node} "{pattern}" --token "{GATEWAY_TOKEN}"'
    out, rc = run_cmd(cmd)
    print(out if rc == 0 else f"Error: {out}")

def help():
    print("""
OpenClaw Management Skill
=========================

Usage:
  python3 openclaw_manage.py status          - Show all nodes status
  python3 openclaw_manage.py restart         - Restart all nodes
  python3 openclaw_manage.py run NODE CMD    - Run command on node
  python3 openclaw_manage.py allow NODE PAT  - Add pattern to allowlist
  
Nodes: raspibig, raspi, laptop-hp

Examples:
  python3 openclaw_manage.py status
  python3 openclaw_manage.py run laptop-hp hostname
  python3 openclaw_manage.py allow laptop-hp "C:\\\\WINDOWS\\\\system32\\\\ipconfig.exe"
  
Direct CLI:
  openclaw system presence
  openclaw devices list
  openclaw nodes invoke --node laptop-hp --command system.which --params '{"bins": ["git"]}' --token TOKEN
  openclaw nodes invoke --node laptop-hp --command system.run --params '{"command": ["hostname"]}' --token TOKEN
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help()
    elif sys.argv[1] == "status":
        status()
    elif sys.argv[1] == "restart":
        restart_all()
    elif sys.argv[1] == "run" and len(sys.argv) >= 4:
        run_on_node(sys.argv[2], " ".join(sys.argv[3:]))
    elif sys.argv[1] == "allow" and len(sys.argv) >= 4:
        allowlist_add(sys.argv[2], sys.argv[3])
    else:
        help()

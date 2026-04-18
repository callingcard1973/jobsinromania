#!/usr/bin/env python3
"""Patch dashboard.py to load Mailrelay and Resend senders."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# 1. Add mailrelay and resend to SENDERS dict init
content = content.replace(
    "SENDERS = {'brevo': [], 'gmail': [], 'a2': []}",
    "SENDERS = {'brevo': [], 'gmail': [], 'a2': [], 'mailrelay': [], 'resend': []}"
)

# 2. Add mailrelay/resend loading after gmail loading
old_gmail = """        for key, cfg in data.get('gmail', {}).items():
            if cfg.get('enabled', True):
                SENDERS['gmail'].append({
                    'key': f"gmail:{key}",
                    'email': cfg['email'],
                    'name': cfg.get('name', key),
                    'daily_limit': cfg.get('daily_limit', 100)
                })
    except Exception as e:
        print(f"Failed to load senders.json: {e}", file=sys.stderr)"""

new_gmail = """        for key, cfg in data.get('gmail', {}).items():
            if cfg.get('enabled', True):
                SENDERS['gmail'].append({
                    'key': f"gmail:{key}",
                    'email': cfg['email'],
                    'name': cfg.get('name', key),
                    'daily_limit': cfg.get('daily_limit', 100)
                })
        for key, cfg in data.get('mailrelay', {}).items():
            if cfg.get('enabled', True):
                SENDERS['mailrelay'].append({
                    'key': f"mailrelay:{key}",
                    'email': cfg['email'],
                    'name': cfg.get('name', key),
                    'daily_limit': cfg.get('daily_limit', 2666),
                    'api_url': cfg.get('api_url', '')
                })
        for key, cfg in data.get('resend', {}).items():
            if cfg.get('enabled', True):
                SENDERS['resend'].append({
                    'key': f"resend:{key}",
                    'email': cfg['email'],
                    'name': cfg.get('name', key),
                    'daily_limit': cfg.get('daily_limit', 100)
                })
    except Exception as e:
        print(f"Failed to load senders.json: {e}", file=sys.stderr)"""
content = content.replace(old_gmail, new_gmail)

# 3. Add Mailrelay and Resend optgroups to the sender dropdown in HTML
old_dropdown = """      <optgroup label="A2 SMTP (50/day)">"""
new_dropdown = """      <optgroup label="Mailrelay (2666/day)">
        {% for s in senders.get('mailrelay', []) %}
        <option value="{{ s.email }}">{{ s.email }} ({{ s.name }})</option>
        {% endfor %}
      </optgroup>
      <optgroup label="Resend (100/day)">
        {% for s in senders.get('resend', []) %}
        <option value="{{ s.email }}">{{ s.email }} ({{ s.name }})</option>
        {% endfor %}
      </optgroup>
      <optgroup label="A2 SMTP (50/day)">"""
content = content.replace(old_dropdown, new_dropdown)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Mailrelay + Resend senders added")

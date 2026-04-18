#!/usr/bin/env python3
"""Add all campaign settings to the edit page."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard_html.py"
with open(path, "r") as f:
    content = f.read()

old_form = """  <div class="form-group">
    <label>Enabled</label>
    <select name="{{ sector_name }}_enabled">
      <option value="true" {% if sector.enabled %}selected{% endif %}>Yes</option>
      <option value="false" {% if not sector.enabled %}selected{% endif %}>No</option>
    </select>
  </div>

  <div class="form-group">
    <label>Daily Limit</label>
    <input type="number" name="{{ sector_name }}_daily_limit" value="{{ sector.daily_limit }}">
  </div>

  <div class="form-group">
    <label>Delay (seconds)</label>
    <input type="number" name="{{ sector_name }}_delay_min" value="{{ sector.delay_min|default(180) }}" placeholder="Min delay">
  </div>

  <div class="form-group">
    <label>Sender</label>"""

new_form = """  <div class="row">
    <div class="form-group">
      <label>Enabled</label>
      <select name="{{ sector_name }}_enabled">
        <option value="true" {% if sector.enabled %}selected{% endif %}>Yes</option>
        <option value="false" {% if not sector.enabled %}selected{% endif %}>No</option>
      </select>
    </div>
    <div class="form-group">
      <label>Sender Type</label>
      <select name="{{ sector_name }}_sender_type">
        <option value="brevo" {% if sector.get('sender_type','brevo')=='brevo' %}selected{% endif %}>Brevo API</option>
        <option value="mailrelay" {% if sector.get('sender_type')=='mailrelay' %}selected{% endif %}>Mailrelay API</option>
        <option value="gmail_only" {% if sector.get('sender_type')=='gmail_only' %}selected{% endif %}>Gmail Only</option>
        <option value="zoho" {% if sector.get('sender_type')=='zoho' %}selected{% endif %}>Zoho SMTP</option>
      </select>
    </div>
  </div>

  <div class="row">
    <div class="form-group">
      <label>Daily Limit</label>
      <input type="number" name="{{ sector_name }}_daily_limit" value="{{ sector.daily_limit }}" min="1" max="5000">
    </div>
    <div class="form-group">
      <label>Batch Size (0 = no batching)</label>
      <input type="number" name="{{ sector_name }}_batch_size" value="{{ sector.get('batch_size', 0) }}" min="0">
    </div>
  </div>

  <div class="row">
    <div class="form-group">
      <label>Min Delay (seconds)</label>
      <input type="number" name="{{ sector_name }}_delay_min" value="{{ sector.delay_min|default(180) }}" min="30">
    </div>
    <div class="form-group">
      <label>Max Delay (seconds)</label>
      <input type="number" name="{{ sector_name }}_delay_max" value="{{ sector.delay_max|default(360) }}" min="60">
    </div>
  </div>

  <div class="row">
    <div class="form-group">
      <label>Reply-To Email</label>
      <input type="email" name="{{ sector_name }}_reply_to" value="{{ sector.get('reply_to', '') }}" placeholder="e.g. manpower.dristor@gmail.com">
    </div>
    <div class="form-group">
      <label>Sender Name</label>
      <input type="text" name="{{ sector_name }}_sender_name" value="{{ sector.get('sender_name', '') }}">
    </div>
  </div>

  <div class="form-group">
    <label>SQL Filter (WHERE clause, blank = all)</label>
    <input type="text" name="{{ sector_name }}_filter" value="{{ sector.get('filter', '') }}" placeholder="e.g. judet = 'BUCURESTI'">
  </div>

  <div class="row">
    <div class="form-group">
      <label>Business Hours</label>
      <select name="{{ sector_name }}_bh_enabled">
        <option value="true" {% if sector.get('business_hours',{}).get('enabled') %}selected{% endif %}>Yes (8-18 Mon-Fri)</option>
        <option value="false" {% if not sector.get('business_hours',{}).get('enabled') %}selected{% endif %}>No (send anytime)</option>
      </select>
    </div>
    <div class="form-group">
      <label>Start Hour</label>
      <input type="number" name="{{ sector_name }}_bh_start" value="{{ sector.get('business_hours',{}).get('start', 8) }}" min="0" max="23">
    </div>
    <div class="form-group">
      <label>End Hour</label>
      <input type="number" name="{{ sector_name }}_bh_end" value="{{ sector.get('business_hours',{}).get('end', 18) }}" min="1" max="24">
    </div>
  </div>

  <div class="row">
    <div class="form-group">
      <label>Template Rotation (number of templates)</label>
      <input type="number" name="{{ sector_name }}_template_count" value="{{ sector.get('template_count', 1) }}" min="1" max="10">
    </div>
    <div class="form-group">
      <label>Exclude Gov Domains</label>
      <select name="{{ sector_name }}_gov_filter">
        <option value="true" {% if cfg.get('gov_domains') %}selected{% endif %}>Yes</option>
        <option value="false" {% if not cfg.get('gov_domains') %}selected{% endif %}>No</option>
      </select>
    </div>
  </div>

  <div class="form-group" style="margin-top:15px;padding:12px;background:#0f172a;border-radius:8px;border:1px solid #334155;">
    <label style="color:#38bdf8;margin-bottom:5px;">Test Mode</label>
    <div class="row">
      <div class="form-group" style="margin-bottom:0;">
        <input type="email" name="{{ sector_name }}_test_email" placeholder="Your email for test send" style="margin-bottom:0;">
      </div>
      <div class="form-group" style="margin-bottom:0;">
        <button type="submit" name="action" value="test_{{ sector_name }}" class="btn btn-secondary" style="width:100%;">Send 1 Test Email</button>
      </div>
    </div>
  </div>

  <div class="form-group">
    <label>Sender</label>"""

content = content.replace(old_form, new_form)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Edit form now has all settings")

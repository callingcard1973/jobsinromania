#!/usr/bin/env python3
"""
Unified Dashboard v3.0 - All raspibig + raspi services in one place

URL: http://raspibig:8085

Changes in v3.0:
- Fixed disk monitoring to include all /mnt/* mounts
- Fixed email stats with proper date tracking
- Fixed scraper count to exclude non-scraper processes
- Removed Odoo monitoring (archived)
- Added raspi system reports section

Usage:
    python3 unified_dashboard.py              # Start on 8085
    python3 unified_dashboard.py --port 8085  # Custom port
"""

import os
import sys
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Flask, render_template_string, jsonify, request, Response

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

app = Flask(__name__)

# Paths
LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS')
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA')
EMAIL_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')

TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Unified Dashboard - raspibig + raspi</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0a0a1a; color: #eee; line-height: 1.5;
        }
        .container { max-width: 1600px; margin: 0 auto; padding: 15px; }

        /* Header */
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 15px 0; border-bottom: 1px solid #333; margin-bottom: 20px;
        }
        header h1 { color: #00d9ff; font-size: 1.5em; }
        header .status { display: flex; gap: 15px; font-size: 0.9em; }
        header .status span { padding: 5px 12px; border-radius: 15px; background: #1a1a2e; }
        header .status .ok { color: #4ade80; }
        header .status .warn { color: #ffc107; }
        header .status .err { color: #ff6b6b; }

        /* Grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 15px; }

        /* Cards */
        .card {
            background: #12122a; border-radius: 10px; padding: 15px;
            border: 1px solid #2a2a4a;
        }
        .card.raspi { border-color: #4ade80; }
        .card h2 {
            font-size: 0.85em; color: #888; text-transform: uppercase;
            margin-bottom: 12px; display: flex; justify-content: space-between;
        }
        .card h2 .badge {
            background: #00d9ff; color: #000; padding: 2px 8px;
            border-radius: 10px; font-size: 0.9em;
        }
        .card h2 .badge.warn { background: #ffc107; }
        .card h2 .badge.err { background: #ff6b6b; color: #fff; }
        .card h2 .badge.raspi { background: #4ade80; }

        /* Stats row */
        .stats-row {
            display: flex; gap: 15px; margin-bottom: 10px;
        }
        .stat {
            flex: 1; background: #1a1a3a; padding: 12px; border-radius: 8px; text-align: center;
        }
        .stat .value { font-size: 1.8em; font-weight: bold; color: #fff; }
        .stat .label { font-size: 0.75em; color: #666; }
        .stat.ok .value { color: #4ade80; }
        .stat.warn .value { color: #ffc107; }
        .stat.err .value { color: #ff6b6b; }
        .scraper-table { border-collapse: collapse; }
        .scraper-table th, .scraper-table td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #2a2a4a; }
        .scraper-table th { color: #888; font-weight: normal; }
        .scraper-table tr.ok td:nth-child(4) { color: #4ade80; }
        .scraper-table tr.warn td:nth-child(4) { color: #ffc107; }
        .scraper-table tr.err td:nth-child(4) { color: #ff6b6b; }

        /* List items */
        .list { max-height: 350px; overflow-y: auto; }
        .list-item {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 10px; border-bottom: 1px solid #2a2a4a;
            font-size: 0.85em;
        }
        .list-item:hover { background: #1a1a3a; }
        .list-item .name { color: #ccc; }
        .list-item .value { color: #888; }
        .list-item .ok { color: #4ade80; }
        .list-item .warn { color: #ffc107; }
        .list-item .err { color: #ff6b6b; }
        .list-item .stale { color: #888; font-style: italic; }

        /* Progress bar */
        .progress { height: 6px; background: #2a2a4a; border-radius: 3px; margin-top: 8px; }
        .progress-bar { height: 100%; border-radius: 3px; background: #00d9ff; }
        .progress-bar.warn { background: #ffc107; }
        .progress-bar.err { background: #ff6b6b; }

        /* Services grid */
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
        .service {
            background: #1a1a3a; padding: 10px; border-radius: 6px; text-align: center;
            font-size: 0.8em;
        }
        .service .port { font-size: 1.2em; font-weight: bold; color: #00d9ff; }
        .service .name { color: #888; }
        .service.down { opacity: 0.5; }
        .service.down .port { color: #ff6b6b; }

        /* Log viewer */
        .log-viewer {
            background: #0d0d1a; border-radius: 6px; padding: 10px;
            font-family: monospace; font-size: 11px; max-height: 150px;
            overflow-y: auto; white-space: pre-wrap;
        }
        .log-viewer .err { color: #ff6b6b; }
        .log-viewer .warn { color: #ffc107; }

        /* Alerts */
        .alerts { margin-bottom: 15px; }
        .alert {
            padding: 10px 15px; border-radius: 6px; margin-bottom: 8px;
            display: flex; justify-content: space-between;
        }
        .alert.warn { background: rgba(255,193,7,0.15); border: 1px solid #ffc107; }
        .alert.err { background: rgba(255,107,107,0.15); border: 1px solid #ff6b6b; }
        .alert.info { background: rgba(0,217,255,0.1); border: 1px solid #00d9ff; }

        /* Footer */
        footer {
            text-align: center; padding: 20px; color: #444; font-size: 0.8em;
            margin-top: 20px; border-top: 1px solid #222;
        }
        footer a { color: #00d9ff; }

        /* Section headers */
        .section-header {
            font-size: 1.1em; color: #00d9ff; margin: 20px 0 15px 0;
            padding-bottom: 8px; border-bottom: 1px solid #333;
        }
        .section-header.raspi { color: #4ade80; }

        /* Responsive */
        @media (max-width: 800px) {
            .grid { grid-template-columns: 1fr; }
            .stats-row { flex-wrap: wrap; }
            .stat { min-width: 45%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>raspibig + raspi Dashboard</h1>
            <div class="status">
                <span id="uptime">Uptime: -</span>
                <span id="raspi-status">raspi: -</span>
                <span id="time">-</span>
                <span id="overall-status" class="ok">OK</span>
            </div>
        </header>

        <div id="alerts" class="alerts"></div>
        <div id="debug-info" style="background:#1a1a2e;padding:10px;margin-bottom:15px;border-radius:5px;color:#ffc107;font-family:monospace;">Loading...</div>

        <div class="grid">
            <!-- Email Campaigns -->
            <div class="card">
                <h2>Email Campaigns <span class="badge" id="email-badge">-</span> <a href="http://raspibig:8088" style="font-size:0.7em;color:#00ff88;">[Manage]</a></h2>
                <div class="stats-row">
                    <div class="stat" id="email-sent"><div class="value">-</div><div class="label">Sent Today</div></div>
                    <div class="stat" id="email-capacity"><div class="value">-</div><div class="label">Capacity</div></div>
                    <div class="stat" id="email-bounces"><div class="value">-</div><div class="label">Bounces</div></div>
                </div>
                <div class="list" id="email-list"></div>
            </div>

            <!-- Scrapers -->
            <div class="card" style="grid-column: span 2;">
                <h2>Scrapers <span class="badge" id="scraper-badge">-</span></h2>
                <div class="stats-row">
                    <div class="stat" id="scraper-running"><div class="value">-</div><div class="label">Running</div></div>
                    <div class="stat" id="scraper-today"><div class="value">-</div><div class="label">Today</div></div>
                    <div class="stat" id="scraper-rows"><div class="value">-</div><div class="label">Rows</div></div>
                </div>
                <table class="scraper-table" style="width:100%; font-size:0.85em; margin-top:10px;">
                    <thead><tr><th>Scraper</th><th>Schedule</th><th>Last Run</th><th>Status</th><th>Rows</th></tr></thead>
                    <tbody id="scraper-schedule"></tbody>
                </table>
            </div>

            
            <!-- Issues & Actions -->
            <div class="card" style="grid-column: 1 / -1; border-color: #ff6b6b;">
                <h2>Issues & Actions <span class="badge" id="issues-badge">-</span>
                    <button onclick="runSelfHealer()" style="margin-left:auto;padding:4px 12px;background:#00d9ff;border:none;border-radius:4px;cursor:pointer;font-size:0.8em;">Run Self-Healer</button>
                </h2>
                <table style="width:100%; font-size:0.85em; border-collapse:collapse;">
                    <thead><tr style="border-bottom:1px solid #333;"><th style="text-align:left;padding:8px;">Issue</th><th style="text-align:left;">Type</th><th style="text-align:left;">Details</th><th style="text-align:right;">Action</th></tr></thead>
                    <tbody id="issues-table"></tbody>
                </table>
                <div id="no-issues" style="padding:20px;text-align:center;color:#4ade80;display:none;">All systems operational</div>
            </div>

<!-- Logs -->
            <div class="card">
                <h2>Logs <span class="badge" id="log-badge">-</span></h2>
                <div class="stats-row">
                    <div class="stat" id="log-size"><div class="value">-</div><div class="label">Total Size</div></div>
                    <div class="stat" id="log-files"><div class="value">-</div><div class="label">Files</div></div>
                    <div class="stat" id="log-errors"><div class="value">-</div><div class="label">Errors 24h</div></div>
                </div>
                <div class="log-viewer" id="log-recent"></div>
            </div>

            <!-- Disk Usage (raspibig) -->
            <div class="card">
                <h2>Disk Usage (raspibig)</h2>
                <div id="disk-list"></div>
            </div>

            <!-- Docker -->
            <div class="card">
                <h2>Docker <span class="badge" id="docker-badge">-</span></h2>
                <div class="list" id="docker-list"></div>
            </div>

            <!-- Raspi System -->
            <div class="card raspi">
                <h2>Raspi System <span class="badge raspi" id="raspi-badge">-</span></h2>
                <div class="stats-row">
                    <div class="stat" id="raspi-cpu"><div class="value">-</div><div class="label">CPU</div></div>
                    <div class="stat" id="raspi-mem"><div class="value">-</div><div class="label">Memory</div></div>
                    <div class="stat" id="raspi-disk"><div class="value">-</div><div class="label">Disk</div></div>
                </div>
                <div class="list" id="raspi-services"></div>
            </div>

            <!-- Brevo Warmup -->
            <div class="card raspi">
                <h2>Brevo Warmup <span class="badge raspi" id="brevo-badge">-</span></h2>
                <div class="stats-row">
                    <div class="stat" id="brevo-active"><div class="value">-</div><div class="label">Active</div></div>
                    <div class="stat" id="brevo-sent"><div class="value">-</div><div class="label">Sent Today</div></div>
                    <div class="stat" id="brevo-paused"><div class="value">-</div><div class="label">Paused</div></div>
                </div>
                <div class="list" id="brevo-list"></div>
            </div>

            <!-- A2 SMTP Warmup -->
            <div class="card raspi">
                <h2>A2 SMTP Warmup <span class="badge raspi" id="a2-badge">-</span></h2>
                <div class="stats-row">
                    <div class="stat" id="a2-sent"><div class="value">-</div><div class="label">Sent Today</div></div>
                    <div class="stat" id="a2-remaining"><div class="value">-</div><div class="label">Remaining</div></div>
                    <div class="stat" id="a2-limit"><div class="value">-</div><div class="label">Daily Limit</div></div>
                </div>
                <div class="list" id="a2-list"></div>
            </div>

            <!-- Services -->
            <div class="card" style="grid-column: span 2;">
                <h2>Services (raspibig)</h2>
                <div class="services" id="services-list"></div>
            </div>

            <!-- Quick Actions -->
            <div class="card" style="grid-column: span 2;">
                <h2>Quick Actions (Raspi) 🔧</h2>
                <div class="quick-actions" style="display:flex;gap:10px;flex-wrap:wrap;padding:10px 0;">
                    <button class="fix-btn" data-fix="health_check" style="padding:8px 16px;background:#4ade80;border:none;border-radius:4px;cursor:pointer;">Health Check</button>
                    <button class="fix-btn" data-fix="bounce_high" style="padding:8px 16px;background:#fbbf24;border:none;border-radius:4px;cursor:pointer;">Bounce Cleanup</button>
                    <button class="fix-btn" data-fix="campaign_low" style="padding:8px 16px;background:#60a5fa;border:none;border-radius:4px;cursor:pointer;">Feed Campaigns</button>
                    <button class="fix-btn" data-fix="disk_full" style="padding:8px 16px;background:#f472b6;border:none;border-radius:4px;cursor:pointer;">Disk Cleanup</button>
                    <button class="fix-btn" data-fix="autofix" style="padding:8px 16px;background:#a78bfa;border:none;border-radius:4px;cursor:pointer;">Auto Fix All</button>
                    <button class="fix-btn" data-fix="warmup_paused" style="padding:8px 16px;background:#34d399;border:none;border-radius:4px;cursor:pointer;">Warmup Status</button>
                </div>
                <div id="fix-result" style="margin-top:10px;padding:10px;background:#222;display:none;max-height:200px;overflow:auto;font-family:monospace;white-space:pre-wrap;"></div>
            </div>
        </div>

        <footer>
            Unified Dashboard v3.0 | Updated: <span id="last-update">-</span> |
            <a href="http://raspibig:8088" style="color:#00ff88;font-weight:bold;">Campaign Manager</a> |
            <a href="/api/stats">API</a> | <a href="/api/logs">Logs API</a>
        </footer>
    </div>

    <script>
        const SERVICES = [
            {port: 81, name: 'CasaOS'},
            {port: 1880, name: 'Node-RED'},
            {port: 5432, name: 'PostgreSQL'},
            {port: 6379, name: 'Redis'},
            {port: 8085, name: 'Dashboard'},
            {port: 8087, name: 'FreeScout'},
            {port: 8088, name: 'Campaigns'},
            {port: 9050, name: 'Tor'},
            {port: 9443, name: 'Portainer'},
            ,
        ];

        async function fetchData() {
            const debugEl = document.getElementById('debug-info');
            try {
                debugEl.textContent = 'Fetching /api/stats...';
                const resp = await fetch('/api/stats');
                if (!resp.ok) {
                    debugEl.textContent = 'HTTP Error: ' + resp.status;
                    return;
                }
                const data = await resp.json();
                debugEl.textContent = 'Data loaded: ' + Object.keys(data).join(', ');
                updateUI(data);
            } catch (e) {
                debugEl.textContent = 'ERROR: ' + e.message;
                console.error('Fetch error:', e);
            }
        }

        function updateUI(data) {
            // Time
            document.getElementById('time').textContent = new Date().toLocaleTimeString();
            document.getElementById('last-update').textContent = new Date().toLocaleString();
            document.getElementById('uptime').textContent = 'Uptime: ' + data.uptime;

            // Raspi status
            const raspiEl = document.getElementById('raspi-status');
            if (data.raspi && data.raspi.online) {
                raspiEl.textContent = 'raspi: OK';
                raspiEl.className = 'ok';
            } else {
                raspiEl.textContent = 'raspi: OFFLINE';
                raspiEl.className = 'err';
            }

            // Alerts
            const alertsDiv = document.getElementById('alerts');
            alertsDiv.innerHTML = data.alerts.map(a =>
                `<div class="alert ${a.level}">${a.message}</div>`
            ).join('');

            // Overall status
            const overall = document.getElementById('overall-status');
            if (data.alerts.some(a => a.level === 'err')) {
                overall.className = 'err'; overall.textContent = 'ERROR';
            } else if (data.alerts.some(a => a.level === 'warn')) {
                overall.className = 'warn'; overall.textContent = 'WARNING';
            } else {
                overall.className = 'ok'; overall.textContent = 'OK';
            }

            // Email
            document.getElementById('email-badge').textContent = data.email.active + ' active';
            setStat('email-sent', data.email.sent_today, data.email.sent_today > 2000 ? 'ok' : '');
            setStat('email-capacity', data.email.capacity, '');
            setStat('email-bounces', data.email.bounces, data.email.bounces > 10 ? 'err' : data.email.bounces > 0 ? 'warn' : 'ok');
            document.getElementById('email-list').innerHTML = data.email.campaigns.map(c => {
                let statusClass = c.status;
                let displayVal = c.sent + '/' + c.limit;
                if (c.stale) {
                    statusClass = 'stale';
                    displayVal = c.sent + '/' + c.limit + ' (stale)';
                }
                return `<div class="list-item"><span class="name">${c.name}</span><span class="${statusClass}">${displayVal}</span></div>`;
            }).join('');

            // Scrapers
            document.getElementById('scraper-badge').textContent = data.scrapers.running + ' running';
            document.getElementById('scraper-badge').className = 'badge' + (data.scrapers.running > 0 ? '' : '');
            setStat('scraper-running', data.scrapers.running, data.scrapers.running > 0 ? 'ok' : '');
            setStat('scraper-today', data.scrapers.completed_today, '');
            setStat('scraper-rows', formatNum(data.scrapers.rows_today), '');
            document.getElementById("scraper-schedule").innerHTML = (data.scrapers.schedule || []).map(s =>
                `<tr class="${s.st_class}"><td>${s.name}</td><td>${s.cron}</td><td>${s.last}</td><td>${s.status}</td><td>${s.rows || "-"}</td></tr>`
            ).join("");

            // Logs
            const logErrors = data.logs.errors_24h;
            document.getElementById('log-badge').textContent = logErrors + ' errors';
            document.getElementById('log-badge').className = 'badge' + (logErrors > 50 ? ' err' : logErrors > 10 ? ' warn' : '');
            setStat('log-size', data.logs.total_size, '');
            setStat('log-files', data.logs.total_files, '');
            setStat('log-errors', logErrors, logErrors > 50 ? 'err' : logErrors > 10 ? 'warn' : 'ok');
            document.getElementById('log-recent').innerHTML = data.logs.recent_errors
                .map(e => `<span class="err">${e}</span>`).join('\\n') || 'No recent errors';

            // Disk
            document.getElementById('disk-list').innerHTML = data.disk.map(d => `
                <div class="list-item">
                    <span class="name">${d.mount}</span>
                    <span class="${d.percent > 90 ? 'err' : d.percent > 80 ? 'warn' : 'ok'}">${d.percent}% (${d.free} free)</span>
                </div>
                <div class="progress"><div class="progress-bar ${d.percent > 90 ? 'err' : d.percent > 80 ? 'warn' : ''}" style="width:${d.percent}%"></div></div>
            `).join('');

            // Docker
            document.getElementById('docker-badge').textContent = data.docker.running + '/' + data.docker.total;
            document.getElementById('docker-list').innerHTML = data.docker.containers.map(c =>
                `<div class="list-item"><span class="name">${c.name}</span><span class="${c.status === 'Up' ? 'ok' : 'err'}">${c.status}</span></div>`
            ).join('');

            // Raspi system
            if (data.raspi && data.raspi.online) {
                document.getElementById('raspi-badge').textContent = 'Online';
                setStat('raspi-cpu', data.raspi.cpu + '%', data.raspi.cpu > 80 ? 'err' : data.raspi.cpu > 60 ? 'warn' : 'ok');
                setStat('raspi-mem', data.raspi.mem + '%', data.raspi.mem > 80 ? 'err' : data.raspi.mem > 60 ? 'warn' : 'ok');
                setStat('raspi-disk', data.raspi.disk + '%', data.raspi.disk > 90 ? 'err' : data.raspi.disk > 80 ? 'warn' : 'ok');
                document.getElementById('raspi-services').innerHTML = data.raspi.services.map(s =>
                    `<div class="list-item"><span class="name">${s.name}</span><span class="${s.status}">${s.info}</span></div>`
                ).join('');
            } else {
                document.getElementById('raspi-badge').textContent = 'Offline';
                document.getElementById('raspi-badge').className = 'badge err';
                setStat('raspi-cpu', '-', '');
                setStat('raspi-mem', '-', '');
                setStat('raspi-disk', '-', '');
                document.getElementById('raspi-services').innerHTML = '<div class="list-item"><span class="name">Unable to connect</span></div>';
            }


            // Brevo Warmup
            if (data.brevo_warmup) {
                const bw = data.brevo_warmup;
                document.getElementById("brevo-badge").textContent = bw.active + " active";
                document.getElementById("brevo-badge").className = "badge raspi" + (bw.paused > 0 ? " warn" : "");
                setStat("brevo-active", bw.active, bw.active > 0 ? "ok" : "");
                setStat("brevo-sent", bw.sent_today, "");
                setStat("brevo-paused", bw.paused, bw.paused > 0 ? "warn" : "");
                document.getElementById("brevo-list").innerHTML = bw.campaigns.map(c => {
                    const statusClass = c.status === "WARMING" ? "ok" : c.status === "PAUSED" ? "warn" : "";
                    return `<div class="list-item"><span class="name">${c.name}</span><span class="${statusClass}">Day ${c.day} | ${c.today}/${c.limit} | ${c.status}</span></div>`;
                }).join("");
            }

            // A2 SMTP Warmup
            if (data.a2_warmup && data.a2_warmup.summary) {
                const a2 = data.a2_warmup;
                document.getElementById('a2-badge').textContent = a2.summary.total_domains + ' domains';
                setStat('a2-sent', a2.summary.total_sent_today, a2.summary.total_sent_today > 0 ? 'ok' : '');
                setStat('a2-remaining', a2.summary.total_remaining, a2.summary.total_remaining > 50 ? 'ok' : a2.summary.total_remaining > 0 ? 'warn' : 'err');
                setStat('a2-limit', a2.summary.total_limit, 'ok');
                if (a2.domains) {
                    document.getElementById('a2-list').innerHTML = a2.domains.map(d => {
                        const pct = d.limit > 0 ? Math.round(d.sent / d.limit * 100) : 0;
                        return `<div class="list-item"><span class="name">${d.domain.replace('.eu','')}</span><span>Day ${d.day} | ${d.sent}/${d.limit} (${pct}%)</span></div>`;
                    }).join('');
                }
            } else {
                document.getElementById('a2-badge').textContent = 'Offline';
                document.getElementById('a2-badge').className = 'badge err';
            }

            // Services
            document.getElementById('services-list').innerHTML = SERVICES.map(s => {
                const isUp = data.services.includes(s.port);
                return `<div class="service ${isUp ? '' : 'down'}"><div class="port">${s.port}</div><div class="name">${s.name}</div></div>`;
            }).join('');
        }

        function setStat(id, value, cls) {
            const el = document.getElementById(id);
            el.querySelector('.value').textContent = value;
            el.className = 'stat ' + cls;
        }

        function formatNum(n) {
            if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
            if (n >= 1000) return (n/1000).toFixed(1) + 'K';
            return n;
        }

        // Initial load and refresh
        fetchData();
        // Fix button handlers
        document.querySelectorAll(".fix-btn").forEach(btn => {
            btn.addEventListener("click", async function() {
                const fixType = this.dataset.fix;
                const resultDiv = document.getElementById("fix-result");
                resultDiv.style.display = "block";
                resultDiv.textContent = "Running " + fixType + "...";
                this.disabled = true;
                
                try {
                    const resp = await fetch("http://192.168.100.20:8089/fix/" + fixType);
                    const data = await resp.json();
                    if (data.success) {
                        resultDiv.innerHTML = `<span style="color:#4ade80">✅ ${data.fix_name || fixType}</span><br><br>${data.output}`;
                    } else {
                        resultDiv.innerHTML = `<span style="color:#ff6b6b">❌ Failed</span><br><br>${data.output}`;
                    }
                } catch (e) {
                    resultDiv.innerHTML = `<span style="color:#ff6b6b">❌ Error: ${e.message}</span>`;
                }
                this.disabled = false;
            });
        });


        // Issues panel
        async function fetchIssues() {
            try {
                const resp = await fetch("/api/issues");
                const data = await resp.json();
                const issues = data.issues || [];
                
                document.getElementById("issues-badge").textContent = issues.length + " issues";
                document.getElementById("issues-badge").className = "badge" + (issues.length > 0 ? " err" : "");
                
                const tbody = document.getElementById("issues-table");
                const noIssues = document.getElementById("no-issues");
                
                if (issues.length === 0) {
                    tbody.innerHTML = "";
                    noIssues.style.display = "block";
                } else {
                    noIssues.style.display = "none";
                    tbody.innerHTML = issues.map(i => {
                        const typeClass = i.severity === "critical" ? "err" : i.severity === "warning" ? "warn" : "";
                        return "<tr style=\"border-bottom:1px solid #222;\"><td style=\"padding:8px;\">" + i.title + "</td><td><span class=\"" + typeClass + "\" style=\"padding:2px 6px;border-radius:3px;background:#1a1a3a;\">" + i.type + "</span></td><td style=\"color:#888;font-size:0.9em;\">" + (i.detail || "-") + "</td><td style=\"text-align:right;\"><button onclick=\"fixIssue(\x27" + i.fix_action + "\x27)\" style=\"padding:4px 10px;background:#4ade80;color:#000;border:none;border-radius:4px;cursor:pointer;font-size:0.8em;\">Fix</button></td></tr>";
                    }).join("");
                }
            } catch (e) {
                console.error("Issues fetch error:", e);
            }
        }
        
        async function fixIssue(action) {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = "...";
            
            try {
                const resp = await fetch("/api/fix/" + action, {method: "POST"});
                const data = await resp.json();
                
                if (data.status === "ok") {
                    btn.textContent = "Done";
                    btn.style.background = "#4ade80";
                    setTimeout(() => fetchIssues(), 1000);
                } else {
                    btn.textContent = "Err";
                    btn.style.background = "#ff6b6b";
                    alert(data.message || "Fix failed");
                }
            } catch (e) {
                btn.textContent = "Err";
                btn.style.background = "#ff6b6b";
                alert("Error: " + e.message);
            }
            
            setTimeout(() => {
                btn.disabled = false;
                btn.textContent = "Fix";
                btn.style.background = "#4ade80";
            }, 3000);
        }
        
        async function runSelfHealer() {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = "Running...";
            
            try {
                const resp = await fetch("/api/fix/run-self-healer", {method: "POST"});
                const data = await resp.json();
                btn.textContent = data.status === "ok" ? "Done!" : "Error";
                setTimeout(() => {
                    btn.textContent = "Run Self-Healer";
                    btn.disabled = false;
                    fetchIssues();
                }, 2000);
            } catch (e) {
                btn.textContent = "Error";
                setTimeout(() => {
                    btn.textContent = "Run Self-Healer";
                    btn.disabled = false;
                }, 2000);
            }
        }
        
        // Fetch issues on load and refresh
        fetchIssues();
        setInterval(fetchIssues, 30000);

        setInterval(fetchData, 15000);
    </script>
</body>
</html>
'''


def get_uptime():
    """Get system uptime."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        return f"{days}d {hours}h"
    except:
        return "?"


def get_disk_usage():
    """Get disk usage for all relevant mounts (/, /home, /mnt/*)."""
    disks = []
    try:
        result = subprocess.run(['df', '-h'], capture_output=True, text=True)
        for line in result.stdout.strip().split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 6:
                mount = parts[5]
                # Include root, home, and ALL /mnt/* mounts dynamically
                if mount in ['/', '/home'] or mount.startswith('/mnt/'):
                    disks.append({
                        'mount': mount,
                        'size': parts[1],
                        'used': parts[2],
                        'free': parts[3],
                        'percent': int(parts[4].replace('%', ''))
                    })
    except:
        pass
    # Sort by mount point
    return sorted(disks, key=lambda x: x['mount'])


def get_docker_status():
    """Get Docker container status (excluding archived Odoo)."""
    containers = []
    # Archived containers to ignore
    ARCHIVED = {'odoo', 'odoo-db'}

    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if '\t' in line:
                name, status = line.split('\t', 1)
                # Skip archived containers
                if name.lower() in ARCHIVED:
                    continue
                containers.append({
                    'name': name,
                    'status': 'Up' if status.startswith('Up') else 'Down'
                })
    except:
        pass

    running = sum(1 for c in containers if c['status'] == 'Up')
    return {'containers': containers, 'running': running, 'total': len(containers)}


def get_services():
    """Get listening ports."""
    ports = []
    try:
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            match = re.search(r':(\d+)\s', line)
            if match:
                ports.append(int(match.group(1)))
    except:
        pass
    return list(set(ports))


def get_raspi_stats():
    """Get raspi system stats via SSH."""
    stats = {
        'online': False,
        'cpu': 0,
        'mem': 0,
        'disk': 0,
        'services': []
    }

    try:
        # Combined command for efficiency
        cmd = '''
cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print int($2)}' 2>/dev/null || echo 0)
mem=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}' 2>/dev/null || echo 0)
disk=$(df / | awk 'NR==2 {print $5}' | tr -d '%' 2>/dev/null || echo 0)
echo "$cpu $mem $disk"
systemctl is-active telegram-bot bounce-webhook 2>/dev/null || true
'''
        result = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=3', '-o', 'StrictHostKeyChecking=no', 'raspi', cmd],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split()
                if len(parts) >= 3:
                    stats['online'] = True
                    stats['cpu'] = int(parts[0]) if parts[0].isdigit() else 0
                    stats['mem'] = int(parts[1]) if parts[1].isdigit() else 0
                    stats['disk'] = int(parts[2]) if parts[2].isdigit() else 0

                # Parse service status
                services = [
                    ('telegram-bot', 'TG Bot'),
                    ('bounce-webhook', 'Bounce WH'),
                ]
                service_lines = lines[1:] if len(lines) > 1 else []
                for i, (svc_name, display) in enumerate(services):
                    status = service_lines[i] if i < len(service_lines) else 'unknown'
                    stats['services'].append({
                        'name': display,
                        'status': 'ok' if status == 'active' else 'err',
                        'info': status
                    })
    except Exception as e:
        pass

    return stats


def get_raspi_campaigns():
    """Fetch campaign status from raspi via SSH with proper date tracking."""
    raspi_campaigns = []
    today = datetime.now().strftime('%Y-%m-%d')

    # Campaigns running on raspi
    campaigns = [
        {'name': 'Poland (raspi)', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND', 'limit': 290},
        {'name': 'Factory (raspi)', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU', 'limit': 290},
        {'name': 'EUFunds-buildjobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_buildjobs'},
        {'name': 'EUFunds-factoryjobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_factoryjobs'},
        {'name': 'EUFunds-warehouse', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_warehouseworkers'},
        {'name': 'CQC-UK (raspi)', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/CQC', 'limit': 100, 'state_file': '.cqc_sender_state.json'},
        {'name': 'EUFunds-mivromania', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_mivromania'},
        {'name': 'EUFunds-mivonline', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_mivromania_online'},
        {'name': 'EUFunds-cifn', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_cifn'},
        {'name': 'EUFunds-expats', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_expatsinromania'},
    ]

    for camp in campaigns:
        sent = 0
        status = 'ok'
        stale = False

        try:
            state_file = camp.get('state_file', 'state.json')
            state_cmd = f'cat {camp["path"]}/{state_file} 2>/dev/null || cat {camp["path"]}/.eufunds_sender_state.json 2>/dev/null || cat {camp["path"]}/state.json 2>/dev/null'
            result = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=3', 'raspi', state_cmd],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                state = json.loads(result.stdout)

                # Check if state has date tracking
                state_date = state.get('date', state.get('last_reset', ''))[:10]

                # Get sent count
                sent = state.get('sent_today', state.get('daily_sent', 0))

                # If state date doesn't match today, mark as stale
                if state_date and state_date != today:
                    stale = True
                    # Don't count stale data toward today's total
                    sent = 0

                # EUFUNDS format with sent_emails dict
                if sent == 0 and 'sent_emails' in state:
                    sender_filter = camp.get('sender')
                    if sender_filter:
                        sent = sum(1 for v in state['sent_emails'].values()
                                   if v.get('date', '')[:10] == today and v.get('sender') == sender_filter)
                    else:
                        sent = sum(1 for v in state['sent_emails'].values() if v.get('date', '')[:10] == today)

                if sent > 0:
                    status = 'ok'
        except Exception:
            status = 'warn'

        raspi_campaigns.append({
            'name': camp['name'],
            'sent': sent,
            'limit': camp['limit'],
            'status': status,
            'stale': stale
        })

    return raspi_campaigns
def get_brevo_warmup_status():
    """Get Brevo warmup status from raspi."""
    try:
        result = subprocess.run(
            ["ssh", "raspi", "/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/brevo_warmup.py status"],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split("\n")
        campaigns = []
        active = 0
        paused = 0
        sent_today = 0
        
        for line in lines:
            if "_BREVO" in line:
                parts = line.split()
                if len(parts) >= 7:
                    name = parts[0]
                    day = parts[1] if parts[1] != "--" else "0"
                    limit = parts[2] if parts[2] != "--" else "0"
                    today = parts[4] if parts[4] != "--" else "0"
                    status = "WARMING" if "WARMING" in line else "PAUSED" if "NOT STARTED" in line else "DONE"
                    
                    campaigns.append({
                        "name": name.replace("_BREVO", ""),
                        "day": day,
                        "limit": limit,
                        "today": today,
                        "status": status
                    })
                    
                    if status == "WARMING":
                        active += 1
                        sent_today += int(today) if today.isdigit() else 0
                    elif status == "PAUSED":
                        paused += 1
        
        return {
            "active": active,
            "paused": paused,
            "sent_today": sent_today,
            "campaigns": campaigns
        }
    except Exception as e:
        return {"active": 0, "paused": 0, "sent_today": 0, "campaigns": [], "error": str(e)}

def get_a2_warmup_status():
    """Fetch A2 SMTP warmup status from raspi."""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "raspi", "/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/a2_status.py --json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        pass
    return {"error": "Cannot fetch A2 status", "domains": [], "summary": {"total_sent_today": 0, "total_remaining": 0, "total_limit": 0}}



def get_email_stats():
    """Get email campaign statistics with proper date tracking."""
    stats = {
        'sent_today': 0,
        'capacity': 2610,  # 9 senders x 290
        'bounces': 0,
        'active': 0,
        'campaigns': []
    }

    # Local raspibig campaigns
    campaigns = [
        ('TRANSPORT (raspibig)', 'TRANSPORT_EU', 290),
        ('TOURISM (raspibig)', 'TOURISM_RO', 290),
        ('HORECA (raspibig)', 'HORECA2026', 290),
        ('NEPAL (raspibig)', 'CIFN_NEPAL', 290),
        ('NORWAY (raspibig)', 'NORWAY', 290),
        ('CAREWORKERS (raspibig)', 'CAREWORKERS', 290),
        ('WAREHOUSE (raspibig)', 'WAREHOUSE_EU', 290)
    ]

    today = datetime.now().strftime('%Y%m%d')

    for display_name, folder_name, limit in campaigns:
        sent = 0
        status = 'ok'
        stale = False

        try:
            # Check for today's sent log
            log_path = EMAIL_DIR / folder_name / 'logs' / f'sent_{today}.log'
            if log_path.exists():
                content = log_path.read_text(errors='ignore')
                sent = content.count('| OK |')
                if sent > 0:
                    stats['active'] += 1
        except:
            pass

        stats['campaigns'].append({
            'name': display_name,
            'sent': sent,
            'limit': limit,
            'status': status,
            'stale': stale
        })
        stats['sent_today'] += sent

    # Add raspi campaigns
    try:
        raspi_camps = get_raspi_campaigns()
        for camp in raspi_camps:
            stats['campaigns'].append(camp)
            if not camp.get('stale', False):
                stats['sent_today'] += camp['sent']
            if camp['sent'] > 0 and not camp.get('stale', False):
                stats['active'] += 1
    except Exception:
        pass

    return stats


def get_scraper_stats():
    """Get scraper statistics from tracker + process detection."""
    stats = {
        "running": 0,
        "completed_today": 0,
        "rows_today": 0,
        "recent": [],
        "schedule": []
    }

    # Load tracker data
    tracker_file = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_runs.json")
    tracker_data = {}
    if tracker_file.exists():
        try:
            tracker_data = json.loads(tracker_file.read_text())
        except:
            pass

    # Running scrapers from process list
    try:
        result = subprocess.run(["pgrep", "-af", "python3.*scraper"], capture_output=True, text=True)
        seen = set()
        for line in result.stdout.split("\n"):
            if not line.strip() or "/bin/bash" in line or "ssh " in line:
                continue
            match = re.search(r"python3?\s+.*?(\w+_?scraper\.py)", line)
            if match and match.group(1) not in seen:
                seen.add(match.group(1))
                stats["running"] += 1
    except:
        pass

    # Process tracker runs
    today = datetime.now().date()
    runs = tracker_data.get("runs", {})
    schedule = tracker_data.get("schedule", {})

    for name, sched in schedule.items():
        run = runs.get(name, {})
        finished = run.get("finished")
        status = run.get("status", "-")
        rows = run.get("rows", 0)

        last_run = "Never"
        if finished:
            try:
                dt = datetime.fromisoformat(finished)
                last_run = dt.strftime("%m-%d %H:%M")
                if dt.date() == today:
                    stats["completed_today"] += 1
                    stats["rows_today"] += rows or 0
            except:
                pass

        st_class = "ok" if status == "ok" else ("warn" if status == "running" else "err" if status == "fail" else "")
        stats["schedule"].append({
            "name": name, "cron": sched, "last": last_run,
            "status": status, "rows": rows, "st_class": st_class
        })

    stats["schedule"].sort(key=lambda x: x["name"])
    return stats


def get_log_stats():
    """Get log statistics."""
    stats = {
        'total_files': 0,
        'total_size': '0 MB',
        'errors_24h': 0,
        'recent_errors': []
    }

    total_bytes = 0
    cutoff = datetime.now() - timedelta(hours=24)
    # Only match actual errors, not warnings
    error_pattern = re.compile(r'.*(error|exception|failed|failure|traceback).*', re.I)

    for log in LOG_DIR.rglob('*.log'):
        try:
            stat = log.stat()
            stats['total_files'] += 1
            total_bytes += stat.st_size

            if datetime.fromtimestamp(stat.st_mtime) > cutoff:
                content = log.read_text(errors='ignore')[-20000:]
                errors = [e for e in error_pattern.findall(content) if 'warning' not in e.lower()]
                stats['errors_24h'] += len(errors)

                for line in content.split('\n')[-50:]:
                    if error_pattern.match(line) and 'warning' not in line.lower():
                        stats['recent_errors'].append(line[:100])
        except:
            pass

    stats['total_size'] = f"{total_bytes / (1024*1024):.1f} MB"
    stats['recent_errors'] = stats['recent_errors'][-5:]

    return stats


def get_failover_status():
    """Get failover system status."""
    state_file = Path('/opt/ACTIVE/INFRA/SYNC_STATE/failover_state.json')
    heartbeat_file = Path('/opt/ACTIVE/INFRA/SYNC_STATE/heartbeat.json')

    status = {
        'mode': 'normal',
        'active': 'raspibig',
        'raspi_ok': False,
        'heartbeat_age': None,
        'last_sync': None,
    }

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            status['mode'] = state.get('mode', 'normal')
            status['active'] = state.get('active', 'raspibig')
        except:
            pass

    if heartbeat_file.exists():
        try:
            hb = json.loads(heartbeat_file.read_text())
            age = time.time() - hb.get('epoch', 0)
            status['heartbeat_age'] = int(age)
        except:
            pass

    result = subprocess.run(['ping', '-c', '1', '-W', '2', '192.168.100.20'],
                          capture_output=True, text=True)
    status['raspi_ok'] = result.returncode == 0

    sync_file = Path('/opt/ACTIVE/INFRA/SYNC_STATE/last_sync.json')
    if sync_file.exists():
        try:
            sync = json.loads(sync_file.read_text())
            status['last_sync'] = sync.get('last_sync', '')[:16]
        except:
            pass

    return status


def get_alerts(disk, docker, logs, email, raspi):
    """Generate alerts based on stats."""
    alerts = []

    # Disk alerts - all mounts
    for d in disk:
        if d['percent'] > 90:
            alerts.append({'level': 'err', 'message': f"Disk {d['mount']} critical: {d['percent']}%"})
        elif d['percent'] > 80:
            alerts.append({'level': 'warn', 'message': f"Disk {d['mount']} high: {d['percent']}%"})

    # Docker alerts (excludes archived containers)
    down = [c for c in docker['containers'] if c['status'] != 'Up']
    if down:
        alerts.append({'level': 'err', 'message': f"Docker down: {', '.join(c['name'] for c in down)}"})

    # Log errors (only real errors, not warnings)
    if logs['errors_24h'] > 100:
        alerts.append({'level': 'err', 'message': f"{logs['errors_24h']} errors in logs (24h)"})
    elif logs['errors_24h'] > 20:
        alerts.append({'level': 'warn', 'message': f"{logs['errors_24h']} errors in logs (24h)"})

    # Raspi alerts
    if not raspi.get('online', False):
        alerts.append({'level': 'err', 'message': "Raspi offline - cannot get stats"})
    else:
        if raspi.get('mem', 0) > 85:
            alerts.append({'level': 'err', 'message': f"Raspi memory critical: {raspi['mem']}%"})
        elif raspi.get('mem', 0) > 70:
            alerts.append({'level': 'warn', 'message': f"Raspi memory high: {raspi['mem']}%"})
        if raspi.get('disk', 0) > 90:
            alerts.append({'level': 'err', 'message': f"Raspi disk critical: {raspi['disk']}%"})

    # Stale email stats alert
    stale_campaigns = [c['name'] for c in email.get('campaigns', []) if c.get('stale', False)]
    if stale_campaigns:
        alerts.append({'level': 'info', 'message': f"Stale stats: {', '.join(stale_campaigns[:3])}..."})

    return alerts


@app.route('/')
def index():
    return render_template_string(TEMPLATE)


@app.route('/api/stats')
def api_stats():
    disk = get_disk_usage()
    docker = get_docker_status()
    logs = get_log_stats()
    email = get_email_stats()
    raspi = get_raspi_stats()

    return jsonify({
        'uptime': get_uptime(),
        'alerts': get_alerts(disk, docker, logs, email, raspi),
        'email': email,
        'scrapers': get_scraper_stats(),
        'logs': logs,
        'disk': disk,
        'docker': docker,
        'services': get_services(),
        'raspi': raspi,
        'failover': get_failover_status(),
        'brevo_warmup': get_brevo_warmup_status(),
        'a2_warmup': get_a2_warmup_status()
    })


@app.route('/api/logs')
def api_logs():
    """Get log files list."""
    logs = []
    for log in LOG_DIR.rglob('*.log'):
        try:
            stat = log.stat()
            logs.append({
                'path': str(log),
                'name': log.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except:
            pass
    return jsonify(sorted(logs, key=lambda x: x['modified'], reverse=True))


@app.route('/api/raspi')
def api_raspi():
    """Get detailed raspi stats."""
    return jsonify(get_raspi_stats())



@app.route("/api/issues")
def api_issues():
    """Get all current issues for dashboard."""
    issues = []
    
    # Check GLOBAL_SEND_LOCK
    lock_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK")
    if lock_file.exists():
        content = lock_file.read_text().strip()
        if content:
            age_hours = (datetime.now().timestamp() - lock_file.stat().st_mtime) / 3600
            issues.append({
                "id": "lock",
                "type": "BLOCKED",
                "title": "GLOBAL_SEND_LOCK active",
                "detail": f"{age_hours:.0f}h old: {content[:40]}",
                "severity": "critical",
                "fix_action": "clear-lock"
            })
    
    # Check scraper recovery status
    try:
        result = subprocess.run(
            ["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/scraper_recovery.py", "json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for s in data.get("scrapers", []):
                if s.get("stale"):
                    issues.append({
                        "id": f"scraper-{s[name]}",
                        "type": "STALE",
                        "title": f"{s[name]} scraper stale",
                        "detail": s.get("message", ""),
                        "severity": "warning",
                        "fix_action": f"restart-scraper/{s[name]}"
                    })
    except Exception as e:
        pass
    
    # Check campaign contacts
    try:
        result = subprocess.run(
            ["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/campaign_replenisher.py", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for c in data.get("campaigns", []):
                if c.get("low"):
                    issues.append({
                        "id": f"campaign-{c[name]}",
                        "type": "LOW",
                        "title": f"{c[name]} low contacts",
                        "detail": f"{c.get(contacts, 0)} contacts",
                        "severity": "warning",
                        "fix_action": f"replenish/{c[name]}"
                    })
    except Exception as e:
        pass
    
    # Check tracker stuck states
    tracker_file = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_runs.json")
    if tracker_file.exists():
        try:
            data = json.loads(tracker_file.read_text())
            now = datetime.now()
            for name, run in data.get("runs", {}).items():
                if run.get("status") == "running":
                    started = datetime.fromisoformat(run["started"])
                    age_hours = (now - started).total_seconds() / 3600
                    if age_hours > 2:
                        issues.append({
                            "id": f"tracker-{name}",
                            "type": "STUCK",
                            "title": f"{name} tracker stuck",
                            "detail": f"Running for {age_hours:.1f}h",
                            "severity": "info",
                            "fix_action": f"reset-tracker/{name}"
                        })
        except Exception:
            pass
    
    return jsonify({"issues": issues, "count": len(issues)})


@app.route("/api/fix/<action>", methods=["POST"])
@app.route("/api/fix/<action>/<param>", methods=["POST"])
def api_fix(action, param=None):
    """Execute a fix action."""
    result = {"action": action, "param": param, "status": "error"}
    
    try:
        if action == "clear-lock":
            lock_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK")
            if lock_file.exists():
                backup = lock_file.with_suffix(".cleared")
                lock_file.rename(backup)
                result["status"] = "ok"
                result["message"] = "Lock cleared"
            else:
                result["status"] = "ok"
                result["message"] = "Lock already clear"
        
        elif action == "restart-scraper" and param:
            proc = subprocess.run(
                ["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/scraper_recovery.py", "restart", param],
                capture_output=True, text=True, timeout=30
            )
            result["status"] = "ok" if proc.returncode == 0 else "error"
            result["message"] = proc.stdout.strip() or proc.stderr.strip()
        
        elif action == "replenish" and param:
            proc = subprocess.run(
                ["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/campaign_replenisher.py", "--feed", param],
                capture_output=True, text=True, timeout=60
            )
            result["status"] = "ok" if proc.returncode == 0 else "error"
            result["message"] = proc.stdout.strip()[:200]
        
        elif action == "reset-tracker" and param:
            tracker_file = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_runs.json")
            if tracker_file.exists():
                data = json.loads(tracker_file.read_text())
                if param in data.get("runs", {}):
                    data["runs"][param]["status"] = "reset"
                    data["runs"][param]["finished"] = datetime.now().isoformat()
                    tracker_file.write_text(json.dumps(data, indent=2))
                    result["status"] = "ok"
                    result["message"] = f"Tracker {param} reset"
                else:
                    result["message"] = f"Tracker {param} not found"
            else:
                result["message"] = "Tracker file not found"
        
        elif action == "run-self-healer":
            proc = subprocess.run(
                ["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/self_healer.py", "--json"],
                capture_output=True, text=True, timeout=30
            )
            result["status"] = "ok" if proc.returncode == 0 else "error"
            result["message"] = proc.stdout.strip()[:300]
        
        else:
            result["message"] = f"Unknown action: {action}"
    
    except subprocess.TimeoutExpired:
        result["message"] = "Timeout"
    except Exception as e:
        result["message"] = str(e)
    
    return jsonify(result)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Unified Dashboard v3.0')
    parser.add_argument('--port', type=int, default=8085, help='Port to run on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    args = parser.parse_args()

    print(f"Starting Unified Dashboard v3.0 on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


# ==================== ISSUES & FIX API ====================


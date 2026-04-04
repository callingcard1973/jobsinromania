#!/usr/bin/env python3
# Telegram Alert Notifier Service
import requests
import json
import sys
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration - use placeholder values
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"
TELEGRAM_API_URL = "https://api.telegram.org"

def send_telegram_message(message, parse_mode="HTML"):
    """Send message to Telegram"""
    try:
        url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            app.logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
        return True
    except Exception as e:
        app.logger.error(f"Error sending Telegram message: {e}")
        return False

def format_alert_message(alert):
    """Format alert data into readable Telegram message"""
    status = alert.get('status', 'unknown')
    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})

    severity = labels.get('severity', 'unknown').upper()
    alertname = labels.get('alertname', 'Unknown Alert')
    instance = labels.get('instance', 'N/A')
    summary = annotations.get('summary', 'No summary')
    description = annotations.get('description', 'No description')

    # Icon based on status and severity
    if status == 'firing':
        icon = '🚨' if severity == 'CRITICAL' else '⚠️'
    else:
        icon = '✅'

    message = f"{icon} <b>{status.upper()}</b>\n\n"
    message += f"<b>Alert:</b> {alertname}\n"
    message += f"<b>Severity:</b> {severity}\n"
    message += f"<b>Instance:</b> {instance}\n"
    message += f"<b>Summary:</b> {summary}\n"
    message += f"<b>Description:</b> {description}\n"
    message += f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return message

@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive alerts from Alertmanager and forward to Telegram"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "No JSON data"}), 400

        alerts = data.get('alerts', [])
        group_labels = data.get('groupLabels', {})

        if not alerts:
            return jsonify({"status": "ok", "message": "No alerts"}), 200

        # Group alerts by commonality
        for alert in alerts:
            message = format_alert_message(alert)
            success = send_telegram_message(message)
            if success:
                app.logger.info(f"Alert sent: {alert.get('labels', {}).get('alertname', 'Unknown')}")
            else:
                app.logger.warning(f"Failed to send alert: {alert.get('labels', {}).get('alertname', 'Unknown')}")

        return jsonify({"status": "ok", "message": f"Processed {len(alerts)} alert(s)"}), 200

    except Exception as e:
        app.logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.logger.info("Starting Telegram Alert Notifier")
    app.run(host='0.0.0.0', port=8081, debug=False)

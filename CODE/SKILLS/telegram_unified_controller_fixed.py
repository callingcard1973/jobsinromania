#!/usr/bin/env python3
"""
Telegram Unified Controller - Single interface for all raspibig operations
Connects to PICOCLAW, spam learning, email processing, and system commands

Usage:
    /status - System status overview
    /spam_score <text> - Get spam score
    /enrich <company> <country> - Enrich company data
    /process_emails - Trigger email processing
    /campaign <action> - Campaign operations
    /help - Show all commands

Part of raspibig automation system
"""

import os
import sys
import json
import re
import asyncio
import sqlite3
import stat
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PICOCLAW_URL = "http://localhost:5055"
LM_STUDIO_URL = "http://localhost:1234"
SPAM_DB = Path("/opt/ACTIVE/INFRA/SPAM/spam_learning.db")
UNIFIED_LEARNING_DB = Path("/opt/ACTIVE/INFRA/SPAM/unified_learning.db")

# Multi-LLM Configuration
# Local LM Studio models (default)
LOCAL_MODELS = {
    "lfm2.5-1.2b-instruct": "Local - Fast general purpose",
    "granite-4.0-h-micro": "Local - Reasoning",
    "exaone-4.0-1.2b": "Local - Multilingual",
    "qwen2.5-coder-1.5b-instruct": "Local - Code/Automation",
    "spam-classifier-3b-v1": "Local - Spam detection",
}

# OpenCode configuration
OPENCODE_URL = os.environ.get("OPENCODE_URL", "http://localhost:36000")
OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY", "")

# Claude configuration (set ANTHROPIC_API_KEY env var)
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_URL = os.environ.get("CLAUDE_URL", "https://api.anthropic.com/v1/messages")

# z.ai configuration
ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "")
ZAI_URL = os.environ.get("ZAI_URL", "https://api.z.ai/v1/chat/completions")

# Logging & safety
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("raspibig.bot")

# Available LLM providers
LLM_PROVIDERS = {
    "local": "LM Studio (local)",
    "opencode": "OpenCode + z.ai",
    "z.ai": "z.ai (cloud)",
    "claude": "Claude (API)",
}

HELP_TEXT = """
🤖 *Raspibig Unified Controller*

Available Commands:

*System Status*
/status - Overview of all systems
/services - Check running services
/stats - Detailed statistics
/sh <command> - Run shell command

*Spam & Email*
/spam - Fast spam check (keyword-based)
/spam_score <text> - LLM spam score (0-100)
/intent <text> - Classify reply intent
/replies - Show today's urgent replies
/spam_learn <email> <flag|allow|block> - Teach the system
/learned_spam - Show recently learned
/blocked - Show blocked senders
/process_emails - Trigger email processing

*Learning & Analytics*
/learning_stats - Unified learning statistics
/response_patterns - Show email response patterns
/learning_export - Export learning data

*System Integration*
/bridge_status - OpenCode + PICOCLAW bridge status
/bridge_history - Bridge task history
/bridge_test - Test integration

*z.ai Hub - Central AI Coordination*
/hub_status - z.ai Hub status overview
/hub_test <question> - Test hub routing
/hub_multi <question> - Multi-provider aggregation
/hub_task <task> - Test specific task type

*Data & Enrichment*
/enrich <company> <country> - Enrich company data
/lead <company>,<country> - Fast lead scoring
/campaign status - Show campaign status
/campaign stats - Campaign statistics

*AI & LLM*
/llm <question> - Query local LLM
/ask <question> - Ask LLM (alias)
/llm_local <model> <question> - Query specific local model
/llm_opencode <question> - Query via OpenCode
/llm_zai <question> - Query z.ai cloud
/llm_claude <question> - Query Claude (if API key set)
/models - List available models
/skills - List available PICOCLAW skills

*Subject Lines*
/subject <topic> - Generate subject line variations

*Business Intelligence Dashboard*
/bi_dashboard - Show comprehensive BI dashboard
/bi_collect - Manually collect BI data
/bi_report - Export BI metrics report
/bi_kpis - Show detailed business KPIs

*Logs*
/logs <service> - Get recent logs (default: 50 lines)

Examples:
/spam "Get rich quick!!!"
/intent "Yes I'm interested in the position"
/enrich "Mercedes Benz" Germany
/lead "Volkswagen,Germany"
/subject "Warehouse jobs in Germany"
/sh df -h
/llm Write a professional follow-up email
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Raspibig Unified Controller\n\nType /help for available commands.", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = "📊 *System Status*\n\n"
    
    try:
        r = requests.get(f"{PICOCLAW_URL}/status", timeout=5)
        if r.status_code == 200:
            data = r.json()
            status_msg += f"✅ PICOCLAW: Running\n"
            status_msg += f"   Model: {data.get('llm_model', 'N/A')}\n"
            status_msg += f"   Queue: {data.get('queue_size', 0)}\n"
        else:
            status_msg += f"❌ PICOCLAW: Error {r.status_code}\n"
    except:
        status_msg += f"❌ PICOCLAW: Not responding\n"
    
    try:
        r = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
        if r.status_code == 200:
            models = r.json().get("data", [])
            status_msg += f"\n✅ LM Studio: Running ({len(models)} models)\n"
    except Exception as e:
        status_msg += f"\n❌ LM Studio: Not responding\n"
    
    try:
        if SPAM_DB.exists():
            conn = sqlite3.connect(SPAM_DB)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM spam_decisions")
            count = cur.fetchone()[0]
            status_msg += f"\n✅ Spam Learning: {count} senders learned\n"
            conn.close()
        else:
            status_msg += f"\n⚠️ Spam Learning: DB not found\n"
    except Exception as e:
        status_msg += f"\n❌ Spam Learning: Error\n"
    
    await update.message.reply_text(status_msg, parse_mode="Markdown")

async def spam_score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /spam_score <text to check>")
        return
    
    text = " ".join(context.args)
    
    try:
        r = requests.post(f"{PICOCLAW_URL}/task", json={"task_type": "spam_score", "payload": {"text": text}}, timeout=30)
        if r.status_code == 201:
            task_id = r.json().get("task_id")
            for _ in range(10):
                await asyncio.sleep(1)
                result = requests.get(f"{PICOCLAW_URL}/task/{task_id}")
                if result.status_code == 200:
                    task_data = result.json()
                    if task_data.get("status") == "completed":
                        score = task_data.get("result", {}).get("score", "N/A")
                        reason = task_data.get("result", {}).get("reason", "")
                        emoji = "✅" if int(score) < 30 else "⚠️" if int(score) < 70 else "🚫"
                        await update.message.reply_text(f"{emoji} Spam Score: *{score}*/100\n\n{reason}", parse_mode="Markdown")
                        return
    except Exception as e:
        pass
    
    score = calculate_simple_spam_score(text)
    await update.message.reply_text(f"⚡ Spam Score: *{score}*/100 (fallback)", parse_mode="Markdown")

def calculate_simple_spam_score(text: str) -> int:
    text_lower = text.lower()
    score = 20
    spam_words = ["free", "winner", "urgent", "click", "money", "rich", "guarantee", "act now", "limited time", "congratulations", "prize", "lottery", "viagra", "pills", "discount", "offer", "deal"]
    for word in spam_words:
        if word in text_lower:
            score += 15
    if "!" in text:
        score += 10
    if text.isupper():
        score += 20
    if len(text) < 20:
        score += 10
    return min(score, 100)

async def spam_learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /spam_learn <email> <flag|allow|block>")
        return
    
    email = context.args[0].lower()
    action = context.args[1].lower()
    
    if action not in ["flag", "allow", "block"]:
        await update.message.reply_text("Action must be: flag, allow, or block")
        return
    
    try:
        conn = sqlite3.connect(SPAM_DB)
        cur = conn.cursor()
        
        if action == "block":
            cur.execute("INSERT OR REPLACE INTO spam_decisions (sender_email, first_seen, last_seen, is_blocked, block_reason) VALUES (?, datetime('now'), datetime('now'), TRUE, 'Manual block')", (email,))
        elif action == "allow":
            cur.execute("INSERT OR REPLACE INTO spam_decisions (sender_email, first_seen, last_seen, is_blocked, times_corrected) VALUES (?, datetime('now'), datetime('now'), FALSE, 1)", (email,))
        else:
            cur.execute("INSERT OR REPLACE INTO spam_decisions (sender_email, first_seen, last_seen, times_flagged) VALUES (?, datetime('now'), datetime('now'), 1)", (email,))
        
        conn.commit()
        conn.close()
        
        emoji = "🚫" if action == "block" else "✅" if action == "allow" else "⚠️"
        await update.message.reply_text(f"{emoji} Learned: {email} → {action}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def learned_spam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = sqlite3.connect(SPAM_DB)
        cur = conn.cursor()
        cur.execute("SELECT sender_email, last_seen, times_flagged, times_corrected, is_blocked FROM spam_decisions ORDER BY last_seen DESC LIMIT 20")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            await update.message.reply_text("No learned senders yet.")
            return
        
        msg = "📚 *Recently Learned Senders*\n\n"
        for row in rows:
            email, last_seen, flagged, corrected, blocked = row
            status = "🚫" if blocked else "⚠️" if flagged > corrected else "✅"
            msg += f"{status} {email}\n   Flagged: {flagged}, Corrected: {corrected}\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = sqlite3.connect(SPAM_DB)
        cur = conn.cursor()
        cur.execute("SELECT sender_email, block_reason, last_seen FROM spam_decisions WHERE is_blocked = TRUE ORDER BY last_seen DESC LIMIT 30")
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            await update.message.reply_text("No blocked senders.")
            return
        
        msg = "🚫 *Blocked Senders*\n\n"
        for row in rows:
            email, reason, last_seen = row
            msg += f"• {email}\n   {reason or 'Manual block'}\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def learning_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show unified learning statistics"""
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/unified_learning_database.py", "--stats"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            # Extract JSON from the output
            output = result.stdout
            stats_start = output.find('{')
            if stats_start != -1:
                stats_json = output[stats_start:]
                stats = json.loads(stats_json)
                
                # Format for Telegram
                message = "📊 *Unified Learning Statistics*\n\n"
                message += f"📈 Total Entries: {stats.get('total_entries', 0)}\n"
                message += f"📅 Last 7 Days: {stats.get('last_7_days', 0)}\n\n"
                
                # By type
                by_type = stats.get('by_type', {})
                if by_type:
                    message += "📂 *By Type:*\n"
                    for learning_type, count in by_type.items():
                        message += f"• {learning_type.title()}: {count}\n"
                
                # Response intents
                intents = stats.get('response_intents', {})
                if intents:
                    message += "\n🎯 *Response Intents:*\n"
                    for intent, count in intents.items():
                        message += f"• {intent.replace('_', ' ').title()}: {count}\n"
                
                # Spam accuracy
                spam_accuracy = stats.get('spam_accuracy', 0)
                if spam_accuracy > 0:
                    message += f"\n🛡️ Spam Accuracy: {spam_accuracy:.1%}\n"
                
                await update.message.reply_text(message, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text("❌ Error parsing learning stats")
        else:
            await update.message.reply_text(f"❌ Error getting stats: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def learning_export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export learning data"""
    try:
        await update.message.reply_text("📤 Exporting learning data...")
        
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/unified_learning_database.py", "--export"],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            export_path = result.stdout.strip().split("Exported to: ")[-1]
            await update.message.reply_text(
                f"✅ Learning data exported to:\n`{export_path}`",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Export failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def response_patterns_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show response patterns by intent"""
    try:
        # Get learning stats which include response intents
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/unified_learning_database.py", "--stats"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout
            stats_start = output.find('{')
            if stats_start != -1:
                stats_json = output[stats_start:]
                stats = json.loads(stats_json)
                
                intents = stats.get('response_intents', {})
                if intents:
                    message = "🎯 *Email Response Patterns*\n\n"
                    total = sum(intents.values())
                    message += f"📧 Total Patterns: {total}\n\n"
                    
                    # Sort by count
                    sorted_intents = sorted(intents.items(), key=lambda x: x[1], reverse=True)
                    
                    for intent, count in sorted_intents:
                        percentage = (count / total * 100) if total > 0 else 0
                        intent_name = intent.replace('_', ' ').title()
                        bar_length = int(percentage / 10)  # Simple bar chart
                        bar = "█" * bar_length + "░" * (10 - bar_length)
                        message += f"{intent_name}: {count} ({percentage:.0f}%)\n"
                        message += f"`{bar}`\n\n"
                    
                    await update.message.reply_text(message, parse_mode='MarkdownV2')
                else:
                    await update.message.reply_text("📭 No response patterns found yet")
            else:
                await update.message.reply_text("❌ Error parsing response patterns")
        else:
            await update.message.reply_text(f"❌ Error: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def enrich_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /enrich <company> <country>")
        return
    
    company = " ".join(context.args[:-1])
    country = context.args[-1]
    
    await update.message.reply_text(f"🔍 Enriching: {company} ({country})...")
    
    try:
        r = requests.post(f"{PICOCLAW_URL}/task", json={"task_type": "lead_enrich", "payload": {"company": company, "country": country}}, timeout=30)
        if r.status_code == 201:
            task_id = r.json().get("task_id")
            for _ in range(15):
                await asyncio.sleep(2)
                result = requests.get(f"{PICOCLAW_URL}/task/{task_id}")
                if result.status_code == 200:
                    task_data = result.json()
                    if task_data.get("status") == "completed":
                        data = task_data.get("result", {})
                        await update.message.reply_text(f"✅ *Enrichment Result*\n\nCompany: {company}\nCountry: {country}\nScore: {data.get('score', 'N/A')}\nIndustry: {data.get('industry', 'N/A')}", parse_mode="Markdown")
                        return
            await update.message.reply_text("⏳ Processing timed out")
        else:
            await update.message.reply_text(f"❌ Error: {r.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def bridge_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show OpenCode + PICOCLAW bridge status"""
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/opencode_picoclaw_bridge.py", "--status"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            # Extract JSON from the output
            output = result.stdout
            status_start = output.find('{')
            if status_start != -1:
                status_json = output[status_start:]
                status = json.loads(status_json)
                
                # Format for Telegram
                message = "🌉 *OpenCode + PICOCLAW Bridge Status*\n\n"
                
                # System availability
                message += "🔧 *System Status:*\n"
                message += f"• PICOCLAW: {'✅ Available' if status.get('picoclaw_available') else '❌ Not Available'}\n"
                message += f"• OpenCode: {'✅ Available' if status.get('opencode_available') else '❌ Not Available'}\n\n"
                
                # Flow statistics
                flow_stats = status.get('flow_statistics', {})
                if flow_stats:
                    message += "🔄 *Task Flow:*\n"
                    for flow, count in flow_stats.items():
                        message += f"• {flow}: {count} tasks\n"
                    message += "\n"
                
                # Status breakdown
                status_breakdown = status.get('status_breakdown', {})
                if status_breakdown:
                    message += "📊 *Task Status:*\n"
                    for status_name, count in status_breakdown.items():
                        message += f"• {status_name.title()}: {count}\n"
                    message += "\n"
                
                # Activity info
                active_sessions = status.get('active_sessions', 0)
                message += f"🏃 *Active Sessions: {active_sessions}*\n"
                
                await update.message.reply_text(message, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text("❌ Error parsing bridge status")
        else:
            await update.message.reply_text(f"❌ Error getting bridge status: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def bridge_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bridge task history"""
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/opencode_picoclaw_bridge.py", "--history"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 2:  # Skip header line
                message = "📋 *Bridge Task History*\n\n"
                
                # Show last 10 tasks
                for line in lines[2:12]:  # Skip header, limit to 10
                    if line.strip():
                        message += f"{line}\n"
                
                await update.message.reply_text(message, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text("📭 No bridge tasks yet")
        else:
            await update.message.reply_text(f"❌ Error getting history: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def bridge_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test bridge integration with spam scoring"""
    if not context.args:
        await update.message.reply_text("Usage: /bridge_test <text to test>")
        return
    
    test_text = " ".join(context.args)
    await update.message.reply_text(f"🧪 Testing bridge with:\n`{test_text}`", parse_mode='MarkdownV2')
    
    try:
        # Test the bridge with spam scoring
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/opencode_picoclaw_bridge.py", "--bridge-spam", test_text],
            capture_output=True, text=True, timeout=90
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ *Bridge Test Completed*\n\n{result.stdout}",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Bridge test failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def hub_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show z.ai Hub status"""
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/zai_hub.py", "--status"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            # Extract JSON from the output
            output = result.stdout
            status_start = output.find('{')
            if status_start != -1:
                status_json = output[status_start:]
                status = json.loads(status_json)
                
                # Format for Telegram
                message = "🌐 *z.ai Hub Status*\n\n"
                
                # Provider availability
                providers = status.get('providers', {})
                message += "🔧 *AI Providers:*\n"
                for provider_name, provider_info in providers.items():
                    status_emoji = "✅" if provider_info.get('available') else "❌"
                    capabilities = ", ".join(provider_info.get('capabilities', [])[:2])  # Show first 2 capabilities
                    priority = provider_info.get('priority', 0)
                    message += f"• {status_emoji} {provider_name.title()} (P{priority}) - {capabilities}\n"
                
                # Recent requests
                recent_requests = status.get('recent_requests', [])
                if recent_requests:
                    message += f"\n📋 *Recent Requests: {len(recent_requests)}*\n"
                    for req in recent_requests[:3]:  # Show last 3
                        req_status = "✅" if req.get('success') else "❌"
                        message += f"• {req_status} {req.get('task_type', 'unknown')} → {req.get('provider', 'unknown')}\n"
                
                await update.message.reply_text(message, parse_mode='MarkdownV2')
            else:
                await update.message.reply_text("❌ Error parsing hub status")
        else:
            await update.message.reply_text(f"❌ Error getting hub status: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def campaign_generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate AI campaign using Campaign Auto-Generator"""
    if not context.args:
        await update.message.reply_text("Usage: /campaign_generate <industry>,<country1>,<country2>,...\nExample: /campaign_generate HORECA,Poland,Germany")
        return
    
    params = " ".join(context.args)
    await update.message.reply_text(f"🤖 Generating AI campaign for: {params}")
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/campaign_auto_generator.py", "--generate", params],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ *Campaign Generated*\n\n{result.stdout}",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Campaign generation failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def campaign_deploy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deploy AI-generated campaign"""
    if not context.args:
        await update.message.reply_text("Usage: /campaign_deploy <campaign_id>")
        return
    
    campaign_id = context.args[0]
    await update.message.reply_text(f"🚀 Deploying campaign: {campaign_id}")
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/campaign_auto_generator.py", "--deploy", campaign_id],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ *Campaign Deployed*\n\n{result.stdout}",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Campaign deployment failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get email summaries"""
    priority = context.args[0] if context.args else None
    category = context.args[1] if len(context.args) > 1 else None
    
    await update.message.reply_text("📧 Processing email summaries...")
    
    try:
        cmd = ["python3", "/opt/ACTIVE/INFRA/SPAM/email_summarizer.py", "--summaries"]
        if priority:
            cmd.append(priority)
        if category:
            cmd.append(category)
        
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=90
        )
        
        if result.returncode == 0:
            # Format the output for Telegram
            output = result.stdout
            if len(output) > 4000:  # Telegram limit
                output = output[:4000] + "...(truncated)"
            
            await update.message.reply_text(
                f"📋 *Email Summaries*\n\n```{output}```",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Error getting email summaries: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def email_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get pending email actions"""
    await update.message.reply_text("📝 Getting pending email actions...")
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/email_summarizer.py", "--actions"],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            output = result.stdout
            if len(output) > 4000:
                output = output[:4000] + "...(truncated)"
            
            await update.message.reply_text(
                f"📝 *Pending Email Actions*\n\n```{output}```",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Error getting email actions: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def complete_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Complete a pending email action"""
    if not context.args:
        await update.message.reply_text("Usage: /complete_action <action_id>")
        return
    
    action_id = context.args[0]
    await update.message.reply_text(f"✅ Completing action #{action_id}")
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SPAM/email_summarizer.py", "--complete", action_id],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            await update.message.reply_text(f"✅ Action #{action_id} completed")
        else:
            await update.message.reply_text(f"❌ Failed to complete action: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def hub_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test z.ai Hub with a question"""
    if not context.args:
        await update.message.reply_text("Usage: /hub_test <your question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text(f"🌐 Testing z.ai Hub with:\n`{question}`", parse_mode='MarkdownV2')
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/zai_hub.py", "--test", question],
            capture_output=True, text=True, timeout=90
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ *Hub Test Completed*\n\n{result.stdout}",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Hub test failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def hub_multi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test z.ai Hub multi-provider aggregation"""
    if not context.args:
        await update.message.reply_text("Usage: /hub_multi <your question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text(f"🌐 Testing multi-provider aggregation:\n`{question}`", parse_mode='MarkdownV2')
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/zai_hub.py", "--multi", question],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            # Format the multi-provider result nicely
            output = result.stdout
            await update.message.reply_text(
                f"🔄 *Multi-Provider Analysis*\n\n```\n{output[-3000:]}```",  # Last 3000 chars to avoid long messages
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Multi-test failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def hub_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test z.ai Hub with specific task type"""
    if not context.args:
        await update.message.reply_text("Usage: /hub_task <task_type>")
        return
    
    task_type = context.args[0]
    prompt = f"Test prompt for {task_type}"
    
    await update.message.reply_text(f"🌐 Testing z.ai Hub with task:\n`{task_type}`", parse_mode='MarkdownV2')
    
    try:
        result = subprocess.run(
            ["python3", "/opt/ACTIVE/INFRA/SKILLS/zai_hub.py", "--test-task", task_type],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ *Task Test Completed*\n\n{result.stdout}",
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(f"❌ Task test failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def llm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /llm <your question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text(f"🤔 Thinking...")
    
    try:
        r = requests.post(f"{LM_STUDIO_URL}/v1/chat/completions", json={"model": "lfm2.5-1.2b-instruct", "messages": [{"role": "user", "content": question}], "temperature": 0.7, "max_tokens": 500}, timeout=60)
        if r.status_code == 200:
            response = r.json().get("choices", [{}])[0].get("message", {}).get("content", "No response")
            if len(response) > 3000:
                response = response[:3000] + "\n\n...(truncated)"
            await update.message.reply_text(f"💡 *Response*\n\n{response}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ LLM Error: {r.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{PICOCLAW_URL}/task-types", timeout=5)
        if r.status_code == 200:
            data = r.json()
            skills = data.get("task_types", {})
            msg = "🛠️ *Available PICOCLAW Skills*\n\n"
            for i, (skill, schema) in enumerate(list(skills.items())[:15], 1):
                msg += f"{i}. `{skill}`\n"
            if len(skills) > 15:
                msg += f"\n...and {len(skills) - 15} more"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Could not fetch skills")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /campaign <status|stats>")
        return
    
    action = context.args[0].lower()
    
    if action == "status":
        state_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_state.json")
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
            msg = f"📬 *Campaign Status*\n\nRunning: {state.get('running', False)}\nSent today: {state.get('sent_today', 0)}\nLast send: {state.get('last_send', 'N/A')}"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Campaign state file not found")
    elif action == "stats":
        log_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log.csv")
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
            total = len(lines) - 1
            await update.message.reply_text(f"📊 *Campaign Stats*\n\nTotal sends: {total}")
        else:
            await update.message.reply_text("⚠️ No send log found")
    else:
        await update.message.reply_text("Unknown action. Use: status or stats")

async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🔧 *Services Status*\n\n"
    services = [("PICOCLAW", "http://localhost:5055/health"), ("LM Studio", "http://localhost:1234/v1/models")]
    for name, url in services:
        try:
            r = requests.get(url, timeout=3)
            msg += f"✅ {name}: Running\n"
        except:
            msg += f"❌ {name}: Not responding\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = context.args[0] if context.args else "email"
    lines = int(context.args[1]) if len(context.args) > 1 else 30
    log_dir = Path("/opt/ACTIVE/INFRA/LOGS")
    log_files = {"email": "smart_email_processor.log", "spam": "spam_learning.log", "campaign": "campaign_orchestrator.log"}
    log_file = log_dir / log_files.get(service, "smart_email_processor.log")
    
    if not log_file.exists():
        await update.message.reply_text(f"⚠️ No logs found for {service}")
        return
    
    try:
        with open(log_file) as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:]
        log_text = "".join(recent)
        if len(log_text) > 3000:
            log_text = "...\n" + log_text[-2800:]
        await update.message.reply_text(f"📝 *Recent Logs ({service})*\n\n```\n{log_text}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📈 *System Statistics*\n\n"
    try:
        log_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log.csv")
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
            total = len(lines) - 1
            msg += f"📧 Total Emails Sent: {total}\n"
    except:
        pass
    try:
        if SPAM_DB.exists():
            conn = sqlite3.connect(SPAM_DB)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM spam_decisions WHERE is_blocked = TRUE")
            blocked = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM spam_decisions")
            total = cur.fetchone()[0]
            conn.close()
            msg += f"🚫 Blocked Senders: {blocked}\n📚 Total Learned: {total}\n"
    except:
        pass
    try:
        r = requests.get(f"{PICOCLAW_URL}/status", timeout=5)
        if r.status_code == 200:
            data = r.json()
            msg += f"⏳ PICOCLAW Queue: {data.get('queue_size', 0)}\n"
    except:
        pass
    await update.message.reply_text(msg, parse_mode="Markdown")

async def process_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 Email processing must be triggered via systemd:\n`sudo systemctl restart llm-email-processor`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language messages - use existing LLM-based handler"""
    user_message = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    
    # Import the existing handle_natural from telegram_llm_bot
    # This uses LLM to interpret and execute shell commands
    sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
    try:
        from telegram_llm_bot import handle_natural
        result = handle_natural(user_message, chat_id)
        
        # Handle_natural returns HTML-formatted messages
        await update.message.reply_text(result, parse_mode="HTML")
        return
    except ImportError as e:
        pass
    except Exception as e:
        pass
    
    # Fallback if the import fails - use simple pattern matching
    lower_msg = user_message.lower()
    
    # Simple greetings
    greetings = ["hello", "hi", "hey", "buna", "salut"]
    if any(g in lower_msg for g in greetings):
        await update.message.reply_text(
            "👋 Hello! Try things like:\n"
            "• \"How's the system?\"\n"
            "• \"Show me the stats\"\n"
            "• \"Check spam for Free money!!!\"\n"
            "• /help for commands",
            parse_mode="Markdown"
        )
        return
    
    # Try simple spam check
    if any(w in lower_msg for w in ["spam", "check"]):
        text_match = re.search(r'(?:spam|check)[:\s]+(.+)', lower_msg)
        if text_match:
            text_to_check = text_match.group(1).strip()
            context.args = text_to_check.split()
            await spam_score_command(update, context)
            return
    
    # Try simple enrich
    if any(w in lower_msg for w in ["enrich", "company"]):
        words = user_message.split()
        if len(words) >= 2:
            # Assume last word is country, rest is company
            country = words[-1].strip(".,?!")
            company = " ".join(words[1:-1]) if len(words) > 2 else words[0]
            if company.lower() not in ["enrich", "company", "info"]:
                context.args = [company, country]
                await enrich_command(update, context)
                return
    
    # Fallback to LLM query
    context.args = user_message.split()
    await llm_command(update, context)

# ============== ADDITIONAL COMMANDS FROM OLD telegram_llm_bot ==============

async def spam_fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fast spam check using keyword-based detection"""
    if not context.args:
        await update.message.reply_text("Usage: /spam <text to check>")
        return
    
    text = " ".join(context.args)
    
    try:
        sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
        from fast_tools import spam_fast
        result = spam_fast(text)
        emoji = "🚨" if result["spam"] else "✅"
        await update.message.reply_text(
            f"{emoji} <b>Spam:</b> {result['spam']}\n<b>Confidence:</b> {result['confidence']}\n<b>Reason:</b> {result['reason']}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def intent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Classify reply intent"""
    if not context.args:
        await update.message.reply_text("Usage: /intent <reply text>")
        return
    
    text = " ".join(context.args)
    
    try:
        sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
        from fast_tools import intent_fast
        result = intent_fast(text)
        emoji = {"interested": "🎯", "question": "❓", "auto_reply": "🤖", "not_interested": "👎", "unsubscribe": "🚫"}.get(result["intent"], "📧")
        await update.message.reply_text(
            f"{emoji} <b>Intent:</b> {result['intent']}\n<b>Sentiment:</b> {result['sentiment']}\n<b>Action:</b> {result['action']}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def lead_fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fast lead scoring"""
    if not context.args:
        await update.message.reply_text("Usage: /lead <company>,<country>")
        return
    
    args_text = " ".join(context.args)
    parts = args_text.split(",")
    company = parts[0].strip()
    country = parts[1].strip() if len(parts) > 1 else ""
    
    try:
        sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
        from fast_tools import lead_fast
        result = lead_fast(company, country)
        emoji = "🔥" if result["priority"] == "high" else "👍" if result["priority"] == "medium" else "👎"
        await update.message.reply_text(
            f"{emoji} <b>Score:</b> {result['score']}/10\n<b>Priority:</b> {result['priority']}\n<b>Reason:</b> {result['reason']}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def subject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate subject line variations"""
    if not context.args:
        await update.message.reply_text("Usage: /subject <topic>")
        return
    
    topic = " ".join(context.args)
    
    try:
        sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
        from fast_tools import subject_fast
        subjects = subject_fast(topic)
        msg = "<b>Subject variations:</b>\n" + "\n".join(f"• {s}" for s in subjects)
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def replies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's replies"""
    try:
        sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
        from email_fetcher import EmailFetcher
        fetcher = EmailFetcher()
        results = fetcher.analyze_replies(days=1)
        
        msg = f"<b>Today's Replies:</b> {results['total']}\n\n"
        for intent, count in sorted(results['by_intent'].items(), key=lambda x: -x[1]):
            msg += f"• {intent}: {count}\n"
        
        if results['urgent']:
            msg += f"\n<b>🚨 Urgent ({len(results['urgent'])}):</b>\n"
            for r in results['urgent'][:5]:
                msg += f"• {r['email'][:30]}\n"
        
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run shell command"""
    if not context.args:
        await update.message.reply_text("Usage: /sh <command>")
        return
    
    import subprocess
    
    cmd = " ".join(context.args)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if len(output) > 3000:
            output = output[:3000] + "\n... (truncated)"
        await update.message.reply_text(f"<pre>$ {cmd}\n\n{output or '(done)'}</pre>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask LLM directly (alias for /llm)"""
    if not context.args:
        await update.message.reply_text("Usage: /ask <your question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Thinking...")
    
    try:
        r = requests.post(f"{LM_STUDIO_URL}/v1/chat/completions", 
            json={"model": "lfm2.5-1.2b-instruct",
                  "messages": [{"role": "user", "content": question}],
                  "max_tokens": 300, "temperature": 0.7}, timeout=120)
        
        if r.status_code == 200:
            response = r.json().get("choices", [{}])[0].get("message", {}).get("content", "No response")
            if len(response) > 3000:
                response = response[:3000] + "\n...(truncated)"
            await update.message.reply_text(f"<b>Answer:</b>\n{response}", parse_mode="HTML")
        else:
            await update.message.reply_text(f"LLM Error: {r.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ============== MULTI-LLM ROUTING ==============

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available LLM models"""
    msg = "🧠 *Available LLM Models*\n\n"
    
    # Local models
    msg += "*Local (LM Studio):*\n"
    try:
        r = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
        if r.status_code == 200:
            models = r.json().get("data", [])
            for m in models:
                msg += f"• {m['id']}\n"
    except:
        msg += "  (not available)\n"
    
    # OpenCode
    msg += "\n*OpenCode + z.ai:*\n"
    msg += "  • Advanced reasoning via z.ai\n"
    
    # Claude
    msg += "\n*Claude:*\n"
    if CLAUDE_API_KEY:
        msg += "  • API configured ✅\n"
    else:
        msg += "  • Not configured (set ANTHROPIC_API_KEY)\n"
    
    msg += "\n*Usage:*\n"
    msg += "• /llm <question> - Local LLM\n"
    msg += "• /llm_local <model> <question>\n"
    msg += "• /llm_opencode <question>\n"
    msg += "• /llm_claude <question>\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def llm_local_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Query specific local model"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /llm_local <model_name> <question>\n\n"
            "Example: /llm_local qwen2.5-coder-1.5b-instruct write a python script",
            parse_mode="Markdown"
        )
        return
    
    # Find the model name (first arg that's a known model or just use first arg)
    args_text = " ".join(context.args)
    
    # Check if first arg is a model name
    known_models = ["lfm2.5-1.2b-instruct", "granite-4.0-h-micro", "exaone-4.0-1.2b", 
                   "qwen2.5-coder-1.5b-instruct", "spam-classifier-3b-v1"]
    
    model = "lfm2.5-1.2b-instruct"  # default
    question = args_text
    
    for m in known_models:
        if m in args_text:
            model = m
            question = args_text.split(m, 1)[1].strip()
            break
    
    if question == args_text:  # No model recognized, use default
        question = args_text
    
    await update.message.reply_text(f"🤔 Using {model}...")
    
    try:
        r = requests.post(f"{LM_STUDIO_URL}/v1/chat/completions", 
            json={"model": model,
                  "messages": [{"role": "user", "content": question}],
                  "max_tokens": 500, "temperature": 0.7}, timeout=120)
        
        if r.status_code == 200:
            response = r.json().get("choices", [{}])[0].get("message", {}).get("content", "No response")
            if len(response) > 3000:
                response = response[:3000] + "\n...(truncated)"
            await update.message.reply_text(f"💡 *[{model}]*\n\n{response}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"Error: {r.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def llm_opencode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Query via OpenCode + z.ai"""
    if not context.args:
        await update.message.reply_text("Usage: /llm_opencode <question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Asking OpenCode + z.ai...")

    # Guard: require OPENCODE_API_KEY to be configured
    if not OPENCODE_API_KEY:
        await update.message.reply_text(
            "❌ OpenCode API key not configured. Set the `OPENCODE_API_KEY` environment variable.",
            parse_mode="Markdown"
        )
        return

    try:
        # Try to create a session and send to OpenCode
        import uuid
        session_id = str(uuid.uuid4())[:8]
        
        # OpenCode uses local server - check if it's running
        r = requests.get(f"{OPENCODE_URL}/sessions", 
                       headers={"Authorization": f"Bearer {OPENCODE_API_KEY}"},
                       timeout=5)
        
        if r.status_code == 200:
            sessions = r.json()
            if sessions:
                # Use existing session
                session_id = sessions[0].get("id", "default")
        
        # Send message to OpenCode
        r = requests.post(
            f"{OPENCODE_URL}/sessions/{session_id}/messages",
            headers={
                "Authorization": f"Bearer {OPENCODE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"content": question, "role": "user"},
            timeout=120
        )
        
        if r.status_code == 200:
            data = r.json()
            response = data.get("content", data.get("message", {}).get("content", "No response"))
            if len(response) > 3000:
                response = response[:3000] + "\n...(truncated)"
            await update.message.reply_text(f"💬 *via OpenCode + z.ai*\n\n{response}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"OpenCode error: {r.status_code}\n{r.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        await update.message.reply_text(
            "❌ OpenCode server not running.\n\n"
            "To start: `opencode server`\n"
            "Or use /llm for local LLM",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

async def llm_claude_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Query Claude API"""
    if not context.args:
        await update.message.reply_text("Usage: /llm_claude <question>")
        return
    
    if not CLAUDE_API_KEY:
        await update.message.reply_text(
            "❌ Claude API not configured.\n\n"
            "Set ANTHROPIC_API_KEY env variable:\n"
            "`export ANTHROPIC_API_KEY='your-key'`",
            parse_mode="Markdown"
        )
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Asking Claude...")
    
    try:
        r = requests.post(
            CLAUDE_URL,
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": question}]
            },
            timeout=120
        )
        
        if r.status_code == 200:
            data = r.json()
            response = data.get("content", [{}])[0].get("text", "No response")
            if len(response) > 3000:
                response = response[:3000] + "\n...(truncated)"
            await update.message.reply_text(f"💬 *via Claude*\n\n{response}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"Claude error: {r.status_code}\n{r.text[:200]}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

async def llm_zai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Query z.ai cloud API"""
    if not context.args:
        await update.message.reply_text("Usage: /llm_zai <question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Asking z.ai...")

    # Guard: require ZAI_API_KEY to be configured
    if not ZAI_API_KEY:
        await update.message.reply_text(
            "❌ z.ai API key not configured. Set the `ZAI_API_KEY` environment variable.",
            parse_mode="Markdown"
        )
        return

    try:
        r = requests.post(
            f"{ZAI_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {ZAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "glm-4",
                "messages": [{"role": "user", "content": question}],
                "max_tokens": 500
            },
            timeout=120
        )
        
        if r.status_code == 200:
            data = r.json()
            # z.ai response format
            choices = data.get("choices", [])
            if choices:
                response = choices[0].get("message", {}).get("content", "No response")
            else:
                response = str(data)
            if len(response) > 3000:
                response = response[:3000] + "\n...(truncated)"
            await update.message.reply_text(f"💬 *via z.ai*\n\n{response}", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"z.ai error: {r.status_code}\n{ r.text[:200]}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

async def bi_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show business intelligence dashboard summary"""
    try:
        sys.path.insert(0, '/opt/ACTIVE/INFRA/SPAM')
        from business_intelligence_collector import BusinessIntelligenceCollector
        
        collector = BusinessIntelligenceCollector()
        summary = collector.get_dashboard_summary()
        
        if "error" in summary:
            await update.message.reply_text(f"❌ Error getting dashboard: {summary['error']}")
            return
        
        msg = "📊 <b>Business Intelligence Dashboard</b>\n\n"
        
        # Email metrics
        if 'email' in summary:
            email = summary['email']
            msg += "📧 <b>Email Performance:</b>\n"
            msg += f"  • Total leads: {email.get('total_leads', 0)}\n"
            msg += f"  • Response rate: {email.get('response_rate', 0)}%\n"
            msg += f"  • Avg response time: {email.get('avg_response_time_hours', 0)}h\n\n"
        
        # AI operations
        if 'ai' in summary:
            ai = summary['ai']
            msg += "🤖 <b>AI Operations:</b>\n"
            msg += f"  • Success rate: {ai.get('success_rate', 0)}%\n"
            msg += f"  • Total requests: {ai.get('total_requests', 0)}\n"
            msg += f"  • Avg response time: {ai.get('avg_response_time', 0)}s\n\n"
        
        # Learning metrics
        if 'learning' in summary:
            learning = summary['learning']
            msg += "📚 <b>Learning System:</b>\n"
            msg += f"  • Total learned: {learning.get('total_learned_items', 0)}\n"
            msg += f"  • Spam learned: {learning.get('spam_learned', 0)}\n"
            msg += f"  • Response patterns: {learning.get('response_patterns_learned', 0)}\n"
            msg += f"  • Accuracy: {learning.get('accuracy_rate', 0)}%\n\n"
        
        # System performance
        if 'system' in summary:
            system = summary['system']
            msg += "💻 <b>System Performance:</b>\n"
            msg += f"  • CPU: {system.get('cpu_usage', 0)}%\n"
            msg += f"  • Memory: {system.get('memory_usage', 0)}%\n"
            msg += f"  • Disk: {system.get('disk_usage', 0)}%\n"
            msg += f"  • Uptime: {system.get('uptime_seconds', 0) // 3600}h\n\n"
        
        # Business KPIs
        if 'business' in summary:
            business = summary['business']
            msg += "🎯 <b>Business KPIs:</b>\n"
            msg += f"  • Recruitment efficiency: {business.get('recruitment_efficiency', 0)}%\n"
            msg += f"  • Campaign effectiveness: {business.get('campaign_effectiveness', 0)}%\n"
            msg += f"  • AI accuracy: {business.get('ai_accuracy', 0)}%\n"
            msg += f"  • System uptime: {business.get('system_uptime', 0)}%\n"
            msg += f"  • <b>Overall score: {business.get('overall_score', 0)}%</b>\n"
        
        await update.message.reply_text(msg, parse_mode="HTML")
        
    except Exception as e:
        await update.message.reply_text(f"Error showing dashboard: {str(e)}")

async def bi_collect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger business intelligence data collection"""
    try:
        await update.message.reply_text("🔄 Collecting business intelligence data...")
        
        sys.path.insert(0, '/opt/ACTIVE/INFRA/SPAM')
        from business_intelligence_collector import BusinessIntelligenceCollector
        
        collector = BusinessIntelligenceCollector()
        collector.collect_all_metrics()
        
        await update.message.reply_text(
            "✅ Business intelligence data collection completed!\n\n"
            "Use /bi_dashboard to view the updated dashboard."
        )
        
    except Exception as e:
        await update.message.reply_text(f"Error collecting data: {str(e)}")

async def bi_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export business intelligence report"""
    try:
        sys.path.insert(0, '/opt/ACTIVE/INFRA/SPAM')
        from business_intelligence_collector import BusinessIntelligenceCollector
        
        collector = BusinessIntelligenceCollector()
        report_path = collector.export_metrics_report()
        
        if report_path:
            await update.message.reply_text(
                f"📊 Business intelligence report exported!\n\n"
                f"Location: {report_path}\n\n"
                f"The report contains comprehensive metrics and analytics for all system components."
            )
        else:
            await update.message.reply_text("❌ Failed to export report")
            
    except Exception as e:
        await update.message.reply_text(f"Error exporting report: {str(e)}")

async def bi_kpis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed business KPIs and trends"""
    try:
        sys.path.insert(0, '/opt/ACTIVE/INFRA/SPAM')
        from business_intelligence_collector import BusinessIntelligenceCollector
        
        collector = BusinessIntelligenceCollector()
        
        # Get recent business KPIs from database
        import sqlite3
        conn = sqlite3.connect(collector.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM business_kpis 
            ORDER BY timestamp DESC 
            LIMIT 24
        """)
        results = cursor.fetchall()
        
        if not results:
            await update.message.reply_text("No KPI data available. Use /bi_collect to collect data first.")
            return
        
        # Get column names
        cursor.execute("PRAGMA table_info(business_kpis)")
        columns = [col[1] for col in cursor.fetchall()]
        
        conn.close()
        
        # Format recent KPIs
        msg = "📈 <b>Recent Business KPIs (24 hours)</b>\n\n"
        
        for i, row in enumerate(results[:5]):  # Show last 5 readings
            metrics = dict(zip(columns, row))
            timestamp = metrics.pop('timestamp', '')
            metrics.pop('id', '')
            
            if i == 0:
                msg += f"<b>Latest ({timestamp[-8:]}):</b>\n"
            else:
                msg += f"{timestamp[-8:]}:\n"
            
            for key, value in metrics.items():
                if key == 'overall_score':
                    emoji = "🏆" if value >= 80 else "📊" if value >= 60 else "📉"
                    msg += f"  {emoji} {key.replace('_', ' ').title()}: {value}%\n"
                else:
                    msg += f"  • {key.replace('_', ' ').title()}: {value}%\n"
            
            msg += "\n"
        
        await update.message.reply_text(msg, parse_mode="HTML")
        
    except Exception as e:
        await update.message.reply_text(f"Error getting KPIs: {str(e)}")

def main():
    # Basic raspibig / Unix environment checks
    try:
        if os.name == 'nt':
            logger.warning("Running on Windows — some raspibig/unix assumptions may not hold.")

        # Recommend tighter permissions for this script file
        try:
            file_path = Path(__file__)
            st = file_path.stat()
            mode = st.st_mode
            # if group/other have read/write/exec bits, warn
            if mode & 0o077:
                logger.warning("Permissions for %s allow group/other access. Consider: chmod 640 %s", file_path, file_path)
        except Exception:
            pass
    except Exception:
        pass

    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable not set")
        print("Get token from @BotFather and set:")
        print("  export TELEGRAM_BOT_TOKEN='your_token_here'")
        sys.exit(1)
    
    print(f"🤖 Starting Raspibig Unified Controller...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("spam", spam_fast_command))
    app.add_handler(CommandHandler("spam_score", spam_score_command))
    app.add_handler(CommandHandler("intent", intent_command))
    app.add_handler(CommandHandler("lead", lead_fast_command))
    app.add_handler(CommandHandler("subject", subject_command))
    app.add_handler(CommandHandler("replies", replies_command))
    app.add_handler(CommandHandler("sh", shell_command))
    app.add_handler(CommandHandler("shell", shell_command))
    app.add_handler(CommandHandler("spam_learn", spam_learn_command))
    app.add_handler(CommandHandler("learned_spam", learned_spam_command))
    app.add_handler(CommandHandler("blocked", blocked_command))
    app.add_handler(CommandHandler("learning_stats", learning_stats_command))
    app.add_handler(CommandHandler("learning_export", learning_export_command))
    app.add_handler(CommandHandler("response_patterns", response_patterns_command))
    app.add_handler(CommandHandler("bridge_status", bridge_status_command))
    app.add_handler(CommandHandler("bridge_history", bridge_history_command))
    app.add_handler(CommandHandler("bridge_test", bridge_test_command))
    app.add_handler(CommandHandler("hub_status", hub_status_command))
    app.add_handler(CommandHandler("hub_test", hub_test_command))
    app.add_handler(CommandHandler("hub_multi", hub_multi_command))
    app.add_handler(CommandHandler("hub_task", hub_task_command))
    app.add_handler(CommandHandler("enrich", enrich_command))
    app.add_handler(CommandHandler("llm", llm_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("llm_local", llm_local_command))
    app.add_handler(CommandHandler("llm_opencode", llm_opencode_command))
    app.add_handler(CommandHandler("llm_zai", llm_zai_command))
    app.add_handler(CommandHandler("llm_claude", llm_claude_command))
    app.add_handler(CommandHandler("models", models_command))
    app.add_handler(CommandHandler("skills", skills_command))
    app.add_handler(CommandHandler("campaign", campaign_command))
    app.add_handler(CommandHandler("campaign_generate", campaign_generate_command))
    app.add_handler(CommandHandler("campaign_deploy", campaign_deploy_command))
    app.add_handler(CommandHandler("emails", emails_command))
    app.add_handler(CommandHandler("email_actions", email_actions_command))
    app.add_handler(CommandHandler("complete_action", complete_action_command))
    app.add_handler(CommandHandler("bi_dashboard", bi_dashboard_command))
    app.add_handler(CommandHandler("bi_collect", bi_collect_command))
    app.add_handler(CommandHandler("bi_report", bi_report_command))
    app.add_handler(CommandHandler("bi_kpis", bi_kpis_command))
    app.add_handler(CommandHandler("services", services_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("process_emails", process_emails_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot ready! Press Ctrl+C to stop")
    print(f"Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

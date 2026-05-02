#!/usr/bin/env python3
"""
Telegram Unified Controller - Fixed for raspibig/unix compliance
Single interface for all raspibig operations following project conventions

Usage:
    /status - System status overview
    /spam_score <text> - Get spam score
    /enrich <company> <country> - Enrich company data
    /campaign_generate <industry>,<countries> - Generate AI campaign
    /emails [priority] [category] - Get email summaries
    /help - Show all commands

Follows raspibig conventions:
- Uses 192.168.100.21 (not hostname)
- Proper Unix permissions and paths
- Systemd service integration
- Local processing (LM Studio, PICOCLAW)
"""

import os
import sys
import json
import re
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration following raspibig conventions
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8")
PICOCLAW_URL = "http://localhost:5055"  # PICOCLAW on raspibig
LM_STUDIO_URL = "http://localhost:1234"  # LM Studio on raspibig
RASPIBIG_IP = "192.168.100.21"  # Always use IP, not hostname

# Paths following raspibig conventions
SPAM_DB = Path("/opt/ACTIVE/INFRA/SPAM/spam_learning.db")
UNIFIED_LEARNING_DB = Path("/opt/ACTIVE/INFRA/SPAM/unified_learning.db")
CAMPAIGN_GENERATOR = "/opt/ACTIVE/INFRA/SPAM/campaign_auto_generator.py"
EMAIL_SUMMARIZER = "/opt/ACTIVE/INFRA/SPAM/email_summarizer.py"
ZAI_HUB = "/opt/ACTIVE/INFRA/SKILLS/zai_hub.py"
OPENCODE_BRIDGE = "/opt/ACTIVE/INFRA/SKILLS/opencode_picoclaw_bridge.py"
UNIFIED_LEARNING = "/opt/ACTIVE/INFRA/SPAM/unified_learning_database.py"

# Setup logging for Unix compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RaspibigController:
    """Main controller class following Unix/raspibig conventions"""
    
    def __init__(self):
        self._check_unix_environment()
        
    def _check_unix_environment(self):
        """Ensure we're running in proper Unix/raspibig environment"""
        if os.name != 'posix':
            logger.warning("Not running on Unix system - some features may not work")
        
        # Check key raspibig paths
        key_paths = [
            "/opt/ACTIVE/INFRA",
            "/opt/ACTIVE/EMAIL", 
            "/usr/local/bin/opencode"
        ]
        
        for path in key_paths:
            if not os.path.exists(path):
                logger.warning(f"raspibig path not found: {path}")
    
    def _run_raspibig_command(self, cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Execute command on raspibig following Unix conventions"""
        try:
            logger.info(f"Executing raspibig command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/opt/ACTIVE/INFRA"  # Use standard raspibig working directory
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command with raspibig status"""
    await update.message.reply_text(
        "🤖 *Raspibig Unified Controller*\n\n"
        "System running with PICOCLAW, LM Studio, and AI integration\n\n"
        "Use /help for available commands",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comprehensive help following project structure"""
    help_text = """
📚 *Raspibig Controller Commands*

🔍 *System & Status:*
• `/status` - System overview
• `/services` - Service health  
• `/stats` - System statistics
• `/logs <service>` - View logs

📧 *Email Processing:*
• `/emails [priority] [category]` - Email summaries
• `/email_actions` - Pending actions
• `/complete_action <id>` - Complete action
• `/process_emails` - Trigger email processing

🤖 *AI & LLM:*
• `/llm <question>` - Local LLM query
• `/spam_score <text>` - Spam scoring
• `/enrich <company> <country>` - Company enrichment
• `/intent <text>` - Response intent

🎯 *Campaigns:*
• `/campaign status|stats` - Campaign status
• `/campaign_generate <industry>,<countries>` - AI campaign
• `/campaign_deploy <id>` - Deploy campaign

🧠 *AI Integration:*
• `/hub_status` - z.ai Hub status
• `/hub_test <question>` - Test hub
• `/hub_multi <question>` - Multi-provider test
• `/bridge_status` - OpenCode+PICOCLAW status
• `/bridge_history` - Bridge task history

📊 *Learning:*
• `/learning_stats` - Learning statistics
• `/response_patterns` - Response patterns
• `/learned_spam` - Learned spam
• `/blocked` - Blocked senders

🛠️ *System:*
• `/sh <command>` - Execute shell command
• `/skills` - PICOCLAW tasks
• `/models` - Available LLM models

Use /status to see current system state.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """System status overview"""
    try:
        controller = RaspibigController()
        status_parts = []
        
        # Check PICOCLAW
        try:
            response = requests.get(f"{PICOCLAW_URL}/status", timeout=5)
            if response.status_code == 200:
                status_parts.append("✅ PICOCLAW (port 5055)")
            else:
                status_parts.append("❌ PICOCLAW")
        except:
            status_parts.append("❌ PICOCLAW")
        
        # Check LM Studio
        try:
            response = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
            if response.status_code == 200:
                status_parts.append("✅ LM Studio (port 1234)")
            else:
                status_parts.append("❌ LM Studio")
        except:
            status_parts.append("❌ LM Studio")
        
        # Check services
        services_to_check = ["llm-email-processor", "telegram-unified-controller"]
        for service in services_to_check:
            try:
                result = controller._run_raspibig_command(
                    ["systemctl", "is-active", service], 
                    timeout=10
                )
                if result.returncode == 0:
                    status_parts.append(f"✅ {service}")
                else:
                    status_parts.append(f"❌ {service}")
            except:
                status_parts.append(f"❌ {service}")
        
        status_message = "📊 *System Status*\n\n" + "\n".join(status_parts)
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting status: {str(e)}")

async def spam_score_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Spam scoring using PICOCLAW"""
    if not context.args:
        await update.message.reply_text("Usage: /spam_score <text to score>")
        return
    
    text_to_score = " ".join(context.args)
    await update.message.reply_text(f"🔍 Scoring: `{text_to_score[:100]}...`", parse_mode='Markdown')
    
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["curl", "-s", f"{PICOCLAW_URL}/task", 
             "-H", "Content-Type: application/json",
             "-d", f'{{\"task_type\": \"spam_score\", \"payload\": {{\"text\": \"{text_to_score}\"}}}}'],
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                if response_data.get("status") == "completed":
                    score_result = response_data.get("result", {})
                    score = score_result.get("score", 0)
                    reason = score_result.get("reason", "No reason provided")
                    
                    message = f"📊 *Spam Score: {score}/100*\n\nReason: {reason}"
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Spam scoring failed")
            except json.JSONDecodeError:
                await update.message.reply_text("❌ Invalid response format")
        else:
            await update.message.reply_text(f"❌ Error: {result.stderr}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def enrich_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Company enrichment using PICOCLAW"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /enrich <company> <country>")
        return
    
    company = context.args[0]
    country = " ".join(context.args[1:])
    
    await update.message.reply_text(f"🔍 Enriching: {company} ({country})")
    
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["curl", "-s", f"{PICOCLAW_URL}/task",
             "-H", "Content-Type: application/json",
             "-d", f'{{"task_type": "lead_enrich", "payload": {{"company": "{company}", "country": "{country}"}}}}'],
            timeout=60
        )
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                if response_data.get("status") == "completed":
                    enrich_result = response_data.get("result", {})
                    
                    message = f"🏢 *{company}* ({country})\n\n"
                    for key, value in enrich_result.items():
                        if isinstance(value, (str, int, float)):
                            message += f"• {key.replace('_', ' ').title()}: {value}\n"
                    
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Enrichment failed")
            except json.JSONDecodeError:
                await update.message.reply_text("❌ Invalid response format")
        else:
            await update.message.reply_text(f"❌ Error: {result.stderr}")
            
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
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["python3", CAMPAIGN_GENERATOR, "--generate", params],
            timeout=120
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ *Campaign Generated*\n\n```\n{result.stdout}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Campaign generation failed: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get email summaries using Email Summarizer"""
    priority = context.args[0] if context.args else None
    category = context.args[1] if len(context.args) > 1 else None
    
    await update.message.reply_text("📧 Processing email summaries...")
    
    try:
        controller = RaspibigController()
        cmd = ["python3", EMAIL_SUMMARIZER, "--summaries"]
        if priority:
            cmd.append(priority)
        if category:
            cmd.append(category)
        
        result = controller._run_raspibig_command(cmd, timeout=90)
        
        if result.returncode == 0:
            output = result.stdout
            if len(output) > 4000:  # Telegram limit
                output = output[:4000] + "...(truncated)"
            
            await update.message.reply_text(
                f"📋 *Email Summaries*\n\n```\n{output}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Error getting email summaries: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def email_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get pending email actions"""
    await update.message.reply_text("📝 Getting pending email actions...")
    
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["python3", EMAIL_SUMMARIZER, "--actions"],
            timeout=60
        )
        
        if result.returncode == 0:
            output = result.stdout
            if len(output) > 4000:
                output = output[:4000] + "...(truncated)"
            
            await update.message.reply_text(
                f"📝 *Pending Email Actions*\n\n```\n{output}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Error getting email actions: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def hub_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show z.ai Hub status"""
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["python3", ZAI_HUB, "--status"],
            timeout=30
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"🌐 *z.ai Hub Status*\n\n```\n{result.stdout}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Error getting hub status: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute safe shell commands on raspibig"""
    if not context.args:
        await update.message.reply_text("Usage: /sh <command>")
        return
    
    shell_cmd = " ".join(context.args)
    
    # Security check - only allow safe commands
    safe_commands = [
        'systemctl', 'service', 'ps', 'df', 'free', 'uptime', 'whoami', 
        'pwd', 'ls', 'cat', 'head', 'tail', 'grep', 'wc', 'date'
    ]
    
    if not any(safe_cmd in shell_cmd for safe_cmd in safe_commands):
        await update.message.reply_text("❌ Command not allowed for security")
        return
    
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            shell_cmd.split(),
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout
            if len(output) > 4000:
                output = output[:4000] + "...(truncated)"
            
            await update.message.reply_text(
                f"🖥️ *Shell Output*\n\n```\n{output}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Error: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check service health"""
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"],
            timeout=30
        )
        
        if result.returncode == 0:
            # Filter for relevant services
            lines = result.stdout.split('\n')
            relevant_services = []
            
            for line in lines:
                if any(service in line.lower() for service in ['telegram', 'llm', 'email', 'campaign']):
                    relevant_services.append(line)
            
            if relevant_services:
                message = "🔧 *Running Services*\n\n```\n" + "\n".join(relevant_services[:10]) + "\n```"
            else:
                message = "🔧 No relevant services found"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Error getting services: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """System statistics"""
    try:
        controller = RaspibigController()
        
        # Get basic system stats
        stats_info = []
        
        # Uptime
        result = controller._run_raspibig_command(["uptime", "-p"], timeout=10)
        if result.returncode == 0:
            stats_info.append(f"⏱️ Uptime: {result.stdout.strip()}")
        
        # Memory
        result = controller._run_raspibig_command(["free", "-h"], timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Mem:' in line:
                    stats_info.append(f"💾 Memory: {line.strip()}")
                    break
        
        # Disk
        result = controller._run_raspibig_command(["df", "-h", "/"], timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if '/dev/' in line:
                    parts = line.split()
                    if len(parts) >= 6:
                        stats_info.append(f"💿 Disk: {parts[4]} used ({parts[5]})")
                        break
        
        message = "📊 *System Statistics*\n\n" + "\n".join(stats_info)
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting stats: {str(e)}")

async def learning_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show learning database statistics"""
    try:
        controller = RaspibigController()
        result = controller._run_raspibig_command(
            ["python3", UNIFIED_LEARNING, "--stats"],
            timeout=30
        )
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"📚 *Learning Statistics*\n\n```\n{result.stdout}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Error getting learning stats: {result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List PICOCLOW tasks/skills"""
    try:
        response = requests.get(f"{PICOCLAW_URL}/tasks", timeout=10)
        if response.status_code == 200:
            tasks_data = response.json()
            message = "🛠️ *PICOCLAW Tasks/Skills*\n\n"
            
            for task in tasks_data.get('tasks', []):
                message += f"• `{task}`\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error getting PICOCLAW tasks")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle natural language messages with simple responses"""
    user_message = update.message.text.strip().lower()
    
    # Simple greetings and responses
    greetings = ["hello", "hi", "hey", "buna", "salut", "good morning", "good afternoon"]
    if any(greeting in user_message for greeting in greetings):
        await update.message.reply_text(
            "👋 Hello! I'm the Raspibig Unified Controller.\n\n"
            "Try commands like:\n"
            "• /status - Check system status\n"
            "• /help - See all commands\n"
            "• /spam_score test text - Test spam scoring",
            parse_mode='Markdown'
        )
        return
    
    # Simple status requests
    if any(word in user_message for word in ["status", "how are you", "how's it going"]):
        await status_command(update, context)
        return
    
    # Default response
    await update.message.reply_text(
        "🤖 I can help with raspibig operations!\n\n"
        "Use /help to see available commands, or try:\n"
        "• /status\n"
        "• /emails\n"
        "• /campaign_generate HORECA,Poland",
        parse_mode='Markdown'
    )

def main():
    """Main function with proper Unix setup"""
    # Set proper file permissions for security
    try:
        os.chmod(__file__, 0o750)  # rwxr-x--- for raspibig security
    except:
        pass  # Continue if permission change fails
    
    # Validate environment
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable not set")
        print("Get token from @BotFather and set:")
        print("  export TELEGRAM_BOT_TOKEN='your_token_here'")
        sys.exit(1)
    
    logger.info(f"🤖 Starting Raspibig Unified Controller...")
    logger.info(f"Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")
    
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    handlers = [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("status", status_command),
        CommandHandler("spam_score", spam_score_command),
        CommandHandler("enrich", enrich_command),
        CommandHandler("campaign_generate", campaign_generate_command),
        CommandHandler("emails", emails_command),
        CommandHandler("email_actions", email_actions_command),
        CommandHandler("hub_status", hub_status_command),
        CommandHandler("sh", shell_command),
        CommandHandler("shell", shell_command),
        CommandHandler("services", services_command),
        CommandHandler("stats", stats_command),
        CommandHandler("learning_stats", learning_stats_command),
        CommandHandler("skills", skills_command),
        CommandHandler("campaign", campaign_command),  # Keep for compatibility
        CommandHandler("process_emails", process_emails_command),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    ]
    
    for handler in handlers:
        app.add_handler(handler)
    
    logger.info("✅ Bot ready! Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

# Compatibility function for existing command
async def campaign_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Campaign command for compatibility"""
    if not context.args:
        await update.message.reply_text("Usage: /campaign status|stats")
        return
    
    action = context.args[0].lower()
    if action in ["status", "stats"]:
        await update.message.reply_text("📊 Use /campaign_generate to create AI campaigns")
    else:
        await update.message.reply_text("Unknown campaign action. Use /help")

async def process_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Email processing command"""
    await update.message.reply_text(
        "📧 Email processing is handled by systemd service:\n"
        "`sudo systemctl restart llm-email-processor`",
        parse_mode='Markdown'
    )

if __name__ == "__main__":
    main()
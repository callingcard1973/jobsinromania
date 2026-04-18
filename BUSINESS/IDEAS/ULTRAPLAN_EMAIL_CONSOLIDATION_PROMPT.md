# Email Consolidation — Prompt for new Claude session

Paste this in a new Claude Code session (working directory D:\MEMORY\IDEAS or D:\MEMORY\ULTRAPLAN):

---

Read D:\MEMORY\ULTRAPLAN\ULTRAPLAN_STATUS.md first. Consolidate the 3 email systems (email_pipeline.py + email_poller.py + queue_worker.py) into one clean pipeline. One scan, one classify, one route. Max 250 lines per script. If an email is broken — skip it, log it, continue. Use sklearn first, escalate to Ollama qwen2.5:1.5b on localhost:11434. Key files: /opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py, /opt/AUTOMATE/email_poller.py, /opt/AUTOMATE/queue_worker.py, /opt/AUTOMATE/email_proposer.py, /opt/ACTIVE/EMAIL/ORDERS/email_accounts.py

#!/bin/bash
# Deploy LLM Email Responder to raspibig
# Run from laptop: bash deploy.sh

set -e
REMOTE="tudor@192.168.100.21"
DEST="/opt/ACTIVE/EMAIL/LLM_RESPONDER"
SRC="D:/MEMORY/IDEAS/LLM"

echo "=== Creating remote directory ==="
ssh $REMOTE "mkdir -p $DEST/logs $DEST/models"

echo "=== Copying files ==="
scp "$SRC/email_responder.py" $REMOTE:$DEST/
scp "$SRC/gmail_drafter.py" $REMOTE:$DEST/
scp "$SRC/response_templates.py" $REMOTE:$DEST/
scp "$SRC/import_labels_to_pg.py" $REMOTE:$DEST/
scp "$SRC/config.json" $REMOTE:$DEST/
scp "$SRC/models/email_classifier.pkl" $REMOTE:$DEST/models/
scp "$SRC/labels.db" $REMOTE:$DEST/

echo "=== Installing services ==="
scp "$SRC/email-responder.service" $REMOTE:/tmp/
scp "$SRC/gmail-drafter.service" $REMOTE:/tmp/
ssh $REMOTE "sudo cp /tmp/email-responder.service /etc/systemd/system/ && \
             sudo cp /tmp/gmail-drafter.service /etc/systemd/system/ && \
             sudo systemctl daemon-reload"

echo "=== Setting raspibig model to qwen3-8b ==="
ssh $REMOTE "cd $DEST && sed -i 's|google/gemma-3-4b|qwen3-8b|' config.json"

echo "=== Importing labels to PostgreSQL ==="
ssh $REMOTE "cd $DEST && python3 import_labels_to_pg.py"

echo "=== Loading Qwen3-8B ==="
ssh $REMOTE "lms unload --all 2>/dev/null; lms load qwen3-8b --yes"

echo "=== Restarting classifier with new model ==="
ssh $REMOTE "sudo systemctl restart email-classifier.service"

echo "=== Starting services ==="
ssh $REMOTE "sudo systemctl enable --now email-responder.service"
# gmail-drafter needs GMAIL_APP_PASSWORD first
echo "NOTE: Set GMAIL_APP_PASSWORD in gmail-drafter.service before enabling"

echo "=== Verify ==="
ssh $REMOTE "systemctl status email-responder.service | head -5"
ssh $REMOTE "curl -s http://localhost:5080/health"
ssh $REMOTE "lms ps"

echo "=== DONE ==="

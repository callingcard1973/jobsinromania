#!/usr/bin/env bash
# Deploy CV Parser to raspibig + factoryjobs.eu/cv/
set -euo pipefail

REMOTE="tudor@192.168.100.21"
REMOTE_DIR="/opt/ACTIVE/PHONE_CAMPAIGN/cv_parser"
CPANEL_USER="loaiidil"
CPANEL_HOST="nl1-cl8-ats1.a2hosting.com"
TOKEN_FILE="/opt/ACTIVE/PHONE_CAMPAIGN/cpanel_token.txt"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> [1/4] Creating remote directory..."
ssh "$REMOTE" "mkdir -p $REMOTE_DIR"

echo "==> [2/4] Copying files to raspibig..."
scp "$SCRIPT_DIR/app.py" \
    "$SCRIPT_DIR/parser.py" \
    "$SCRIPT_DIR/requirements.txt" \
    "$REMOTE:$REMOTE_DIR/"

echo "==> [3/4] Installing Python dependencies on raspibig..."
ssh "$REMOTE" "pip3 install --quiet -r $REMOTE_DIR/requirements.txt"

echo "==> [4/4] Installing and starting systemd service..."
scp "$SCRIPT_DIR/cv-parser.service" "$REMOTE:/tmp/cv-parser.service"
ssh "$REMOTE" "
  sudo cp /tmp/cv-parser.service /etc/systemd/system/cv-parser.service
  sudo systemctl daemon-reload
  sudo systemctl enable cv-parser
  sudo systemctl restart cv-parser
  sleep 2
  sudo systemctl status cv-parser --no-pager | head -20
"

echo ""
echo "==> [5/5] Deploying index.html to factoryjobs.eu/cv/ via cPanel UAPI..."

# Read cPanel token from raspibig (where the token file lives)
TOKEN=$(ssh "$REMOTE" "cat $TOKEN_FILE")

BASE_URL="https://${CPANEL_HOST}:2083"
AUTH="Authorization: cpanel ${CPANEL_USER}:${TOKEN}"

# Create /cv/ directory
echo "    Creating cv/ directory..."
MKDIR_RESULT=$(curl -sf -H "$AUTH" \
  "${BASE_URL}/execute/Fileman/mkdir?path=%2Fhome%2F${CPANEL_USER}%2Ffactoryjobs.eu%2Fcv" || true)
echo "    mkdir result: $MKDIR_RESULT"

# Upload index.html
echo "    Uploading index.html..."
SAVE_RESULT=$(curl -sf -H "$AUTH" -X POST \
  "${BASE_URL}/execute/Fileman/save_file_content" \
  --data-urlencode "dir=/home/${CPANEL_USER}/factoryjobs.eu/cv" \
  --data-urlencode "filename=index.html" \
  --data-urlencode "content@${SCRIPT_DIR}/index.html")
echo "    save result: $SAVE_RESULT"

echo ""
echo "Done!"
echo "  API:      http://192.168.100.21:5050/parse-cv"
echo "  Frontend: https://factoryjobs.eu/cv/"
echo ""
echo "Test with:"
echo "  curl -X POST http://192.168.100.21:5050/parse-cv -F 'file=@/path/to/cv.pdf'"

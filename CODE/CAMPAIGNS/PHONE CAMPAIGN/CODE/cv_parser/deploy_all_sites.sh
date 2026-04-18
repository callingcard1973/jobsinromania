#!/usr/bin/env bash
# Deploy /cv/index.html to all 14 job site domains on A2 Hosting
# Runs ON raspibig. factoryjobs.eu is already done — skipped.
set -euo pipefail

HOST="nl1-cl8-ats1.a2hosting.com"
USER="loaiidil"
SRC="/opt/ACTIVE/PHONE_CAMPAIGN/cv_parser/index.html"
TOKEN_FILE="/opt/ACTIVE/PHONE_CAMPAIGN/cpanel_token.txt"

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "ERROR: Token file not found: $TOKEN_FILE"
  exit 1
fi
TOKEN=$(cat "$TOKEN_FILE")

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: Source file not found: $SRC"
  exit 1
fi

cp "$SRC" /tmp/cv_index.html
echo "Source copied to /tmp/cv_index.html"

DOMAINS=(
  careworkers.eu
  buildjobs.eu
  electricjobs.eu
  farmworkers.eu
  horecaworkers.eu
  meatworkers.eu
  mechanicjobs.eu
  warehouseworkers.eu
  aluminumrecyclehub.com
  expatsinromania.org
  interjob.ro
  mivromania.info
  mivromania.online
  nepalezi.com
)

AUTH="Authorization: cpanel ${USER}:${TOKEN}"
BASE="https://${HOST}:2083/json-api/cpanel"

ok=0
fail=0

for DOMAIN in "${DOMAINS[@]}"; do
  DOCROOT="/home/${USER}/${DOMAIN}"

  # 1. Create /cv/ directory
  mkdir_result=$(curl -sf \
    -H "$AUTH" \
    "${BASE}?cpanel_jsonapi_version=2&cpanel_jsonapi_module=Fileman&cpanel_jsonapi_func=mkdir&path=%2Fhome%2F${USER}%2F${DOMAIN}&name=cv" \
    2>&1) || true

  # 2. Upload index.html
  upload_result=$(curl -sf \
    -H "$AUTH" \
    "${BASE}?cpanel_jsonapi_version=2&cpanel_jsonapi_module=Fileman&cpanel_jsonapi_func=savefile&dir=%2Fhome%2F${USER}%2F${DOMAIN}%2Fcv&filename=index.html" \
    --data-urlencode "content@/tmp/cv_index.html" \
    2>&1)

  if echo "$upload_result" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('cpanelresult',{}).get('data',[{}])[0].get('result',0)==1 else 1)" 2>/dev/null; then
    echo "OK  $DOMAIN/cv/"
    ((ok++))
  else
    echo "FAIL $DOMAIN/cv/ — $upload_result"
    ((fail++))
  fi
done

echo ""
echo "Done: ${ok} OK, ${fail} FAIL"

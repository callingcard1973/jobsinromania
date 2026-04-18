# Aliyun DirectMail DNS Configuration — Handoff

**Date**: 2026-04-08  
**Domains**: expatsinromania.org, cifn.eu  
**cPanel**: nl1-cl8-ats1.a2hosting.com:2083 (user: loaiidil, token: 3KN7DT1EROZH79X3UWI3LUV4MJF5KXHX)

---

## cifn.eu — VERIFIED

All 4 records added, Aliyun confirmed verification.

| # | Type | Host | Value | Status |
|---|------|------|-------|--------|
| 1 | TXT | aliyundm.cifn.eu | `a1faacbde9ae9859db68` | Verified |
| 2 | TXT | cifn.eu | `v=spf1 include:spfdm-ap-southeast-1.aliyun.com include:spf.brevo.com -all` | Verified |
| 3 | TXT | aliyun-ap-southeast-1._domainkey.cifn.eu | DKIM 1024-bit key (starts `MIGfMA0...nsY4QIDAQAB`) | Verified |
| 4 | TXT | _dmarc.cifn.eu | `v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com` | Verified |
| 5 | MX | cifn.eu | mxdm-ap-southeast-1.aliyun.com | Verified |

**Note**: cifn.eu has 2 DMARC records (Brevo + Aliyun). Both functional, no conflict.

---

## expatsinromania.org — NOT YET VERIFIED, NEEDS CLEANUP

### What's working (confirmed in zone file)
- **Ownership**: `aliyundm` TXT = `2640863cc4ce991e9f07` — present
- **DKIM**: `aliyun-ap-southeast-1._domainkey` TXT — present with correct key

### What's broken
- **SPF**: The main `expatsinromania.org.` SPF record does NOT contain `include:spfdm-ap-southeast-1.aliyun.com`. Multiple edit attempts created duplicates, and the wrong ones got deleted each time.
- **DMARC**: Old garbled record `_dmarc.expatsinromania.org. 14400 TXT \nv=DMARC1; p=quarantine...` still present. The clean Aliyun DMARC was deleted by mistake.

### Root cause
cPanel API2 `edit_zone_record` does NOT edit in-place — it **adds a new record**. Combined with `remove_zone_record` by line index (which shifts after each operation), this caused the correct new records to be deleted while old ones survived.

### Fix needed (manual or script)

**Step 1**: List current SPF and DMARC records with line indices:
```bash
curl -s -H "Authorization: cpanel loaiidil:3KN7DT1EROZH79X3UWI3LUV4MJF5KXHX" \
  "https://nl1-cl8-ats1.a2hosting.com:2083/execute/DNS/parse_zone?zone=expatsinromania.org" | python3 -c "
import json,sys,base64
d=json.load(sys.stdin)
for r in d.get('data',[]):
    if r.get('record_type')=='TXT':
        name = r.get('dname_raw','')
        data = [base64.b64decode(x).decode() for x in r.get('data_b64',[])]
        val = ' '.join(data)
        if 'spf1' in val or 'dmarc' in val.lower():
            print(f'line={r[\"line_index\"]:3} {name:40} {val[:130]}')"
```

**Step 2**: Delete the OLD SPF record (the one WITHOUT `aliyun` in value). Note the line number from Step 1.
```bash
curl -s -G -H "Authorization: cpanel loaiidil:3KN7DT1EROZH79X3UWI3LUV4MJF5KXHX" \
  "https://nl1-cl8-ats1.a2hosting.com:2083/json-api/cpanel" \
  --data-urlencode "cpanel_jsonapi_apiversion=2" \
  --data-urlencode "cpanel_jsonapi_module=ZoneEdit" \
  --data-urlencode "cpanel_jsonapi_func=remove_zone_record" \
  --data-urlencode "domain=expatsinromania.org" \
  --data-urlencode "line=LINE_NUMBER"
```

**Step 3**: Add correct SPF (since old one is gone):
```bash
curl -s -G -H "Authorization: cpanel loaiidil:3KN7DT1EROZH79X3UWI3LUV4MJF5KXHX" \
  "https://nl1-cl8-ats1.a2hosting.com:2083/json-api/cpanel" \
  --data-urlencode "cpanel_jsonapi_apiversion=2" \
  --data-urlencode "cpanel_jsonapi_module=ZoneEdit" \
  --data-urlencode "cpanel_jsonapi_func=add_zone_record" \
  --data-urlencode "domain=expatsinromania.org" \
  --data-urlencode "name=expatsinromania.org." \
  --data-urlencode "type=TXT" \
  --data-urlencode "txtdata=v=spf1 +a +mx +ip4:209.124.66.6 include:spf.a2hosting.com include:spf.brevo.com include:spfdm-ap-southeast-1.aliyun.com -all" \
  --data-urlencode "ttl=14400"
```

**Step 4**: Re-list to find garbled DMARC line (the one with `_dmarc.expatsinromania.org. 14400 TXT` in value — this is corrupted). Delete it.

**Step 5**: Add correct DMARC:
```bash
curl -s -G -H "Authorization: cpanel loaiidil:3KN7DT1EROZH79X3UWI3LUV4MJF5KXHX" \
  "https://nl1-cl8-ats1.a2hosting.com:2083/json-api/cpanel" \
  --data-urlencode "cpanel_jsonapi_apiversion=2" \
  --data-urlencode "cpanel_jsonapi_module=ZoneEdit" \
  --data-urlencode "cpanel_jsonapi_func=add_zone_record" \
  --data-urlencode "domain=expatsinromania.org" \
  --data-urlencode "name=_dmarc.expatsinromania.org." \
  --data-urlencode "type=TXT" \
  --data-urlencode "txtdata=v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com" \
  --data-urlencode "ttl=14400"
```

**Step 6**: Verify on Aliyun — click Refresh.

---

## Lesson Learned: cPanel API2 ZoneEdit Behavior

| Function | Behavior |
|----------|----------|
| `add_zone_record` | Adds new record. Works as expected. |
| `edit_zone_record` | Does NOT edit in-place. ADDS a new record, leaves old one. Effectively same as add. |
| `remove_zone_record` | Removes by line index. **Line indices shift after each removal.** Must re-query between deletions. |

**Safe pattern**: Always DELETE first, then ADD. Never use `edit_zone_record`. Always re-query line indices between each `remove_zone_record` call.

---

## Skill Created

`aliyun-dns` skill deployed to:
- Laptop: `C:\Users\apami\.claude\skills\aliyun-dns\SKILL.md`
- raspibig: `/opt/ACTIVE/INFRA/SKILLS/aliyun-dns/SKILL.md`
- raspi: `~/MEMORY/.claude/skills/aliyun-dns/SKILL.md`

**Skill needs update**: Add the lesson about `edit_zone_record` not working — always use delete+add pattern.

---

## Alternative: cPanel Zone Editor UI

If API keeps causing issues, use the web UI directly:
1. Go to https://nl1-cl8-ats1.a2hosting.com:2083
2. Login as loaiidil
3. Zone Editor → expatsinromania.org → Manage
4. Find and delete the bad SPF/DMARC records manually
5. Add correct ones via + Add Record → TXT

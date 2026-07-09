# Skill: dnc-mailbox-scan

Scan all A2 Hosting IMAP mailboxes (125+ accounts) for campaign opt-out/unsubscribe/stop requests, confirm via body text, and generate a DNC suppression list.

**Trigger keywords:** "scan mailboxes for opt-outs", "check for unsubscribes", "scan all inboxes for DNC", "find opt-outs in campaign mailboxes", "check for stop replies", "run DNC mailbox scan". Use whenever a campaign DNC review is needed — after campaign sends, weekly audit, or on demand.

---

## Why this approach

A2 Hosting's `Email/verify_password` API is **broken** (always returns success). The only reliable way to access A2 mailboxes is:
1. Reset the password via `Email/passwd_pop` API (works, strength ≥50 required)
2. Use PHP IMAP with the new password

IMAP on port 143 requires SSL — always use `{localhost:993/imap/ssl/novalidate-cert}`.

---

## Procedure

### Step 1: Reset mailbox passwords (if needed)

Use `Email/list_pops_with_disk` cPanel API to get the exact list of existing mailboxes, then `Email/passwd_pop` to reset each.

PHP pattern:
```php
$h = ['Authorization: cpanel loaiidil:KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453'];
// GET all mailboxes
$resp = curl_get("https://nl1-cl8-ats1.a2hosting.com:2083/execute/Email/list_pops_with_disk", $h);
// For each: reset password
curl_post("https://nl1-cl8-ats1.a2hosting.com:2083/execute/Email/passwd_pop?email=$email&domain=$domain&password=" . urlencode($new_pw) . "&quota=250", $h);
```

Starting password (2026-06-26): `InterJobScan2026!` — all 125 mailboxes use this.

### Step 2: Scan each mailbox

For each mailbox, connect via IMAP and scan the last 300 messages:

```php
$mbox = imap_open("{localhost:993/imap/ssl/novalidate-cert}INBOX", $email, $pw, OP_READONLY, 0);
$total = imap_num_msg($mbox);
for ($i = $total; $i >= max(1, $total - 300); $i--) {
    $h = imap_headerinfo($mbox, $i);
    // Match subject + from + name against opt-out keywords
}
```

### Step 3: Verify opt-out keywords

Keywords to search (case-insensitive, in subject + from name + from address):
`unsubscribe`, `dezabonare`, `stop`, `opt-out`, `opt out`, `nu mai`, `remove`, `delete`, `nu trimite`, `do not send`, `please remove`, `spam`, `not interested`, `nu ma mai`, `nu mă mai`, `renunț`, `renunt`, `sterge`, `șterge`, `take me off`, `cease`, `desist`, `nu mai contacta`, `nu mai trimite`, `nu mai sunteți`

### Step 4: Confirm via body

On keyword match in subject/from, fetch the email body and verify it's a real opt-out. **Skip these false positives:**

| Matched keyword | False positive pattern | Why |
|----------------|----------------------|-----|
| delete | "[Brevo] An API key has been deleted" | Brevo notification, not opt-out |
| spam | "SMTP2GO Spam/Bounce Weekly Summary" | Auto-generated report |
| cease | "ceasefire" in newsletter subjects | Word fragment match |
| stop | "stopped us in our tracks" | Marketing email |
| unsubscribe | "you have been unsubscribed" or "your unsubscribe request" | Autoresponder confirmation, not a request |

Body confirmation criteria: look for phrases like "please unsubscribe me", "please remove me", "nu mai doresc", "stop sending", "dezabonați-mă", "ștergeți-mă din listă".

### Step 5: Report + add to DNC

For each confirmed opt-out:
1. Print: `BOX, FROM, SUBJECT, DATE, KEYWORD, BODY (first 300 chars)`
2. Write to DNC CSV: `from_email, "opt-out", source_mailbox, date`
3. Append to `dnc_master` on raspi (if available) or local project DNC file

---

## Reference: Full scan script

The canonical script pattern is in `scripts/scan_mailbox_dnc.php`. Deploy it to any A2 domain's writable directory (e.g., `/home/loaiidil/electricjobs.eu/wp/`) and execute via web request. Clean up after execution.

---

## Important notes

- **Batch size:** Scan max 10-15 mailboxes per script execution (PHP web timeout ~120s). For full 125-mailbox scan, run 8-10 batches or use CLI PHP.
- **IMAP timeout:** `imap_timeout(IMAP_OPENTIMEOUT, 5)` and `imap_timeout(IMAP_READTIMEOUT, 5)` before connecting.
- **Password reset:** Only resets if `status:1`. Some accounts may not exist (error "You do not have an email account named .") — skip those.
- **CLI PHP:** On A2, PHP CLI is at `/usr/bin/php`. Execute via `exec()` or SSH. Use `file_put_contents()` to write the scan script, then `exec("/usr/bin/php $script_path")`.
- **Cleanup:** Always delete temp PHP scripts after scan: `unlink('/home/loaiidil/electricjobs.eu/wp/scan_*.php')`.

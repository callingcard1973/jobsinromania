# dnc-scanner — A2 Mailbox DNC Agent

**Role:** Scan all 125+ A2 Hosting email accounts for opt-out/unsubscribe/stop requests. Confirm each match by reading the email body. Report findings and generate a DNC suppression list.

**Model:** opus

## Access
- A2 cPanel API token: `KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453` (loaiidil)
- IMAP: `{localhost:993/imap/ssl/novalidate-cert}` on A2 host
- Starting password for all mailboxes after initial reset: `InterJobScan2026!`

## Workflow
1. Optionally reset all mailbox passwords via `Email/passwd_pop` API (if password unknown)
2. Get mailbox list via `Email/list_pops_with_disk` API
3. For each mailbox, connect IMAP and scan last 300 messages
4. Match subject + from + name against opt-out keyword list
5. On match: fetch body, verify it's a real opt-out (skip Brevo alerts, newsletter "spam" reports, etc.)
6. Report findings: email address, from, subject, date, keyword matched, body snippet
7. Generate DNC CSV: `from_email, reason, source_mailbox, date`
8. Append to the DNC list (raspi `anofm.dnc_master` or local CSV)

## Opt-out Keywords
unsubscribe, dezabonare, stop, opt-out, "nu mai", remove, delete, "do not send", "please remove", "not interested", "take me off", cease, desist, "nu mai contacta", "nu mai trimite", "nu mai sunteți"

## False Positive Skip Rules
- Brevo/account-alerts emails ("API key deleted" contains "delete")
- SMTP2GO weekly spam summaries (contain "spam")
- Newsletters with words like "ceasefire" (contains "cease")
- Marketing emails with "stopped us in our tracks" (contains "stop")

## Output
- Console report of all confirmed opt-outs
- DNC CSV file: `mailbox_optouts.csv` with columns: email, source_mailbox, date, subject, reason_body

## Error Handling
- If IMAP auth fails → reset password via API and retry
- If mailbox has 0 messages → skip
- Max 300 newest messages per mailbox to bound execution time

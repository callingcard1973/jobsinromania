import imaplib, email, re
env = {}
with open('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env') as f:
    for l in f:
        if '=' in l and not l.startswith('#'):
            k, v = l.strip().split('=', 1)
            env[k] = v
imap = imaplib.IMAP4_SSL('nl1-cl8-ats1.a2hosting.com', 993)
imap.login('office@buildjobs.eu', env.get('A2_EMAIL_PASSWORD', ''))
imap.select('INBOX')
_, nums = imap.search(None, '(FROM "mailinblack")')
if nums[0]:
    for num in nums[0].split()[-2:]:
        _, data = imap.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        body = ''
        for part in (msg.walk() if msg.is_multipart() else [msg]):
            ct = part.get_content_type()
            if ct in ('text/plain', 'text/html'):
                body = part.get_payload(decode=True).decode(errors='replace')
                break
        urls = re.findall(r'https?://[^\s<>"\']+', body)
        print('Subject:', msg.get('Subject', '')[:80])
        for u in urls[:5]:
            print('CLICK:', u[:250])
        print()
imap.logout()

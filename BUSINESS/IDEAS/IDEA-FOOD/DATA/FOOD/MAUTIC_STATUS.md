# Mautic Installation Status

Created: 2026-03-21

## NOT THE SAME AS EEATINGH.RO

**eeatingh.ro** = Food delivery platform (like UberEats)
**Mautic** = Marketing automation platform (email campaigns, lead management)

Mautic is MORE relevant to your email campaign business.

## Access

| Item | Value |
|------|-------|
| URL | https://192.168.100.21/mautic/s/login |
| Username | admin |
| Password | Romania1973 |
| Email | tudor@interjob.ro |

## Current Data

| Item | Count |
|------|-------|
| Contacts | 214 |
| Email Templates | 1 |
| Campaigns | 0 |
| Users | 1 |

## Configuration

- **Version:** Mautic 7.0.1
- **Database:** MySQL `mautic` on localhost
- **PHP:** 8.4-fpm
- **Web Server:** Nginx

## Sender Accounts Available

### A2 Hosting SMTP (29 accounts, 50/day each)
See `/opt/ACTIVE/MAUTIC/SENDER_ACCOUNTS.md`

### Brevo SMTP (7 accounts, 290/day each)
See `/opt/ACTIVE/MAUTIC/SENDER_ACCOUNTS.md`

**Total Daily Capacity:** ~3,480 emails/day

## Cron Jobs (Set Up)

```
*/2 * * * * messenger:consume email
*/5 * * * * mautic:campaigns:trigger
*/15 * * * * mautic:campaigns:rebuild
*/15 * * * * mautic:segments:update
*/10 * * * * mautic:email:fetch
*/5 * * * * mautic:broadcasts:send
*/5 * * * * mautic:import
```

## Known Issues

1. **Database schema partially migrated** - Some cron jobs may fail due to missing columns
2. **Curl login test fails** - Try browser login directly

## Next Steps

1. Login via browser at https://192.168.100.21/mautic/s/login
2. Import contacts from CSV
3. Create email templates
4. Set up first campaign
5. Configure SMTP in Settings > Email Settings

## Documentation

- Setup guide: `/opt/ACTIVE/MAUTIC/SETUP.md`
- Sender accounts: `/opt/ACTIVE/MAUTIC/SENDER_ACCOUNTS.md`
- SMTP reference: `/opt/ACTIVE/MAUTIC/SMTP_DSN_REFERENCE.md`

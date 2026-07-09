# 01_senders_brevo — Senders per domeniu (Brevo relay + Gmail SMTP)

**Sursa canonica (single source of truth): raspibig**
- `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns.json` — 52 campanii, sender in `env.SENDER_EMAIL` (Brevo) sau `env.GMAIL_SENDER_EMAIL` (Gmail SMTP).
- `/opt/ACTIVE/SKILLS/email_accounts*.py` — Gmail app passwords (format cu spatii, 16 car). **Verifica prin login SMTP inainte de folosire; laptopul/memoria au avut valori corupte.**
- **API keys Brevo (`xkeysib-...`) si app passwords NU se scriu aici** — se citesc din campaigns.json pe raspibig. Acest folder e doar harta sender->domeniu.

## Doua cai de trimitere

| Cale | Cand | Camp campaigns.json | Limita |
|------|------|---------------------|--------|
| **Brevo relay** | destinatari non-Yahoo | `env.SENDER_EMAIL` + `brevo_account` + `env.BREVO_API_KEY` | pana la 290/zi/campanie |
| **Gmail SMTP** | destinatari @yahoo (DMARC strict) | `env.GMAIL_SENDER_EMAIL` + `env.GMAIL_APP_PASSWORD` + `env.REPLY_TO` | 50/zi/gmail (gentle) |

**Regula HARD (din CLAUDE.md): destinatari @yahoo => DOAR Gmail. Restul pe Brevo.**

## Conturi Brevo (relay, non-Yahoo)

| brevo_account | Sender | Reply-to | Campanii |
|---------------|--------|----------|----------|
| CUMPARLEGUME | `office@cumparlegume.com` | `office@cumparlegume.com` | PRIMARII, COOP_EXPORT, SILOZURI_CEREALE_11JUD (3) |
| BPPLTD | `office@bppltd.co.uk` | `manpower.dristor@gmail.com` | SONOMA_BREVO_BPPLTD (1) |
| FACTORYJOBS | `office@factoryjobs.eu` | `manpower.dristor@gmail.com` | SONOMA_BREVO_FACTORYJOBS (1) |
| (fara account, sender direct) | `export@bppltd.co.uk` | — | EXPORT_PEPENI_BPP |
| (fara account, sender direct) | `office@farmworkers.eu` | — | EXPORT_PEPENI_FARM |
| (fara account, sender direct) | `office@seicarescu.com` | — | EXPORT_PEPENI_SEI |
| (fara account, sender direct) | `vegetablesbucharest@gmail.com` | — | SUPERMARKETURI (via Brevo cu sender Gmail verificat) |

## Conturi Gmail (SMTP, pentru @yahoo)

| Gmail sender | App password alias | Campanii Yahoo |
|--------------|--------------------|----------------|
| `cumparlegume@gmail.com` | cumparlegume | SILOZURI_CEREALE_11JUD_GMAIL_CUMPARLEGUME |
| `vegetablesbucharest@gmail.com` | vegetables | SILOZURI_CEREALE_11JUD_GMAIL_VEGETABLES |
| `fructexportromania@gmail.com` | fructexport | SILOZURI_CEREALE_11JUD_GMAIL_FRUCTEXPORT |
| `manpower.dristor@gmail.com` | (manpower) | FACTORY_RO, SONOMA_AGENTII, SONOMA_G1/G2/G3 (+ altele cu sender in script) |
| `elena.manpower.dristor@gmail.com` | (elena) | EXPORT_AT + 17 campanii (sender hardcoded in script) |

**App passwords (valori):** vezi CLAUDE.md root (cumparlegume/vegetables/fructexport) dar **verifica pe raspibig** inainte de folosire. manpower/elena app passwords doar in campaigns.json pe raspibig.

## Campanii cu sender in script (nu in campaigns.json env)
SME_DEFICIT, NECALIFICATI, BDA_ARHITECTI, SILOZURI_BREVO, SILOZURI_GMAIL_CUMPARLEGUME/VEGETABLES/FRUCTEXPORT — senderul e hardcoded in `campaign_*.py`. De documentat per-script daca se reuseaza.

## Reguli
- Sender custom in orchestrator email trebuie sa accepte `--limit --delay --daily-cap` (altfel exit 2).
- Orchestrator reincarca campaigns.json doar la `systemctl restart campaign-orchestrator.service`.
- 1 sender Gmail = max 50/zi (gentle). Brevo = max 290/zi/campanie.
- Nu publica API keys / app passwords in fisiere sync-uite pe GitHub.

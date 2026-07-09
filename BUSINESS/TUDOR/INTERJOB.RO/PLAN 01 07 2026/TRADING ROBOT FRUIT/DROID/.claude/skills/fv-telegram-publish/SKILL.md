---
name: fv-telegram-publish
description: Publica ofertele/cererile de legume pe canalul Telegram public @cumparlegume via botul @cumparlegume_bot. Oglinda lui fv-fb-publish. Use cand utilizatorul cere 'posteaza pe telegram', 'da pe canalul cumparlegume', 'publica oferte pe telegram', 'ce postam pe TG azi', sau dupa un trading cycle. Re-rulari: 'reposteaza pe telegram', 'verifica bot telegram'. Default dry-run; live DOAR la 'posteaza pe bune'/'--post' dupa aprobare.
---

# fv-telegram-publish

Trimite `DATA/offers_ledger.jsonl` pe canalul **@cumparlegume** via Telegram Bot API.

## Reuse map
- Build text: `CODE/posteaza_oferte_facebook.py` (`build_post`, `load_ledger`) — ACELASI text ca FB.
- Ciclu: `CODE/fv_telegram_publisher.py` (curate + dedup + bot-health + sendMessage).
- Token + chat_id: `DATA/telegram_cumparlegume.json` (gitignored). NU printa tokenul.

## Gate
Default = **dry-run** (printeaza textul). Live doar la `--post` dupa aprobare
numerotata. Prezinta datele, opreste-te, asteapta GO.

## Pasi
1. `python CODE/fv_telegram_publisher.py` — build + curate (dedup pe `tg_post_log.json`, cap 1/zi).
2. **Dry-run:** printeaza textul + decizia curate. Stop.
3. **Live (`--post`):** bot-health (getMe); daca token invalid, oprire. Altfel
   `sendMessage` catre @cumparlegume, inregistreaza `message_id`.
4. Scrie `tg_post_log.json`.

## Why
Acelasi continut pe FB si Telegram = mesaj unic, dublu canal. Dedup + cap previn
spam-ul. Bot-health pre-check opreste rularile moarte cand tokenul e revocat.

## Blocaj posibil
`chat_id` gol => botul nu e admin pe canal sau canalul nu e setat. Adauga
@cumparlegume_bot ca admin si pune `@cumparlegume` in config.

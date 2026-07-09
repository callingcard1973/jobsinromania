---
name: fv-fb-publish
description: Publica ofertele/cererile de legume-fructe pe pagina Facebook Cumpar Legume cu ciclu curate->dedup->gate->post->token-health. Portat din harness-ul InterJob PUBLISHING IN MY FB. Use cand utilizatorul cere 'posteaza pe FB', 'publica oferte pe facebook', 'fb publish legume', 'da anuntul pe pagina cumparlegume', 'ce postam pe FB azi', sau dupa un trading cycle. Use si pentru re-rulari: 'reposteaza', 'verifica token FB', 'fb dry-run'. Default dry-run; live DOAR la 'posteaza pe bune'/'--post' dupa aprobare.
---

# fv-fb-publish

Posteaza `DATA/offers_ledger.jsonl` pe pagina **Cumpar Legume**, apoi verifica.

## Reuse map
- Build text: `CODE/posteaza_oferte_facebook.py` (`build_post`, `load_ledger`, `load_config`).
- Ciclu complet: `CODE/fv_fb_publisher.py` (curate + dedup + token-health + post).
- Token + page_id: `DATA/fb_cumparlegume.json`. NU printa valoarea tokenului.

## Gate (important)
Default = **dry-run**: printeaza anuntul exact, fara apel Graph API. Live DOAR la
instructiune explicita „posteaza pe bune" / `--post`, dupa aprobare numerotata.
Prezinta datele, opreste-te, asteapta GO de la Tudor.

## Pasi
1. `python CODE/fv_fb_publisher.py` — construieste anuntul, ruleaza **curate**:
   - exclude `internal_only` si `entry_type=request` din OFERIM (Vointa = referinta).
   - **dedup**: hash continut vs `fb_post_log.json`; SKIP daca deja postat azi.
   - **cap zilnic**: max 1 postare/zi/pagina.
2. **Dry-run:** printeaza textul + decizia curate. Stop.
3. **Live (`--post`):** verifica token health (GET /me); daca expirat (cod 190),
   raporteaza si NU posta. Altfel POST `/{page}/feed`, inregistreaza `post_id`.
4. Scrie `fb_post_log.json` (date, content_hash, status, post_id|error).

## Token health
Inainte de orice POST: GET `/me?fields=id,name`. Token expirat => oprire cu mesaj
„pune Page Access Token proaspat in fb_cumparlegume.json". Pre-checkul evita
esecuri silentioase cand tokenul long-lived expira.

## Why
Dry-run gate previne postari de masa accidentale. Dedup pe continut + post_id
previne repostarea aceluiasi anunt. Token pre-check opreste rularile moarte.

## Blocaj curent
`access_token` gol in `fb_cumparlegume.json` (tokenuri vechi expirate, cod 190).
Pana se pune un Page Access Token proaspat, ciclul ramane dry-run.

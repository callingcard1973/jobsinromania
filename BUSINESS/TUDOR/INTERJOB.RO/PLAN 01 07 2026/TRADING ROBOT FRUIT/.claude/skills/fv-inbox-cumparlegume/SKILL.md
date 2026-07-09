---
name: fv-inbox-cumparlegume
description: Inspecteaza inboxurile CUMPARLEGUME (cumparlegume@gmail.com + raspunsuri la office@cumparlegume.com) pentru oferte/cereri/raspunsuri legume-fructe. Read-only IMAP, fara marcare citit/stergere. Use cand utilizatorul cere 'inspecteaza inbox cumparlegume', 'verifica raspunsuri office@cumparlegume', 'ce oferte/cereri au venit pe gmail', 'citeste mailuri F&V cumparlegume', sau dupa o campanie COOP_EXPORT ca sa prinzi replicile. Complementar fv-email-poller (Yahoo) si campaign-reply-handler (clasificare generica).
---

# Skill: fv-inbox-cumparlegume

**Executie:** sub-agent fv-trader. Read-only.

## Context
- `office@cumparlegume.com` = sender Brevo (DOAR trimite). Raspunsurile la
  campaniile COOP_EXPORT cad pe **cumparlegume@gmail.com**.
- Credentiale (sursa de adevar = raspibig `/opt/ACTIVE/SKILLS/email_accounts*.py`):
  `cumparlegume@gmail.com`, app pw IMAP din raspibig email_accounts (16 car cu
  spatii), `imap.gmail.com`. Verifica prin login inainte; NU hardcoda parola in cod/commit.

## Ce face
1. Ruleaza `CODE/inspecteaza_inbox_fv.py cumparlegume@gmail.com "<pw>" <zile>`
   (read-only: BODY.PEEK, fara flaguri, fara stergere).
2. Filtreaza pe cuvinte-cheie F&V (produse + oferta/pret/tone/cooperativa/conserve).
3. Listeaza expeditor + subiect + data.

## Faze (cand se cere procesare, nu doar listare)
1. **Listare** — mailuri F&V din ultimele N zile (default 30).
2. **Triere** — oferta (furnizor cu pret) vs cerere (cumparator) vs raspuns campanie
   (interested/opt_out/bounce).
3. **Memoreaza** — oferta -> `fv-offer-extractor` -> offers_ledger; cerere ->
   requests_ledger; opt_out/bounce -> marcheaza pentru DNC unificat.
4. **Raport numerotat** Tudor (fara scoruri).

## Reguli
- Read-only. Niciun mail trimis/sters/marcat. Send = gated, alt skill.
- Email ASCII. Fara scoruri afisate.
- Daca login esueaza: raporteaza, nu reincerca cu alta parola la intamplare.
- opt_out/bounce => DNC, nu raspuns.

## Referinte
- `CODE/inspecteaza_inbox_fv.py` — inspectorul IMAP read-only
- `fv-email-poller` — echivalent pentru Yahoo (apaminerala@yahoo.com)
- `campaign-reply-handler` — clasificare generica replici campanii
- `fv-trading-orchestrator` — orchestratorul care cheama acest skill in Phase 1

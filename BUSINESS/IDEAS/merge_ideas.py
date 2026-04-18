import csv, shutil, os
from datetime import date

CSV = "MASTER.csv"
TODAY = str(date.today())

# Each group: (keep_id, [merge_ids], new_name, merged_description)
MERGES = [
    (3, [59, 119], "INSOLVENTA ALERTS",
     "Subscription alerte insolventa: 770K companii monitorizate + 222K falimentare + date ANAF live. "
     "Tinte: contabili, auditori, furnizori, agentii colectare. EUR 19-99/luna. Alerte zilnice email."),

    (8, [44, 65], "TELEGRAM LICITATII CHANNELS",
     "Canale Telegram cu alerte automate licitatii/tender: @FoodTendersRO (SEAP alimentar), "
     "@TenderAlerts (5.1M EU tenders cu filtre), @InsolvencyRO. Tier premium EUR 5-49/luna + bot versiune."),

    (2, [96, 97], "NORVEGIA RECRUITMENT",
     "Recrutare Norway multi-canal: email outreach 335K+ contacte norvegiene (agentii + angajatori directi "
     "constructii/oil/maritim) + organizare job fair (sponsorizare EUR 500-2000) + comision plasare EUR 500-1000/muncitor."),

    (9, [15, 34], "TED EU TENDER INTELLIGENCE",
     "Produse date licitatii EU: campanii email 13K+ castigatori TED + API/dashboard 5.1M tenders + "
     "newsletter saptamanal top CPV. Monetizare: per plasare + abonament API EUR 99-499/luna + spatiu reclama newsletter."),

    (154, [155, 156, 159], "FARM DISTRESSED SALES PLATFORM",
     "Platforma RE agricola: alerte saptamanale ferme vandute fortat (insolventa + licitatii silite BPI), "
     "listings investitori, catalog PDF 50+ ferme, broker achizitie pentru investitori NO/FI/NL (comision 2-3%). "
     "EUR 29-3000/luna diverse tiers."),

    (11, [74, 147], "COOPERATIVA AGRICOLA",
     "Cooperativa 140+ producatori montani: export EU legume/fructe + registru digital membri (CUI ANAF validat, "
     "documente pre-completate) + outreach 30K HORECA EU pentru produse. Taxa membru EUR 50-200/an + 5% comision vanzari."),

    (5, [27, 58, 108], "HORECA FOOD DISTRIBUTION",
     "Campanii B2B distributie alimentara: 28K+ contacte HORECA + 3030 castigatori SEAP alimentari + "
     "Freskon exhibitors. Email + WhatsApp outreach. Monetizare: EUR 500-5000/contract plasare sau comision broker."),

    (46, [67, 87, 136, 137], "CATALOG GENERATOR PLATFORM",
     "Generator cataloage white-label: angajatori/produse/tenders pe 9+ domenii x 20 tari. "
     "Output HTML → PDF → print-ready (KDP/Lulu). Agent-based QA. Monetizare: EUR 99/catalog custom, "
     "EUR 15-49/carte print Amazon KDP, EUR 500-2000/catalog print personalizat."),

    (14, [47, 73, 133], "COMPANY DATA API DASHBOARD",
     "Date companii live: 117K+ firme RO + 5.1M EU tenders + insolventa + contracte SEAP. "
     "Acces: CSV one-time vs dashboard abonament vs REST API vs bundle RapidAPI (ANAF+email+company+CV+insolventa). "
     "EUR 500-5000/luna dashboard, EUR 99-499/luna API, EUR 0.01-0.50/call."),

    (4, [49, 84, 90], "AGENTII RECRUTARE PLATFORM",
     "Enablement agentii recrutare: DB + campanii + unelte white-label pentru 18K+ agentii UE. "
     "Muncitori RO plasati in UE/international. Monetizare: EUR 420K+/an plasari + EUR 2K-10K/luna broker leads "
     "+ EUR 200-500/luna catalog white-label + licenta franciza EUR 500-2000/luna."),

    (69, [102, 131], "EXPAT RELOCATION SERVICES",
     "Monetizare relocation expati: retea 1166 furnizori (consultanti fiscali, avocati, contabili) + "
     "pachete corporatiste relocation. Comision 10-15% per referral (EUR 50-150) + EUR 500/persoana pachet complet "
     "(documente, cazare, asigurare, transport)."),

    (30, [45, 60], "EMAIL CLASSIFIER SAAS",
     "Clasificator email SaaS: model sklearn (94.5% acuratete) + LLM auto-responder + generare draft Gmail. "
     "API B2B pentru agentii recrutare, imobiliare, logistica. EUR 29-149/luna per client, 1000+ clasificari."),

    (92, [99, 117], "JOB FAIR PLATFORM",
     "Platforma job fair virtual + fizic pe 28 domenii. Angajatori platesc EUR 200-500/stand. "
     "Tiers: evenimente fizice (Bucuresti/Hunedoara), online reverse job fairs (buildjobs.eu), "
     "expansiune internationala (FI/DK/DE/NL, EUR 15-30K/targ)."),

    (36, [132], "INSOLVENTA ACTIVE ASSETS",
     "Monetizare active insolventa: 222K companii falimentare + proprietati vandute fortat BPI. "
     "Investitori/flippers platesc per lead EUR 5-20 sau abonament alerte. "
     "8 fluxuri venituri: licitatii ANAF, BPI, proprietati stat, creante, ferme/imobiliare in dificultate."),

    (68, [81, 104, 124, 149], "NEWSLETTER PROCUREMENT JOBS",
     "Newsletter-uri B2B nisa via Substack/Mailrelay: EU tenders (EUR 19-49/luna), job alerts (EUR 5/luna), "
     "joburi Norvegia (EUR 50/post premium), procurement intelligence (EUR 99/luna), digest CPV top sectoare. "
     "Monetizare: abonament + listings sponsorizate EUR 50-200 per 1000 emailuri."),

    (1, [98, 145, 148], "GUMROAD DATA PRODUCTS",
     "Produse date CSV/PDF pe Gumroad one-time: firme constructii RO, castigatori TED pe tara+sector, "
     "date insolventa, ferme la vanzare, bundle toate. Pret EUR 29-199/dataset. Venit pasiv post-publicare."),

    (111, [112, 115, 116], "NORWAY WORKER SUPPLY CHAIN",
     "Servicii complete muncitori Norvegia: CV database de pe buildjobs.eu/no/ (EUR 20-50/CV agentii), "
     "sponsorizare job fair (EUR 500-2000), curs norvegiana Gumroad (EUR 19), brokeraj cazare (EUR 100-200/plasare)."),

    (86, [94, 113, 114], "WORKER DOCUMENTATION SERVICE",
     "Serviciu documentatie relocare muncitori: EUR 100-300/dosar pentru permise, vize, contracte munca, "
     "declaratii A1, setup payroll, D-number norvegian, cont bancar, training pre-plecare. "
     "50+ dosare/luna = EUR 5-15K venituri."),

    (6, [35], "BULGARIA ALUMINUM CAMPAIGNS",
     "Campanii recrutare sectoare specifice: 79K contacte Bulgaria constructii + 611 companii reciclare aluminiu. "
     "Comision plasare muncitori EUR 3000-5000. Acelasi model DB→campanie ca Norvegia."),

    (77, [135], "SEAP BIDDING ASSISTANT",
     "Asistenta licitare SEAP/TED: consultanti ajuta firme sa liciteze folosind DB 5.1M tenders + "
     "draft propuneri auto-generate LLM. Monetizare: EUR 200-500/oferta + 5% taxa succes sau EUR 50-200/propunere LLM."),

    (63, [121], "CV LINKEDIN ENRICHMENT API",
     "Enrichment date recrutare: CV parsing API (EUR 0.50-2/CV, 100/zi = EUR 50-200/zi) + "
     "scraper LinkedIn profile (EUR 0.10/profil, 50K/luna = EUR 5K). Agentii cumpara profile imbogatite candidati + decidenti."),

    (85, [126], "WORKER INSURANCE BROKER",
     "Brokeraj asigurari muncitori: plasati au nevoie de acoperire medicala + accidente. "
     "Parteneriat ALLIANZ/GROUPAMA. Comision 10-20% din prima. 100+ plasari/luna = EUR 2-5K + sezoniere EUR 50-100/polita."),

    (70, [155], "MADR LAND INVESTOR DATA",
     "Date investitii teren agricol: 9658+ listari anuale vanzari teren x 36 judete + licitatii MADR + "
     "vanzari silite ferme (BPI). Abonament EUR 99-299/luna pentru investitori, fonduri PE, fermieri mici."),

    (43, [61, 66, 79, 82, 127], "COMPANY DATA ENRICHMENT PLATFORM",
     "Platforma enrichment date companii: CUI → lookup ANAF → validare email → extractie bilant → status live. "
     "Tiers monetizare: EUR 0.05-0.20/record enrichment bulk + EUR 5-20/raport companie "
     "(ANAF+bilant+insolventa+SEAP+angajati) + EUR 0.02-0.10/record curatare date + EUR 200/raport economic judet."),

    (29, [42, 100], "DELECROIX AGRI EQUIPMENT",
     "Parteneriat distributie echipamente recoltare Delecroix (benzi transportoare, remorci legume, statii sortare). "
     "Canal vanzare: analiza concurenta + outreach Norvegia (firme agricole) + cooperativa/fermieri mici RO. "
     "Comision 10% pe vanzare."),

    (128, [], "COMPETITOR MONITORING SAAS",
     "Monitorizare concurenta SaaS: client da lista CUI → sistem urmareste contracte SEAP, schimbari ANAF, "
     "risc insolventa, pattern angajari. EUR 99/luna. Date deja in DB."),
]

# Build lookup: id -> row dict
rows = {}
order = []
with open(CSV, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        id_ = int(row['ID'].replace('IDEA-', ''))
        rows[id_] = row
        order.append(id_)

# Build merged_into map
merged_into = {}
for keep, merge_ids, name, desc in MERGES:
    for mid in merge_ids:
        merged_into[mid] = keep

# Apply merges
for keep, merge_ids, name, desc in MERGES:
    if keep not in rows:
        continue
    rows[keep]['Proiect'] = name
    rows[keep]['Ce_face'] = desc
    rows[keep]['Actualizare'] = TODAY
    # merge revenue/effort: keep max effort
    for mid in merge_ids:
        if mid in rows:
            try:
                keep_e = float(rows[keep]['Efort_ore'])
                merge_e = float(rows[mid]['Efort_ore'])
                if merge_e > keep_e:
                    rows[keep]['Efort_ore'] = rows[mid]['Efort_ore']
            except:
                pass

# Mark merged rows
for mid, keep in merged_into.items():
    if mid in rows:
        rows[mid]['Status'] = 'MERGED'
        rows[mid]['Ce_face'] = f'→ contopita in IDEA-{keep:03d}'
        rows[mid]['Venit_EUR'] = ''
        rows[mid]['Actualizare'] = TODAY

# Write back
backup = CSV.replace('.csv', '_backup_before_merge.csv')
shutil.copy(CSV, backup)
print(f"Backup: {backup}")

with open(CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for id_ in order:
        writer.writerow(rows[id_])

# Stats
merged_count = sum(1 for v in rows.values() if v['Status'] == 'MERGED')
active_count = len(rows) - merged_count
print(f"Total idei: {len(rows)}")
print(f"MERGED (duplicate): {merged_count}")
print(f"Active unice: {active_count}")
print("\nMerge-uri aplicate:")
for keep, merge_ids, name, _ in MERGES:
    if merge_ids:
        ids_str = '+'.join(f"IDEA-{m:03d}" for m in merge_ids)
        print(f"  IDEA-{keep:03d} {name} ← absorbit {ids_str}")

#!/usr/bin/env python3
"""
Multilingual email response templates for InterJob recruitment.
Used as fallback when LLM is unavailable and as context for LLM drafting.
"""

COMPANY_INFO = {
    "name": "InterJob Solutions Europe / BP&P Partners",
    "contact": "Tudor Seicarescu",
    "phone": "+40 771 028 948",
    "whatsapp": "+33 7 51 17 13 56",
    "email": "office@interjob.ro",
    "web": "https://interjob.ro",
    "services": "construction, HoReCa, industrial, agriculture workers",
    "origin": "Nepal, India, Bangladesh, Sri Lanka, Philippines",
}

# -- System prompts per language for LLM drafting --
SYSTEM_PROMPTS = {
    "en": f"""You draft professional email replies for {COMPANY_INFO['name']}, a European recruitment agency.
Services: supplying {COMPANY_INFO['services']} from {COMPANY_INFO['origin']}.
Free for employers. Processing: 4-8 months for work permits.
Contact: {COMPANY_INFO['contact']}, {COMPANY_INFO['phone']}, {COMPANY_INFO['email']}
Keep replies concise (3-6 sentences). Match the sender's language if possible.""",

    "ro": f"""Redactezi raspunsuri profesionale pentru {COMPANY_INFO['name']}, agentie de recrutare europeana.
Servicii: furnizare {COMPANY_INFO['services']} din {COMPANY_INFO['origin']}.
Gratuit pentru angajatori. Procesare: 4-8 luni pentru permise de munca.
Contact: {COMPANY_INFO['contact']}, {COMPANY_INFO['phone']}, {COMPANY_INFO['email']}
Raspunsuri concise (3-6 propozitii). Ton profesional, prietenos.""",

    "fr": f"""Vous redigez des reponses professionnelles pour {COMPANY_INFO['name']}, agence de recrutement europeenne.
Services: fourniture de {COMPANY_INFO['services']} depuis {COMPANY_INFO['origin']}.
Gratuit pour les employeurs. Delai: 4-8 mois pour permis de travail.
Contact: {COMPANY_INFO['contact']}, {COMPANY_INFO['phone']}, {COMPANY_INFO['email']}
Reponses concises (3-6 phrases). Ton professionnel.""",
}

# -- Fallback templates when LLM unavailable --
FALLBACK = {
    "inquiry": {
        "en": """Thank you for your interest in our recruitment services.

We supply qualified workers from Nepal, India, and Bangladesh for construction, HoReCa, and industrial sectors across Europe. Our service is free for employers.

Please let us know your specific requirements (number of workers, sector, timeline) and we will prepare a detailed proposal.

Best regards,
{contact} | {phone} | {email}""",

        "ro": """Va multumim pentru interesul acordat serviciilor noastre de recrutare.

Furnizam muncitori calificati din Nepal, India si Bangladesh pentru constructii, HoReCa si industrie in toata Europa. Serviciul este gratuit pentru angajatori.

Va rugam sa ne comunicati cerintele specifice (numar muncitori, sector, termen) si vom pregati o oferta detaliata.

Cu stima,
{contact} | {phone} | {email}""",

        "fr": """Merci pour votre interet pour nos services de recrutement.

Nous fournissons des travailleurs qualifies du Nepal, d'Inde et du Bangladesh pour la construction, l'hotellerie et l'industrie en Europe. Notre service est gratuit pour les employeurs.

Veuillez nous communiquer vos besoins specifiques (nombre, secteur, delai) et nous preparerons une proposition detaillee.

Cordialement,
{contact} | {phone} | {email}""",
    },

    "application": {
        "en": """Thank you for your application. We have received your CV and will review it shortly.

If your profile matches our current openings, we will contact you within 5 business days.

Please ensure your contact details are up to date.

Best regards,
{contact} | {email}""",

        "ro": """Va multumim pentru aplicatie. Am primit CV-ul dumneavoastra si il vom analiza in cel mai scurt timp.

Daca profilul corespunde pozitiilor disponibile, va vom contacta in maximum 5 zile lucratoare.

Cu stima,
{contact} | {email}""",

        "fr": """Merci pour votre candidature. Nous avons bien recu votre CV et l'examinerons prochainement.

Si votre profil correspond a nos postes actuels, nous vous contacterons sous 5 jours ouvrables.

Cordialement,
{contact} | {email}""",
    },

    "campaign_reply": {
        "en": """Thank you for your reply to our message.

We would be happy to discuss how we can support your workforce needs. Could you please share:
- How many workers you need?
- Which positions/sector?
- Preferred start date?

We will then prepare a tailored proposal.

Best regards,
{contact} | {phone} | {email}""",

        "ro": """Va multumim pentru raspuns la mesajul nostru.

Am fi bucurosi sa discutam cum va putem sprijini cu necesarul de personal. Va rugam sa ne comunicati:
- Cati muncitori aveti nevoie?
- Ce pozitii/sector?
- Data de inceput dorita?

Vom pregati o oferta personalizata.

Cu stima,
{contact} | {phone} | {email}""",

        "fr": """Merci pour votre reponse a notre message.

Nous serions ravis de discuter comment nous pouvons repondre a vos besoins en personnel. Pourriez-vous nous preciser:
- Combien de travailleurs avez-vous besoin?
- Quels postes/secteur?
- Date de debut souhaitee?

Nous preparerons une proposition adaptee.

Cordialement,
{contact} | {phone} | {email}""",
    },
}


def get_fallback(intent, lang="en"):
    """Get fallback template for intent + language."""
    tpl = FALLBACK.get(intent, FALLBACK.get("inquiry", {}))
    text = tpl.get(lang, tpl.get("en", ""))
    return text.format(**COMPANY_INFO)


def get_system_prompt(lang="en"):
    """Get LLM system prompt for language."""
    return SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])

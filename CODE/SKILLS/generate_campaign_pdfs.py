#!/usr/bin/env python3
"""
Campaign PDF Generator — All 6 campaigns, 38 languages each.
Cross-platform: runs on Windows (local) and Linux (raspibig).
Uses EURES pre-translated labels (zero tokens, fully offline).

Usage:
    python3 generate_all_campaigns.py --all
    python3 generate_all_campaigns.py --campaign FACTORYJOBS_RO
    python3 generate_all_campaigns.py --campaign BUILDJOBS_RO --lang en,ro
    python3 generate_all_campaigns.py --fetch   # fetch latest CSV first
"""
import csv
import os
import re
import sys
import platform
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

# ── Platform detection ──────────────────────────────────────────────────
IS_LINUX = platform.system() == 'Linux'
IS_WINDOWS = platform.system() == 'Windows'

SCRIPT_DIR = Path(__file__).resolve().parent

if IS_LINUX:
    # raspibig paths
    DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/PDF_CAMPAIGNS')
    ANOFM_CSV_DIR = Path('/mnt/hdd/SCRAPER_DATA/csv/ANOFM')
    FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
    LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/pdf_campaigns')
    sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
    sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES')
    sys.path.insert(0, str(SCRIPT_DIR))
else:
    # Windows local paths
    DATA_DIR = SCRIPT_DIR
    ANOFM_CSV_DIR = SCRIPT_DIR
    FONT_DIR = SCRIPT_DIR / 'fonts'
    LOG_DIR = SCRIPT_DIR / 'logs'

from eures_translations import TRANSLATIONS as EURES_T, LANGUAGES as EURES_LANGS
from cor_mapper import get_campaigns_for_cor, parse_cor_code

ALL_LANG_CODES = list(EURES_LANGS.keys())
MAX_JOBS_PER_PDF = 80

# Logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'campaign_pdfs_{datetime.now():%Y%m}.log'),
        logging.StreamHandler(),
    ],
)

# ── Campaign Configuration ──────────────────────────────────────────────
CAMPAIGN_CONFIG = {
    'FACTORYJOBS_RO': {
        'website': 'factoryjobs.eu',
        'apply_url': 'https://interjob.ro/apply.html',
        'pdf_prefix': 'factoryjobs',
        'remote_dir': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FACTORYJOBS_EU/website/',
        'employer_labels': [
            "Manufacturing Company", "Production Employer", "Factory Employer",
            "Industrial Company", "Manufacturing Firm", "Production Company",
            "Technical Employer", "Industrial Firm", "Assembly Company",
            "Processing Company",
        ],
    },
    'CAREWORKERS_RO': {
        'website': 'careworkers.eu',
        'apply_url': 'https://interjob.ro/apply.html',
        'pdf_prefix': 'careworkers',
        'remote_dir': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/CAREWORKERS_EU/website/',
        'employer_labels': [
            "Healthcare Provider", "Care Facility", "Medical Center",
            "Nursing Home", "Health Employer", "Care Institution",
            "Clinical Employer", "Medical Employer", "Wellness Center",
            "Healthcare Employer",
        ],
    },
    'BUILDJOBS_RO': {
        'website': 'buildjobs.eu',
        'apply_url': 'https://interjob.ro/apply.html',
        'pdf_prefix': 'buildjobs',
        'remote_dir': '/opt/ACTIVE/OPENDATA/DATA/PDF_CAMPAIGNS/BUILDJOBS_RO/',
        'employer_labels': [
            "Construction Company", "Building Contractor", "Civil Works Firm",
            "Construction Employer", "Building Company", "Infrastructure Firm",
            "Construction Contractor", "Building Employer", "Structural Works Co.",
            "Construction Enterprise",
        ],
    },
    'HORECA_RO': {
        'website': 'horecaworkers.eu',
        'apply_url': 'https://interjob.ro/apply.html',
        'pdf_prefix': 'horeca',
        'remote_dir': '/opt/ACTIVE/OPENDATA/DATA/PDF_CAMPAIGNS/HORECA_RO/',
        'employer_labels': [
            "Restaurant Employer", "Hotel & Catering", "Hospitality Company",
            "Food Service Employer", "Restaurant Chain", "Catering Company",
            "Hotel Employer", "Hospitality Group", "Dining Establishment",
            "Hospitality Employer",
        ],
    },
    'DRIVERS_RO': {
        'website': None,
        'apply_url': 'https://interjob.ro/apply.html',
        'pdf_prefix': 'drivers',
        'remote_dir': '/opt/ACTIVE/OPENDATA/DATA/PDF_CAMPAIGNS/DRIVERS_RO/',
        'employer_labels': [
            "Transport Company", "Logistics Employer", "Freight Company",
            "Delivery Employer", "Haulage Firm", "Transport Employer",
            "Logistics Firm", "Shipping Company", "Distribution Co.",
            "Transport Enterprise",
        ],
    },
    'WAREHOUSE_RO': {
        'website': 'warehouseworkers.eu',
        'apply_url': 'https://interjob.ro/apply.html',
        'pdf_prefix': 'warehouse',
        'remote_dir': '/opt/ACTIVE/OPENDATA/DATA/PDF_CAMPAIGNS/WAREHOUSE_RO/',
        'employer_labels': [
            "Logistics Company", "Warehouse Employer", "Distribution Center",
            "Storage Facility", "Logistics Employer", "Supply Chain Co.",
            "Warehouse Firm", "Logistics Enterprise", "Fulfillment Center",
            "Warehouse Company",
        ],
    },
}

# ── Keyword fallback filters (when COR code missing) ───────────────────
FALLBACK_KEYWORDS = {
    'FACTORYJOBS_RO': re.compile(
        r'fabrica|productie|manufacturing|factory|operator.*masini|mecanic|strung|CNC|'
        r'montator|manipulant|ambalator|muncitor.*necalificat|linie.*productie|asamblor|'
        r'confectioner|sudor|lacatus|frezor|rectificator|strungar|bobinator|cablor|'
        r'galvanizator|oxigenist|debitor|carosier|pistolar|brutar|cofetar|macelar|'
        r'lemn|mobila|rindeluitor|sortator|controlul.calitatii',
        re.IGNORECASE),
    'BUILDJOBS_RO': re.compile(
        r'constructor|constructii|zidar|betonist|fierar.*beton|dulgher|instalator|'
        r'electrician.*construct|tencuitor|zugrav|faiantar|pavator|montator.*construct|'
        r'macaragiu|excavator|sapator|izolator|tinichigiu|terasament|drumuri|pod',
        re.IGNORECASE),
    'CAREWORKERS_RO': re.compile(
        r'infirmier|asistent.*medical|ingrijitor|babysitter|bona|medic|farmacist|'
        r'kinetoterapeut|nurse|caregiver|batrani|copii.*supraveghe|moasa|brancardier',
        re.IGNORECASE),
    'HORECA_RO': re.compile(
        r'bucatar|ospatar|barman|receptioner|camerist|chelner|pizzar|patiser|cofetar|'
        r'hotel|restaurant|catering|cantina|ajutor.*bucatar|spalator.*vase',
        re.IGNORECASE),
    'DRIVERS_RO': re.compile(
        r'sofer|conducator.*auto|camion|tir|autocar|autobuz|curier|livrator|'
        r'transport|taxi|masina|vehicul.*greu',
        re.IGNORECASE),
    'WAREHOUSE_RO': re.compile(
        r'depozit|warehouse|magazioner|gestionar|stivuitor|logistic|picking|packing|'
        r'manipulant.*marfa|operator.*depozit|lucrator.*depozit|ambalator|inventar|'
        r'expeditor|receptor.*marfar',
        re.IGNORECASE),
}

# ── Campaign-specific translated strings ────────────────────────────────
# Title per campaign in all available languages (en fallback for missing)
CAMPAIGN_TITLES = {
    'FACTORYJOBS_RO': {
        'ro': 'Locuri de Munca in Fabrici si Productie - Romania',
        'en': 'Factory & Production Jobs - Romania',
        'de': 'Fabrik- & Produktionsjobs - Rumaenien',
        'fr': 'Emplois en Usine & Production - Roumanie',
        'es': 'Empleos en Fabrica y Produccion - Rumania',
        'it': 'Lavori in Fabbrica e Produzione - Romania',
        'pt': 'Empregos em Fabrica e Producao - Romenia',
        'pl': 'Praca w Fabryce i Produkcji - Rumunia',
        'nl': 'Fabrieks- & Productiebanen - Roemenie',
        'hu': 'Gyari es Termelesi Allasok - Romania',
        'cs': 'Prace v Tovarne a Vyrobe - Rumunsko',
        'sk': 'Praca v Tovarni a Vyrobe - Rumunsko',
        'bg': 'Fabrichni i Proizvodstveni Raboti - Rumaniya',
        'ru': 'Rabota na Zavode i Proizvodstve - Rumyniya',
        'uk': 'Robota na Zavodi ta Vyrobnytstvi - Rumuniya',
        'hr': 'Tvornicki i Proizvodni Poslovi - Rumunjska',
        'sr': 'Fabricki i Proizvodni Poslovi - Rumunija',
        'sl': 'Tovarniska in Proizvodna Dela - Romunija',
        'sq': 'Pune ne Fabrike dhe Prodhim - Rumani',
        'mk': 'Fabricki i Proizvodstveni Raboti - Romanija',
        'da': 'Fabriks- og Produktionsjob - Rumaenien',
        'sv': 'Fabriks- och Produktionsjobb - Rumanien',
        'fi': 'Tehdas- ja Tuotantotyot - Romania',
        'no': 'Fabrikk- og Produksjonsjobber - Romania',
        'lt': 'Gamykliniai ir Gamybiniai Darbai - Rumunija',
        'lv': 'Rupnicas un Razosanas Darbi - Rumanija',
        'et': 'Tehase- ja Tootmistood - Rumeenia',
        'el': 'Ergasies se Ergostasio kai Paragogi - Roumania',
        'hi': 'Factory aur Utpadan Naukariyan - Romania',
        'ne': 'Karkhana ra Utpadan Rojgari - Romania',
        'ur': 'Factory aur Paidawar ki Naukriyan - Romania',
        'ar': 'Wazaif al-Masani wal-Intaj - Romania',
        'bn': 'Karkhana o Utpadan Chakri - Romania',
        'pa': 'Factory ate Utpadan Naukariyan - Romania',
        'vi': 'Viec lam Nha may & San xuat - Romania',
        'uz': 'Fabrika va Ishlab chiqarish Ishlari - Ruminiya',
        'ps': 'Da Fabrikay aw Tolid Danday - Romania',
        'am': 'YeFabrika Ina Mirt Siraoch - Romania',
    },
    'CAREWORKERS_RO': {
        'ro': 'Locuri de Munca in Sanatate si Ingrijire - Romania',
        'en': 'Healthcare & Care Worker Jobs - Romania',
        'de': 'Gesundheits- & Pflegejobs - Rumaenien',
        'fr': "Emplois Sante & Aide-soignant - Roumanie",
        'es': 'Empleos en Salud y Cuidados - Rumania',
        'it': 'Lavori Sanita e Assistenza - Romania',
        'pt': 'Empregos em Saude e Cuidados - Romenia',
        'pl': 'Praca w Opiece Zdrowotnej - Rumunia',
        'nl': 'Zorg- & Verpleegbanen - Roemenie',
        'hu': 'Egeszsegugyi es Gondozoi Allasok - Romania',
        'cs': 'Prace ve Zdravotnictvi a Peci - Rumunsko',
        'bg': 'Raboti v Zdraveopazvaneto - Rumaniya',
        'ru': 'Rabota v Zdravookhranenii - Rumyniya',
        'uk': 'Robota v Okhoroni Zdorovya - Rumuniya',
        'hi': 'Swasthya aur Dekhbhal Naukariyan - Romania',
        'ne': 'Swasthya ra Hherchaha Rojgari - Romania',
        'ar': 'Wazaif al-Riaaya al-Sihhiya - Romania',
        'vi': 'Viec lam Cham soc Suc khoe - Romania',
    },
    'BUILDJOBS_RO': {
        'ro': 'Locuri de Munca in Constructii - Romania',
        'en': 'Construction Jobs - Romania',
        'de': 'Baujobs - Rumaenien',
        'fr': 'Emplois dans la Construction - Roumanie',
        'es': 'Empleos en Construccion - Rumania',
        'it': 'Lavori Edili - Romania',
        'pt': 'Empregos na Construcao - Romenia',
        'pl': 'Praca w Budownictwie - Rumunia',
        'nl': 'Bouwbanen - Roemenie',
        'hu': 'Epitoipari Allasok - Romania',
        'cs': 'Prace ve Stavebnictvi - Rumunsko',
        'bg': 'Stroitelni Raboti - Rumaniya',
        'ru': 'Rabota v Stroitelstve - Rumyniya',
        'uk': 'Robota v Budivnytstvi - Rumuniya',
        'hi': 'Nirman Naukariyan - Romania',
        'ne': 'Nirman Rojgari - Romania',
        'ar': 'Wazaif al-Binaa - Romania',
        'vi': 'Viec lam Xay dung - Romania',
    },
    'HORECA_RO': {
        'ro': 'Locuri de Munca in Hoteluri, Restaurante si Catering - Romania',
        'en': 'Hotel, Restaurant & Catering Jobs - Romania',
        'de': 'Hotel-, Restaurant- & Cateringjobs - Rumaenien',
        'fr': "Emplois Hotellerie, Restauration & Traiteur - Roumanie",
        'es': 'Empleos en Hosteleria y Restauracion - Rumania',
        'it': 'Lavori Hotel, Ristorante e Catering - Romania',
        'pt': 'Empregos em Hotelaria e Restauracao - Romenia',
        'pl': 'Praca w Hotelarstwie i Gastronomii - Rumunia',
        'nl': 'Horeca Vacatures - Roemenie',
        'hu': 'Szalloda es Vendeglatas Allasok - Romania',
        'cs': 'Prace v Hotelnictvi a Gastronomii - Rumunsko',
        'bg': 'Raboti v Hotelierstvoto i Restorantiorstvoto - Rumaniya',
        'ru': 'Rabota v Gostinichnom i Restorannom Biznese - Rumyniya',
        'uk': 'Robota v Gotelyakh ta Restoranakh - Rumuniya',
        'hi': 'Hotel, Restaurant aur Catering Naukariyan - Romania',
        'ne': 'Hotel, Restaurant ra Catering Rojgari - Romania',
        'ar': 'Wazaif al-Fanaadiq wal-Mataaim - Romania',
        'vi': 'Viec lam Khach san & Nha hang - Romania',
    },
    'DRIVERS_RO': {
        'ro': 'Locuri de Munca pentru Soferi si Transport - Romania',
        'en': 'Driver & Transport Jobs - Romania',
        'de': 'Fahrer- & Transportjobs - Rumaenien',
        'fr': 'Emplois Chauffeur & Transport - Roumanie',
        'es': 'Empleos de Conductor y Transporte - Rumania',
        'it': 'Lavori Autista e Trasporti - Romania',
        'pt': 'Empregos de Motorista e Transporte - Romenia',
        'pl': 'Praca Kierowcy i Transport - Rumunia',
        'nl': 'Chauffeurs- & Transportbanen - Roemenie',
        'hu': 'Sofor es Szallitmanyozasi Allasok - Romania',
        'cs': 'Prace Ridice a Dopravy - Rumunsko',
        'bg': 'Raboti za Shofori i Transport - Rumaniya',
        'ru': 'Rabota Voditelya i Transport - Rumyniya',
        'uk': 'Robota Vodiya ta Transport - Rumuniya',
        'hi': 'Driver aur Parivahan Naukariyan - Romania',
        'ne': 'Driver ra Yatayat Rojgari - Romania',
        'ar': 'Wazaif al-Saaiq wal-Naql - Romania',
        'vi': 'Viec lam Tai xe & Van tai - Romania',
    },
    'WAREHOUSE_RO': {
        'ro': 'Locuri de Munca in Depozite si Logistica - Romania',
        'en': 'Warehouse & Logistics Jobs - Romania',
        'de': 'Lager- & Logistikjobs - Rumaenien',
        'fr': "Emplois Entrepot & Logistique - Roumanie",
        'es': 'Empleos en Almacen y Logistica - Rumania',
        'it': 'Lavori Magazzino e Logistica - Romania',
        'pt': 'Empregos em Armazem e Logistica - Romenia',
        'pl': 'Praca w Magazynie i Logistyce - Rumunia',
        'nl': 'Magazijn- & Logistiekbanen - Roemenie',
        'hu': 'Raktari es Logisztikai Allasok - Romania',
        'cs': 'Prace ve Skladu a Logistice - Rumunsko',
        'bg': 'Raboti v Sklad i Logistika - Rumaniya',
        'ru': 'Rabota na Sklade i v Logistike - Rumyniya',
        'uk': 'Robota na Skladi ta v Logistytsi - Rumuniya',
        'hi': 'Warehouse aur Logistics Naukariyan - Romania',
        'ne': 'Warehouse ra Logistics Rojgari - Romania',
        'ar': 'Wazaif al-Mustaudaat wal-Imadaad - Romania',
        'vi': 'Viec lam Kho bai & Hau can - Romania',
    },
}

# Shared translations (subtitle, intro, notices)
SHARED_STRINGS = {
    'subtitle': {
        'ro': 'Oportunitati de angajare din surse guvernamentale oficiale',
        'en': 'Employment opportunities from official government sources',
        'de': 'Beschaeftigungsmoeglichkeiten aus offiziellen Regierungsquellen',
        'fr': "Opportunites d'emploi provenant de sources gouvernementales officielles",
        'es': 'Oportunidades de empleo de fuentes gubernamentales oficiales',
        'it': 'Opportunita di lavoro da fonti governative ufficiali',
        'pt': 'Oportunidades de emprego de fontes governamentais oficiais',
        'pl': 'Oferty pracy ze zrodel rzadowych',
        'nl': 'Werkgelegenheid uit officiele overheidsbronnen',
        'hu': 'Allaslehetosegek hivatalos kormanyzati forrasokbol',
        'cs': 'Pracovni prilezitosti z oficialnich vladnich zdroju',
        'bg': 'Vazmoznosti za rabota ot ofitsialni pravitelstveni iztochnitsi',
        'ru': 'Vakansii iz ofitsialnykh gosudarstvennykh istochnikov',
        'uk': 'Vakansii z ofitsiynykh derzhavnykh dzherel',
    },
    'intro_line1': {
        'ro': 'Toate informatiile din acest document sunt preluate de pe site-urile guvernamentale ale Romaniei si din bazele de date publice oficiale de ocupare a fortei de munca (ANOFM).',
        'en': 'All information in this document is sourced from Romanian government websites and official public employment databases (ANOFM - National Employment Agency).',
        'de': 'Alle Informationen in diesem Dokument stammen von rumaenischen Regierungswebseiten und offiziellen Beschaeftigungsdatenbanken (ANOFM).',
        'fr': "Toutes les informations de ce document proviennent des sites gouvernementaux roumains et des bases de donnees officielles de l'emploi (ANOFM).",
        'es': 'Toda la informacion de este documento proviene de sitios web gubernamentales rumanos y bases de datos oficiales de empleo (ANOFM).',
    },
    'intro_line2': {
        'ro': 'Aceste oportunitati sunt destinate in principal candidatilor aflati deja in Romania, dar aplicarile sunt deschise tuturor.',
        'en': 'These opportunities are primarily for candidates already located in Romania, but applications are open to everyone.',
        'de': 'Diese Moeglichkeiten richten sich hauptsaechlich an Kandidaten in Rumaenien, aber Bewerbungen stehen allen offen.',
        'fr': 'Ces opportunites sont principalement destinees aux candidats deja en Roumanie, mais les candidatures sont ouvertes a tous.',
        'es': 'Estas oportunidades estan destinadas principalmente a candidatos ya ubicados en Rumania, pero las solicitudes estan abiertas a todos.',
    },
    'nationality_notice': {
        'ro': 'Acest formular este deschis tuturor nationalitatilor. Prioritate au candidatii aflati deja in Romania.',
        'en': 'This form is open to all nationalities. Priority is given to candidates already present in Romania.',
        'de': 'Dieses Formular steht allen Nationalitaeten offen. Vorrang haben Kandidaten die sich bereits in Rumaenien befinden.',
        'fr': 'Ce formulaire est ouvert a toutes les nationalites. La priorite est donnee aux candidats deja presents en Roumanie.',
        'es': 'Este formulario esta abierto a todas las nacionalidades. Se da prioridad a los candidatos ya presentes en Rumania.',
    },
    'contract_type': {
        'ro': 'Tip contract', 'en': 'Contract Type', 'de': 'Vertragsart', 'fr': 'Type de contrat',
        'es': 'Tipo de contrato', 'it': 'Tipo di contratto', 'pt': 'Tipo de contrato',
        'pl': 'Typ umowy', 'nl': 'Contracttype', 'hu': 'Szerzodes tipusa', 'cs': 'Typ smlouvy',
        'bg': 'Vid na dogovora', 'ru': 'Tip kontrakta', 'uk': 'Typ kontraktu',
    },
    'not_specified': {
        'ro': 'Nespecificat in datele guvernamentale',
        'en': 'Not specified in government data',
        'de': 'In Regierungsdaten nicht angegeben',
        'fr': 'Non specifie dans les donnees gouvernementales',
        'es': 'No especificado en datos gubernamentales',
    },
    'description': {
        'ro': 'Descriere', 'en': 'Description', 'de': 'Beschreibung', 'fr': 'Description',
        'es': 'Descripcion', 'it': 'Descrizione', 'pt': 'Descricao', 'pl': 'Opis',
        'nl': 'Beschrijving', 'hu': 'Leiras', 'cs': 'Popis', 'bg': 'Opisanie',
        'ru': 'Opisanie', 'uk': 'Opys',
    },
    'available_jobs': {
        'ro': 'Locuri de Munca Disponibile',
        'en': 'Available Jobs',
        'de': 'Verfuegbare Stellen',
        'fr': 'Emplois Disponibles',
        'es': 'Empleos Disponibles',
        'it': 'Lavori Disponibili',
        'pt': 'Vagas Disponiveis',
        'pl': 'Dostepne Oferty Pracy',
        'nl': 'Beschikbare Vacatures',
        'hu': 'Elerheto Allasok',
        'cs': 'Dostupna Pracovni Mista',
        'bg': 'Nalichni Rabotni Mesta',
        'ru': 'Dostupnye Vakansii',
        'uk': 'Dostupni Vakansii',
    },
    'cta_note': {
        'ro': 'Apasa butonul de mai sus pentru a aplica.',
        'en': 'Click the button above to apply for these positions.',
        'de': 'Klicken Sie auf die Schaltflaeche oben um sich zu bewerben.',
        'fr': "Cliquez sur le bouton ci-dessus pour postuler.",
        'es': 'Haga clic en el boton de arriba para aplicar.',
    },
}


# ── Helper functions ────────────────────────────────────────────────────

def safe_text(text):
    if not text:
        return ''
    return text.replace('\t', '  ').replace('\r', '').replace('\n', ' ')


def get_label(key, lang_code, eures_key=None):
    if eures_key and eures_key in EURES_T:
        t = EURES_T[eures_key]
        if lang_code in t:
            return t[lang_code]
    if key in SHARED_STRINGS:
        t = SHARED_STRINGS[key]
        if lang_code in t:
            return t[lang_code]
        if 'en' in t:
            return t['en']
        if 'ro' in t:
            return t['ro']
    return key


def format_salary(sal_min, sal_max):
    try:
        lo = float(sal_min) if sal_min else 0
        hi = float(sal_max) if sal_max else 0
    except (ValueError, TypeError):
        lo, hi = 0, 0
    if lo > 0 and hi > 0:
        return f"{int(lo)} - {int(hi)} RON"
    if lo > 0:
        return f"{int(lo)} RON"
    if hi > 0:
        return f"{int(hi)} RON"
    return ''


def parse_location(loc_str):
    if not loc_str:
        return '', ''
    parts = [p.strip() for p in loc_str.split('>')]
    county = parts[0].title() if parts else ''
    city = parts[-1].title() if len(parts) > 1 else ''
    return city, county


def find_latest_anofm_csv():
    """Find or fetch the latest full ANOFM CSV.
    On Linux (raspibig): read from local /mnt/usb disk.
    On Windows: download from raspibig via pscp.
    """
    if IS_LINUX:
        csvs = sorted(ANOFM_CSV_DIR.glob('anofm_*.csv'), key=lambda p: p.stat().st_mtime, reverse=True)
        for c in csvs:
            if c.stat().st_size > 1_000_000:
                return str(c)
        return str(csvs[0]) if csvs else None

    # Windows: fetch from raspibig
    print("Fetching latest ANOFM CSV from raspibig...")
    cmd = 'plink -ssh tudor@192.168.100.21 -pw bucare "ls -tS /mnt/hdd/SCRAPER_DATA/csv/ANOFM/anofm_*.csv 2>/dev/null | head -5"'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=30)
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    if not files:
        print("ERROR: No ANOFM CSV found on raspibig")
        return None

    remote_file = files[0]
    local_file = str(SCRIPT_DIR / 'anofm_latest.csv')
    print(f"  Downloading: {os.path.basename(remote_file)}")
    cmd = f'pscp -pw bucare tudor@192.168.100.21:"{remote_file}" "{local_file}"'
    subprocess.run(cmd, shell=True, timeout=120)

    if os.path.exists(local_file) and os.path.getsize(local_file) > 1000:
        print(f"  OK ({os.path.getsize(local_file) / 1024:.0f} KB)")
        return local_file
    print("  ERROR: Download failed")
    return None


def load_and_filter_jobs(csv_path, campaign_name, config):
    """Load ANOFM CSV and filter by COR codes + keyword fallback."""
    jobs = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            occupation = row.get('occupation', '')
            cor_code = parse_cor_code(occupation)

            matched = False
            if cor_code:
                campaigns = get_campaigns_for_cor(cor_code)
                if campaign_name in campaigns:
                    matched = True

            if not matched:
                title = row.get('job_title', '')
                desc = row.get('job_description', '')
                text = f"{title} {desc} {occupation}"
                pattern = FALLBACK_KEYWORDS.get(campaign_name)
                if pattern and pattern.search(text):
                    matched = True

            if matched:
                city, county = parse_location(row.get('location', ''))
                salary = format_salary(row.get('salary_min', ''), row.get('salary_max', ''))
                jobs.append({
                    'title': row.get('job_title', '').title(),
                    'employer': config['employer_labels'][i % len(config['employer_labels'])],
                    'city': city,
                    'county': county,
                    'salary': salary,
                    'contract_type': row.get('contract_type', ''),
                    'positions': row.get('positions_available', ''),
                    'description': row.get('job_description', ''),
                })

    return jobs[:MAX_JOBS_PER_PDF]


def build_content(lang_code, campaign_name):
    """Build translated text content for a specific campaign + language."""
    titles = CAMPAIGN_TITLES.get(campaign_name, {})
    pdf_title = titles.get(lang_code, titles.get('en', campaign_name))

    return {
        'pdf_title': pdf_title,
        'subtitle': get_label('subtitle', lang_code),
        'intro_line1': get_label('intro_line1', lang_code),
        'intro_line2': get_label('intro_line2', lang_code),
        'nationality_notice': get_label('nationality_notice', lang_code),
        'section_jobs': get_label('available_jobs', lang_code),
        'label_employer': get_label('company', lang_code, 'company'),
        'label_location': get_label('location', lang_code, 'location'),
        'label_salary': get_label('salary', lang_code, 'salary'),
        'label_contract': get_label('contract_type', lang_code),
        'label_positions': get_label('positions', lang_code, 'positions'),
        'label_description': get_label('description', lang_code),
        'label_not_specified': get_label('not_specified', lang_code),
        'cta_text': get_label('apply_now', lang_code, 'apply_now'),
        'cta_note': get_label('cta_note', lang_code),
        'footer_source': 'Data source: ANOFM (National Employment Agency of Romania)',
        'footer_date': f'Dataset date: {datetime.now().strftime("%B %Y")}',
    }


def setup_font(pdf):
    dejavu_path = FONT_DIR / 'DejaVuSans.ttf'
    dejavu_bold = FONT_DIR / 'DejaVuSans-Bold.ttf'
    if dejavu_path.exists():
        pdf.add_font('DejaVu', '', str(dejavu_path), uni=True)
        pdf.add_font('DejaVu', 'B', str(dejavu_bold), uni=True)
        return 'DejaVu'
    return 'Helvetica'


def add_apply_button(pdf, font_name, content, apply_url):
    btn_w, btn_h = 80, 14
    btn_x = (210 - btn_w) / 2
    btn_y = pdf.get_y()
    pdf.set_fill_color(0, 153, 51)
    pdf.rect(btn_x, btn_y, btn_w, btn_h, 'F')
    pdf.set_font(font_name, 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(btn_x, btn_y + 2)
    pdf.cell(btn_w, btn_h - 2, safe_text(content['cta_text']), ln=False, align='C', link=apply_url)
    pdf.link(btn_x, btn_y, btn_w, btn_h, apply_url)
    pdf.set_y(btn_y + btn_h + 3)
    pdf.set_font(font_name, '', 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, safe_text(content['cta_note']), ln=True, align='C')


def generate_pdf(lang_code, content, jobs, output_dir, config):
    """Generate a single PDF for one campaign in one language."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    font_name = setup_font(pdf)
    apply_url = config['apply_url']

    # Page 1: Introduction
    pdf.add_page()
    pdf.set_font(font_name, 'B', 18)
    pdf.set_text_color(0, 51, 102)
    pdf.multi_cell(0, 10, safe_text(content['pdf_title']), align='C')

    pdf.set_font(font_name, '', 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7, safe_text(content['subtitle']), ln=True, align='C')
    pdf.ln(3)

    pdf.set_draw_color(0, 102, 204)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    pdf.set_font(font_name, '', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, safe_text(content['intro_line1']))
    pdf.ln(2)
    pdf.multi_cell(0, 5, safe_text(content['intro_line2']))
    pdf.ln(4)

    # Nationality notice
    pdf.set_fill_color(230, 245, 255)
    pdf.set_draw_color(0, 102, 204)
    y_before = pdf.get_y()
    pdf.rect(15, y_before, 180, 12, 'DF')
    pdf.set_xy(20, y_before + 2)
    pdf.set_font(font_name, 'B', 9)
    pdf.set_text_color(0, 51, 102)
    pdf.multi_cell(170, 4, safe_text(content['nationality_notice']))
    pdf.set_y(y_before + 14)

    # APPLY NOW (top)
    pdf.ln(4)
    add_apply_button(pdf, font_name, content, apply_url)
    pdf.ln(4)

    # Section header
    pdf.set_font(font_name, 'B', 14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, safe_text(content['section_jobs']), ln=True)
    pdf.ln(2)

    # Job listings
    for i, job in enumerate(jobs):
        if pdf.get_y() > 250:
            pdf.add_page()

        pdf.set_font(font_name, 'B', 10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 6, f"{i+1}. {safe_text(job.get('title', ''))}", ln=True)

        pdf.set_font(font_name, '', 8)
        pdf.set_text_color(60, 60, 60)

        employer = job.get('employer', '')
        if employer:
            pdf.cell(0, 4, f"  {safe_text(content['label_employer'])}: {employer}", ln=True)

        city = job.get('city', '')
        county = job.get('county', '')
        location = f"{city}, {county}" if city and county else city or county
        if location:
            pdf.cell(0, 4, f"  {safe_text(content['label_location'])}: {safe_text(location)}", ln=True)

        salary = job.get('salary', '')
        if salary:
            pdf.cell(0, 4, f"  {safe_text(content['label_salary'])}: {safe_text(salary)}", ln=True)

        contract = job.get('contract_type', '')
        if contract:
            pdf.cell(0, 4, f"  {safe_text(content['label_contract'])}: {safe_text(contract)}", ln=True)

        positions = job.get('positions', '')
        if positions and str(positions) not in ('', '0'):
            pdf.cell(0, 4, f"  {safe_text(content['label_positions'])}: {positions}", ln=True)

        desc = job.get('description', '')
        if desc and len(desc) > 5:
            pdf.set_font(font_name, '', 7)
            pdf.multi_cell(0, 3.5, f"  {safe_text(content['label_description'])}: {safe_text(desc[:200])}")

        pdf.ln(2)
        pdf.set_draw_color(220, 220, 220)
        pdf.set_line_width(0.1)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(1)

    # APPLY NOW (bottom)
    pdf.ln(4)
    add_apply_button(pdf, font_name, content, apply_url)

    # Footer
    pdf.ln(6)
    pdf.set_font(font_name, '', 7)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 4, safe_text(content['footer_source']), ln=True, align='C')
    pdf.cell(0, 4, safe_text(content['footer_date']), ln=True, align='C')

    # Save
    prefix = config['pdf_prefix']
    output_path = os.path.join(output_dir, f'{prefix}_{lang_code.upper()}.pdf')
    pdf.output(output_path)
    return output_path


def deploy_pdfs(campaign_name, output_dir, config):
    """Deploy generated PDFs to website directories.
    On Linux (raspibig): copy locally.
    On Windows: upload via pscp.
    """
    remote_dir = config['remote_dir']
    if not remote_dir:
        return

    if IS_LINUX:
        # Local copy on raspibig
        dst = Path(remote_dir)
        dst.mkdir(parents=True, exist_ok=True)
        import shutil
        for f in Path(output_dir).glob('*.pdf'):
            shutil.copy2(f, dst / f.name)
    else:
        # Upload from Windows
        cmd = f'plink -ssh tudor@192.168.100.21 -pw bucare "mkdir -p {remote_dir}"'
        subprocess.run(cmd, shell=True, timeout=15, capture_output=True)
        for f in os.listdir(output_dir):
            if f.endswith('.pdf'):
                local = os.path.join(output_dir, f)
                cmd = f'pscp -pw bucare "{local}" tudor@192.168.100.21:"{remote_dir}{f}"'
                subprocess.run(cmd, shell=True, timeout=30, capture_output=True)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate campaign PDFs for all websites')
    parser.add_argument('--all', action='store_true', help='Generate for all 6 campaigns')
    parser.add_argument('--campaign', help='Specific campaign (e.g., FACTORYJOBS_RO)')
    parser.add_argument('--lang', help='Comma-separated language codes (default: all 38)')
    parser.add_argument('--fetch', action='store_true', help='Fetch latest ANOFM CSV from raspibig first')
    parser.add_argument('--upload', action='store_true', help='Upload PDFs to raspibig after generation')
    parser.add_argument('--csv', help='Path to ANOFM CSV (default: anofm_latest.csv)')
    args = parser.parse_args()

    # Determine CSV path
    csv_path = args.csv
    if not csv_path:
        if IS_LINUX:
            csv_path = find_latest_anofm_csv()
        else:
            csv_path = str(SCRIPT_DIR / 'anofm_latest.csv')
    if args.fetch or not os.path.exists(csv_path):
        csv_path = find_latest_anofm_csv()
        if not csv_path:
            sys.exit(1)

    # Determine campaigns
    if args.campaign:
        if args.campaign not in CAMPAIGN_CONFIG:
            print(f"ERROR: Unknown campaign '{args.campaign}'")
            print(f"Available: {', '.join(CAMPAIGN_CONFIG.keys())}")
            sys.exit(1)
        campaigns = [args.campaign]
    elif args.all:
        campaigns = list(CAMPAIGN_CONFIG.keys())
    else:
        print("Specify --all or --campaign NAME")
        parser.print_help()
        sys.exit(1)

    # Determine languages
    lang_codes = args.lang.split(',') if args.lang else ALL_LANG_CODES

    print(f"=== Campaign PDF Generator ===")
    print(f"CSV: {os.path.basename(csv_path)}")
    print(f"Campaigns: {len(campaigns)} | Languages: {len(lang_codes)}")
    print(f"Total PDFs to generate: {len(campaigns) * len(lang_codes)}")
    print()

    total_generated = 0
    for campaign_name in campaigns:
        config = CAMPAIGN_CONFIG[campaign_name]
        website = config['website'] or '(no website)'
        print(f"--- {campaign_name} -> {website} ---")

        # Filter jobs
        jobs = load_and_filter_jobs(csv_path, campaign_name, config)
        print(f"  Matched {len(jobs)} jobs (showing max {MAX_JOBS_PER_PDF})")

        if not jobs:
            print(f"  SKIPPED: No matching jobs found")
            continue

        # Output dir
        if IS_LINUX:
            output_dir = str(DATA_DIR / campaign_name)
        else:
            output_dir = str(SCRIPT_DIR / 'output' / campaign_name)
        os.makedirs(output_dir, exist_ok=True)

        # Generate PDFs
        generated = 0
        for lang_code in lang_codes:
            lang_name = EURES_LANGS.get(lang_code, lang_code)
            try:
                label = f"  [{lang_code}] {lang_name}"
                print(label.encode('ascii', 'replace').decode('ascii'), end='...', flush=True)
            except Exception:
                print(f"  [{lang_code}]", end='...', flush=True)

            try:
                content = build_content(lang_code, campaign_name)
                path = generate_pdf(lang_code, content, jobs, output_dir, config)
                size_kb = os.path.getsize(path) / 1024
                print(f" OK ({size_kb:.0f} KB)")
                generated += 1
            except Exception as e:
                print(f" ERROR: {e}")

        print(f"  Generated: {generated}/{len(lang_codes)} PDFs")
        total_generated += generated

        # Deploy if requested
        if args.upload:
            print(f"  Deploying PDFs...", end='', flush=True)
            try:
                deploy_pdfs(campaign_name, output_dir, config)
                print(" OK")
            except Exception as e:
                print(f" ERROR: {e}")

        print()

    print(f"=== DONE ===")
    print(f"Total PDFs generated: {total_generated}")
    out_base = str(DATA_DIR) if IS_LINUX else str(SCRIPT_DIR / 'output')
    print(f"Output: {out_base}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Ministry Open Data Scraper - Search every ministry in every country for open data.
Downloads only datasets with email or phone fields.

Usage:
    python3 ministry_opendata_scraper.py --country NO           # Single country
    python3 ministry_opendata_scraper.py --all                  # All countries
    python3 ministry_opendata_scraper.py --scan                 # Scan for APIs
    python3 ministry_opendata_scraper.py --download NO          # Download with email/phone
"""

import argparse
import json
import os
import subprocess
import psycopg2
import re
from datetime import datetime

DB_CONFIG = {'dbname': 'interjob_master', 'user': 'tudor'}
OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/MINISTRIES'

# Countries with ministry search terms in English + local language
COUNTRIES = {
    'NO': {
        'name': 'Norway',
        'lang': 'Norwegian',
        'ministries': [
            ('Ministry of Trade', 'Naringsdepartementet'),
            ('Ministry of Labour', 'Arbeids- og inkluderingsdepartementet'),
            ('Brreg', 'Bronnoysundregistrene'),
        ],
        'portals': ['data.norge.no', 'brreg.no/api'],
        'search_en': 'Norway ministry open data companies API',
        'search_local': 'norsk offentlig data bedrifter API'
    },
    'SE': {
        'name': 'Sweden',
        'lang': 'Swedish',
        'ministries': [
            ('Ministry of Enterprise', 'Naringsdepartementet'),
            ('Bolagsverket', 'Bolagsverket'),
            ('SCB', 'Statistiska centralbyran'),
        ],
        'portals': ['oppnadata.se', 'bolagsverket.se'],
        'search_en': 'Sweden ministry open data companies API',
        'search_local': 'svensk oppen data foretag API'
    },
    'DK': {
        'name': 'Denmark',
        'lang': 'Danish',
        'ministries': [
            ('Ministry of Industry', 'Erhvervsministeriet'),
            ('CVR', 'Det Centrale Virksomhedsregister'),
            ('Virk.dk', 'Virk.dk'),
        ],
        'portals': ['opendata.dk', 'cvr.dk', 'datacvr.virk.dk'],
        'search_en': 'Denmark ministry open data companies CVR API',
        'search_local': 'dansk offentlige data virksomheder API'
    },
    'FI': {
        'name': 'Finland',
        'lang': 'Finnish',
        'ministries': [
            ('Ministry of Economic Affairs', 'Tyo- ja elinkeinoministeri'),
            ('PRH', 'Patentti- ja rekisterihallitus'),
            ('YTJ', 'Yritys- ja yhteisotietojarjestelma'),
        ],
        'portals': ['avoindata.fi', 'ytj.fi', 'prh.fi'],
        'search_en': 'Finland ministry open data companies API',
        'search_local': 'suomi avoin data yritykset API'
    },
    'DE': {
        'name': 'Germany',
        'lang': 'German',
        'ministries': [
            ('Ministry of Economy', 'Bundesministerium fur Wirtschaft'),
            ('Handelsregister', 'Handelsregister'),
            ('Unternehmensregister', 'Unternehmensregister'),
        ],
        'portals': ['govdata.de', 'handelsregister.de', 'unternehmensregister.de'],
        'search_en': 'Germany ministry open data companies Handelsregister API',
        'search_local': 'deutschland offene daten unternehmen API'
    },
    'PL': {
        'name': 'Poland',
        'lang': 'Polish',
        'ministries': [
            ('Ministry of Development', 'Ministerstwo Rozwoju'),
            ('KRS', 'Krajowy Rejestr Sadowy'),
            ('CEIDG', 'Centralna Ewidencja'),
        ],
        'portals': ['dane.gov.pl', 'krs.ms.gov.pl', 'ceidg.gov.pl'],
        'search_en': 'Poland ministry open data companies KRS API',
        'search_local': 'polska otwarte dane firmy API'
    },
    'FR': {
        'name': 'France',
        'lang': 'French',
        'ministries': [
            ('Ministry of Economy', 'Ministere de lEconomie'),
            ('INSEE', 'Institut national de la statistique'),
            ('Infogreffe', 'Infogreffe'),
        ],
        'portals': ['data.gouv.fr', 'sirene.fr', 'api.insee.fr'],
        'search_en': 'France ministry open data companies SIRENE API',
        'search_local': 'france donnees ouvertes entreprises API'
    },
    'NL': {
        'name': 'Netherlands',
        'lang': 'Dutch',
        'ministries': [
            ('Ministry of Economic Affairs', 'Ministerie van Economische Zaken'),
            ('KVK', 'Kamer van Koophandel'),
        ],
        'portals': ['data.overheid.nl', 'kvk.nl'],
        'search_en': 'Netherlands ministry open data companies KVK API',
        'search_local': 'nederland open data bedrijven API'
    },
    'BE': {
        'name': 'Belgium',
        'lang': 'Dutch/French',
        'ministries': [
            ('FPS Economy', 'SPF Economie'),
            ('KBO/BCE', 'Kruispuntbank van Ondernemingen'),
        ],
        'portals': ['data.gov.be', 'kbopub.economie.fgov.be'],
        'search_en': 'Belgium ministry open data companies BCE API',
        'search_local': 'belgie open data ondernemingen API'
    },
    'ES': {
        'name': 'Spain',
        'lang': 'Spanish',
        'ministries': [
            ('Ministry of Economy', 'Ministerio de Economia'),
            ('Registro Mercantil', 'Registro Mercantil Central'),
        ],
        'portals': ['datos.gob.es', 'rmc.es'],
        'search_en': 'Spain ministry open data companies Registro Mercantil API',
        'search_local': 'espana datos abiertos empresas API'
    },
    'IT': {
        'name': 'Italy',
        'lang': 'Italian',
        'ministries': [
            ('Ministry of Economic Development', 'Ministero dello Sviluppo Economico'),
            ('Registro Imprese', 'Registro delle Imprese'),
            ('InfoCamere', 'InfoCamere'),
        ],
        'portals': ['dati.gov.it', 'registroimprese.it'],
        'search_en': 'Italy ministry open data companies Registro Imprese API',
        'search_local': 'italia dati aperti imprese API'
    },
    'AT': {
        'name': 'Austria',
        'lang': 'German',
        'ministries': [
            ('Ministry of Economy', 'Bundesministerium fur Wirtschaft'),
            ('Firmenbuch', 'Firmenbuch'),
        ],
        'portals': ['data.gv.at', 'firmenbuch.at'],
        'search_en': 'Austria ministry open data companies Firmenbuch API',
        'search_local': 'osterreich offene daten unternehmen API'
    },
    'CH': {
        'name': 'Switzerland',
        'lang': 'German/French/Italian',
        'ministries': [
            ('SECO', 'Staatssekretariat fur Wirtschaft'),
            ('Zefix', 'Zentraler Firmenindex'),
        ],
        'portals': ['opendata.swiss', 'zefix.ch'],
        'search_en': 'Switzerland ministry open data companies Zefix API',
        'search_local': 'schweiz offene daten unternehmen API'
    },
    'CZ': {
        'name': 'Czech Republic',
        'lang': 'Czech',
        'ministries': [
            ('Ministry of Industry', 'Ministerstvo prumyslu'),
            ('ARES', 'Administrativni registr ekonomickych subjektu'),
        ],
        'portals': ['data.gov.cz', 'ares.gov.cz'],
        'search_en': 'Czech ministry open data companies ARES API',
        'search_local': 'cesko otevrena data firmy API'
    },
    'RO': {
        'name': 'Romania',
        'lang': 'Romanian',
        'ministries': [
            ('Ministry of Economy', 'Ministerul Economiei'),
            ('ONRC', 'Oficiul National al Registrului Comertului'),
            ('ANAF', 'Agentia Nationala de Administrare Fiscala'),
        ],
        'portals': ['data.gov.ro', 'onrc.ro', 'anaf.ro'],
        'search_en': 'Romania ministry open data companies ONRC API',
        'search_local': 'romania date deschise firme API'
    },
    'BG': {
        'name': 'Bulgaria',
        'lang': 'Bulgarian',
        'ministries': [
            ('Ministry of Economy', 'Ministerstvo na ikonomikata'),
            ('Commercial Register', 'Targovski registar'),
        ],
        'portals': ['opendata.government.bg', 'brra.bg'],
        'search_en': 'Bulgaria ministry open data companies API',
        'search_local': 'bulgaria otvoreni danni firmi API'
    },
    'HU': {
        'name': 'Hungary',
        'lang': 'Hungarian',
        'ministries': [
            ('Ministry of Economy', 'Gazdasagi Miniszterium'),
            ('Company Registry', 'Cegjegyzek'),
        ],
        'portals': ['data.gov.hu', 'e-cegjegyzek.hu'],
        'search_en': 'Hungary ministry open data companies API',
        'search_local': 'magyarorszag nyilt adatok cegek API'
    },
    'PT': {
        'name': 'Portugal',
        'lang': 'Portuguese',
        'ministries': [
            ('Ministry of Economy', 'Ministerio da Economia'),
            ('Registo Comercial', 'Registo Comercial'),
        ],
        'portals': ['dados.gov.pt', 'publicidade.mj.pt'],
        'search_en': 'Portugal ministry open data companies API',
        'search_local': 'portugal dados abertos empresas API'
    },
    'GR': {
        'name': 'Greece',
        'lang': 'Greek',
        'ministries': [
            ('Ministry of Development', 'Ypourgeio Anaptixis'),
            ('GEMI', 'Geniko Emporiko Mitroo'),
        ],
        'portals': ['data.gov.gr', 'businessregistry.gr'],
        'search_en': 'Greece ministry open data companies GEMI API',
        'search_local': 'ellada anoichta dedomena etaireies API'
    },
    'IE': {
        'name': 'Ireland',
        'lang': 'English',
        'ministries': [
            ('Dept of Enterprise', 'Department of Enterprise'),
            ('CRO', 'Companies Registration Office'),
        ],
        'portals': ['data.gov.ie', 'cro.ie'],
        'search_en': 'Ireland ministry open data companies CRO API',
        'search_local': 'Ireland open data companies API'
    },
    'GB': {
        'name': 'United Kingdom',
        'lang': 'English',
        'ministries': [
            ('Companies House', 'Companies House'),
            ('HMRC', 'HM Revenue and Customs'),
        ],
        'portals': ['data.gov.uk', 'companieshouse.gov.uk'],
        'search_en': 'UK Companies House open data API bulk download',
        'search_local': 'UK Companies House open data API'
    },
    'EE': {
        'name': 'Estonia',
        'lang': 'Estonian',
        'ministries': [
            ('Ministry of Economic Affairs', 'Majandus- ja Kommunikatsiooniministeerium'),
            ('e-Business Register', 'Ariregister'),
        ],
        'portals': ['opendata.riik.ee', 'ariregister.rik.ee'],
        'search_en': 'Estonia ministry open data companies API',
        'search_local': 'eesti avatud andmed ettevotted API'
    },
    'LV': {
        'name': 'Latvia',
        'lang': 'Latvian',
        'ministries': [
            ('Ministry of Economics', 'Ekonomikas ministrija'),
            ('UR', 'Uznemumu registrs'),
        ],
        'portals': ['data.gov.lv', 'ur.gov.lv'],
        'search_en': 'Latvia ministry open data companies API',
        'search_local': 'latvija atverto datu uznemumi API'
    },
    'LT': {
        'name': 'Lithuania',
        'lang': 'Lithuanian',
        'ministries': [
            ('Ministry of Economy', 'Ukio ministerija'),
            ('RC', 'Registru centras'),
        ],
        'portals': ['data.gov.lt', 'registrucentras.lt'],
        'search_en': 'Lithuania ministry open data companies API',
        'search_local': 'lietuva atviri duomenys imones API'
    },
    'SI': {
        'name': 'Slovenia',
        'lang': 'Slovenian',
        'ministries': [
            ('Ministry of Economy', 'Ministrstvo za gospodarstvo'),
            ('AJPES', 'Agencija za javnopravne evidence'),
        ],
        'portals': ['podatki.gov.si', 'ajpes.si'],
        'search_en': 'Slovenia ministry open data companies AJPES API',
        'search_local': 'slovenija odprta podatke podjetja API'
    },
    'SK': {
        'name': 'Slovakia',
        'lang': 'Slovak',
        'ministries': [
            ('Ministry of Economy', 'Ministerstvo hospodarstva'),
            ('ORSR', 'Obchodny register'),
        ],
        'portals': ['data.gov.sk', 'orsr.sk'],
        'search_en': 'Slovakia ministry open data companies API',
        'search_local': 'slovensko otvorene data firmy API'
    },
    'HR': {
        'name': 'Croatia',
        'lang': 'Croatian',
        'ministries': [
            ('Ministry of Economy', 'Ministarstvo gospodarstva'),
            ('Sudski registar', 'Sudski registar'),
        ],
        'portals': ['data.gov.hr', 'sudreg.pravosudje.hr'],
        'search_en': 'Croatia ministry open data companies API',
        'search_local': 'hrvatska otvoreni podaci tvrtke API'
    },
    'LU': {
        'name': 'Luxembourg',
        'lang': 'French/German',
        'ministries': [
            ('Ministry of Economy', 'Ministere de lEconomie'),
            ('RCS', 'Registre de Commerce et des Societes'),
        ],
        'portals': ['data.public.lu', 'lbr.lu'],
        'search_en': 'Luxembourg ministry open data companies RCS API',
        'search_local': 'luxembourg donnees ouvertes entreprises API'
    },
}

# Known OpenAPI/CKAN endpoints to try with mcp2cli
KNOWN_APIS = {
    'NO': 'https://data.brreg.no/enhetsregisteret/api/docs/index.html',
    'DK': 'https://datacvr.virk.dk/api',
    'SE': 'https://www.bolagsverket.se/apier',
    'FI': 'https://avoindata.prh.fi/ytj.html',
    'GB': 'https://developer.company-information.service.gov.uk/',
    'FR': 'https://api.insee.fr/catalogue/',
    'NL': 'https://developers.kvk.nl/',
    'BE': 'https://kbopub.economie.fgov.be/kbopub-api/',
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def run_mcp2cli(spec_url, list_only=False):
    """Run mcp2cli to discover or fetch API data."""
    try:
        if list_only:
            cmd = ['mcp2cli', '--spec', spec_url, '--list']
        else:
            cmd = ['mcp2cli', '--spec', spec_url, '--list']

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        return None


def check_has_contact_fields(api_response):
    """Check if API response mentions email or phone fields."""
    if not api_response:
        return False, False

    response_lower = api_response.lower()
    has_email = any(term in response_lower for term in ['email', 'e-mail', 'mail', 'epost'])
    has_phone = any(term in response_lower for term in ['phone', 'telefon', 'tel', 'mobile', 'fax'])

    return has_email, has_phone


def scan_country_apis(country_code):
    """Scan a country's known APIs for available data."""
    if country_code not in COUNTRIES:
        print(f"Unknown country: {country_code}")
        return []

    country = COUNTRIES[country_code]
    results = []

    print(f"\n=== Scanning {country['name']} ({country_code}) ===")
    print(f"Language: {country['lang']}")
    print(f"Search EN: {country['search_en']}")
    print(f"Search Local: {country['search_local']}")

    # Check known APIs
    if country_code in KNOWN_APIS:
        api_url = KNOWN_APIS[country_code]
        print(f"\nChecking API: {api_url}")
        api_response = run_mcp2cli(api_url, list_only=True)
        if api_response:
            has_email, has_phone = check_has_contact_fields(api_response)
            results.append({
                'country_code': country_code,
                'source_name': f"{country['name']} Official API",
                'source_url': api_url,
                'has_email': has_email,
                'has_phone': has_phone,
                'api_available': True
            })
            print(f"  Email: {has_email}, Phone: {has_phone}")

    # Check portals
    for portal in country['portals']:
        print(f"Portal: {portal}")
        results.append({
            'country_code': country_code,
            'source_name': portal,
            'source_url': f"https://{portal}",
            'has_email': None,  # Unknown until checked
            'has_phone': None,
            'api_available': False
        })

    return results


def save_to_db(results):
    """Save scan results to database."""
    conn = get_conn()
    cur = conn.cursor()

    for r in results:
        cur.execute("""
            INSERT INTO opendata_sources
            (country_code, country_name, source_name, source_url, has_email, has_phone, api_available, last_checked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (
            r['country_code'],
            COUNTRIES.get(r['country_code'], {}).get('name', ''),
            r['source_name'],
            r['source_url'],
            r.get('has_email'),
            r.get('has_phone'),
            r.get('api_available', False)
        ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"Saved {len(results)} results to database")


def scan_all():
    """Scan all countries."""
    all_results = []
    for code in COUNTRIES.keys():
        results = scan_country_apis(code)
        all_results.extend(results)

    save_to_db(all_results)

    print(f"\n=== SUMMARY ===")
    print(f"Countries scanned: {len(COUNTRIES)}")
    print(f"Sources found: {len(all_results)}")


def download_with_contacts(country_code):
    """Download data that has email or phone using mcp2cli."""
    if country_code not in KNOWN_APIS:
        print(f"No known API for {country_code}")
        return

    api_url = KNOWN_APIS[country_code]
    country = COUNTRIES[country_code]

    print(f"\n=== Downloading from {country['name']} ===")
    print(f"API: {api_url}")

    # Create output directory
    output_dir = os.path.join(OUTPUT_DIR, country_code)
    os.makedirs(output_dir, exist_ok=True)

    # Try to discover and download
    # This would need to be customized per API
    print(f"Output dir: {output_dir}")
    print("Note: Actual download requires API-specific implementation")


def list_countries():
    """List all configured countries."""
    print("=" * 80)
    print("CONFIGURED COUNTRIES FOR OPEN DATA SEARCH")
    print("=" * 80)
    print(f"{'Code':<5} {'Country':<20} {'Language':<15} {'Portals':<40}")
    print("-" * 80)

    for code, info in sorted(COUNTRIES.items()):
        portals = ', '.join(info['portals'][:2])
        print(f"{code:<5} {info['name']:<20} {info['lang']:<15} {portals:<40}")

    print("-" * 80)
    print(f"Total: {len(COUNTRIES)} countries")


def main():
    parser = argparse.ArgumentParser(description='Ministry Open Data Scraper')
    parser.add_argument('--country', '-c', help='Single country code (e.g., NO, SE)')
    parser.add_argument('--all', action='store_true', help='Scan all countries')
    parser.add_argument('--scan', action='store_true', help='Scan for APIs')
    parser.add_argument('--download', help='Download data for country')
    parser.add_argument('--list', action='store_true', help='List all countries')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.list:
        list_countries()
    elif args.all or args.scan:
        scan_all()
    elif args.country:
        results = scan_country_apis(args.country.upper())
        save_to_db(results)
    elif args.download:
        download_with_contacts(args.download.upper())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

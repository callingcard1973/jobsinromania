#!/usr/bin/env python3
"""Configuration for MERCOSUR parallel scraping system"""

from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
OUTPUT_BASE = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_parallel")
EXISTING_DATA = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_final")

# Thread counts per worker
THREAD_COUNTS = {
    "websites": 10,
    "govapis": 5,
    "associations": 5,
    "registries": 2,
    "tradeshows": 3,
    "enricher": 8,
}

# Timeouts (seconds)
TIMEOUTS = {
    "request": 30,
    "page_load": 60,
    "selenium_wait": 10,
    "worker_total": 3600,  # 1 hour per worker max
}

# Request settings
REQUEST_DELAY = (1, 3)  # Random delay between requests (min, max seconds)
MAX_RETRIES = 3
RETRY_DELAY = 5

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

# Government API targets
GOV_APIS = {
    "apex_brasil": {
        "name": "APEX Brasil",
        "base_url": "https://portal.apexbrasil.com.br",
        "endpoints": [
            "/api/exportadores",
            "/api/empresas",
            "/api/v1/companies",
            "/api/v2/exporters",
            "/exporters/search",
        ],
        "country": "Brazil",
    },
    "prochile": {
        "name": "ProChile",
        "base_url": "https://www.prochile.gob.cl",
        "endpoints": [
            "/api/exportadores",
            "/exportadores/api",
            "/directorio-exportadores/api",
        ],
        "country": "Chile",
    },
    "uruguay_xxi": {
        "name": "Uruguay XXI",
        "base_url": "https://www.uruguayxxi.gub.uy",
        "endpoints": [
            "/api/exporters",
            "/exportadores/data.json",
            "/empresas/exportadoras.json",
        ],
        "country": "Uruguay",
    },
    "argentina_exporta": {
        "name": "Argentina Exporta",
        "base_url": "https://www.argentina.gob.ar/produccion",
        "endpoints": [
            "/api/empresas-exportadoras",
            "/comercio-exterior/directorio",
        ],
        "country": "Argentina",
    },
    "rediex": {
        "name": "REDIEX Paraguay",
        "base_url": "https://www.rediex.gov.py",
        "endpoints": [
            "/api/exportadores",
            "/directorio/empresas.json",
        ],
        "country": "Paraguay",
    },
}

# Association targets with selectors
ASSOCIATIONS = {
    "abiec": {
        "name": "ABIEC (Brazilian Beef)",
        "url": "https://www.abiec.com.br/associados/",
        "country": "Brazil",
        "sector": "beef",
        "selectors": {
            "company_list": ".associado, .member-item, .company-card",
            "name": "h3, h4, .name, .company-name",
            "website": "a[href*='http']:not([href*='abiec'])",
            "email": "a[href^='mailto:']",
        },
    },
    "abiove": {
        "name": "ABIOVE (Brazilian Soy)",
        "url": "https://abiove.org.br/associadas/",
        "country": "Brazil",
        "sector": "soy",
        "selectors": {
            "company_list": ".associada, .member, .company",
            "name": "h3, h4, .title",
            "website": "a[href*='http']:not([href*='abiove'])",
        },
    },
    "abpa": {
        "name": "ABPA (Brazilian Poultry)",
        "url": "https://abpa-br.org/associadas/",
        "country": "Brazil",
        "sector": "poultry",
        "selectors": {
            "company_list": ".associada, .member-card",
            "name": ".name, h3, h4",
            "website": "a[href*='http']:not([href*='abpa'])",
        },
    },
    "ipcva": {
        "name": "IPCVA (Argentine Beef)",
        "url": "https://www.ipcva.com.ar/frigorificos/",
        "country": "Argentina",
        "sector": "beef",
        "selectors": {
            "company_list": ".frigorifico, .empresa, .member",
            "name": "h3, h4, .name",
            "website": "a[href*='http']:not([href*='ipcva'])",
        },
    },
    "wines_argentina": {
        "name": "Wines of Argentina",
        "url": "https://www.winesofargentina.org/en/wineries",
        "country": "Argentina",
        "sector": "wine",
        "selectors": {
            "company_list": ".winery, .bodega, .member-card",
            "name": "h3, h4, .title",
            "website": "a.website, a[href*='http']:not([href*='winesofargentina'])",
        },
    },
    "salmonchile": {
        "name": "SalmonChile",
        "url": "https://www.salmonchile.cl/socios/",
        "country": "Chile",
        "sector": "salmon",
        "selectors": {
            "company_list": ".socio, .member, .company-card",
            "name": "h3, h4, .company-name",
            "website": "a[href*='http']:not([href*='salmonchile'])",
        },
    },
    "asoex": {
        "name": "ASOEX (Chilean Fruit)",
        "url": "https://www.asoex.cl/socios/",
        "country": "Chile",
        "sector": "fruit",
        "selectors": {
            "company_list": ".socio, .member",
            "name": "h3, h4, .name",
            "website": "a[href*='http']:not([href*='asoex'])",
        },
    },
    "abemel": {
        "name": "ABEMEL (Brazilian Honey)",
        "url": "https://www.abemel.com.br/associados/",
        "country": "Brazil",
        "sector": "honey",
        "selectors": {
            "company_list": ".associado, .member",
            "name": "h3, h4, .name",
            "website": "a[href*='http']:not([href*='abemel'])",
        },
    },
}

# Trade show targets
TRADE_SHOWS = {
    "apas_show": {
        "name": "APAS Show 2026",
        "url": "https://apasshow.com.br/expositores",
        "country": "Brazil",
        "sector": "food/retail",
        "selectors": {
            "exhibitor_list": ".expositor, .exhibitor, .company-card",
            "name": "h3, h4, .company-name, .title",
            "stand": ".stand, .booth",
            "website": "a[href*='http']:not([href*='apas'])",
        },
    },
    "fispal": {
        "name": "Fispal Food Service 2026",
        "url": "https://fispalfoodservice.com.br/expositores",
        "country": "Brazil",
        "sector": "food service",
        "selectors": {
            "exhibitor_list": ".expositor, .exhibitor",
            "name": "h3, h4, .name",
            "website": "a[href*='http']:not([href*='fispal'])",
        },
    },
    "mercoagro": {
        "name": "Mercoagro 2026",
        "url": "https://www.mercoagro.com.br/expositores",
        "country": "Brazil",
        "sector": "agribusiness",
        "selectors": {
            "exhibitor_list": ".expositor, .exhibitor-item",
            "name": "h3, h4, .company",
            "website": "a[href*='http']:not([href*='mercoagro'])",
        },
    },
    "expoaladi": {
        "name": "Expoaladi 2026",
        "url": "https://www.expoaladi.org/expositores",
        "country": "Regional",
        "sector": "food",
        "selectors": {
            "exhibitor_list": ".expositor, .exhibitor",
            "name": "h3, h4, .name",
            "website": "a[href*='http']",
        },
    },
    "fenavinho": {
        "name": "Fenavinho 2026",
        "url": "https://www.fenavinho.com.br/expositores",
        "country": "Brazil",
        "sector": "wine",
        "selectors": {
            "exhibitor_list": ".expositor, .exhibitor",
            "name": "h3, h4, .name",
            "website": "a[href*='http']:not([href*='fenavinho'])",
        },
    },
}

# Registry bulk download targets
REGISTRIES = {
    "brazil_cnpj": {
        "name": "Brazil CNPJ",
        "url": "https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj",
        "method": "bulk_download",
        "filter_codes": [
            "0111-3",  # Rice
            "0115-6",  # Soy
            "0151-2",  # Cattle
            "0155-5",  # Poultry
            "1011-2",  # Beef processing
            "1012-1",  # Poultry processing
            "1061-9",  # Grain milling
            "1066-0",  # Vegetable oil
        ],
        "country": "Brazil",
    },
    "chile_sii": {
        "name": "Chile SII",
        "url": "https://www.sii.cl/estadisticas/empresas.htm",
        "method": "bulk_download",
        "country": "Chile",
    },
}

# Enrichment sources
ENRICHMENT_SOURCES = {
    "google_search": {
        "enabled": True,
        "template": '"{company}" email contact site:{domain}',
    },
    "whois": {
        "enabled": True,
    },
    "linkedin": {
        "enabled": False,  # Requires authentication
    },
    "hunter_io": {
        "enabled": False,  # Requires API key
        "api_key": None,
    },
}

# Contact page patterns
CONTACT_PAGE_PATTERNS = [
    "/contact",
    "/contacto",
    "/contato",
    "/contact-us",
    "/contactenos",
    "/fale-conosco",
    "/about/contact",
    "/empresa/contacto",
]

# Email patterns to extract
EMAIL_PATTERNS = [
    r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
]

# Phone patterns
PHONE_PATTERNS = [
    r"tel:([+\d\s()-]+)",
    r"\+55\s*\d{2}\s*\d{4,5}[-.\s]?\d{4}",  # Brazil
    r"\+54\s*\d{2,4}\s*\d{4}[-.\s]?\d{4}",  # Argentina
    r"\+598\s*\d{2}\s*\d{3}[-.\s]?\d{4}",   # Uruguay
    r"\+56\s*\d{1,2}\s*\d{4}[-.\s]?\d{4}",  # Chile
    r"\+595\s*\d{2,3}\s*\d{3}[-.\s]?\d{4}", # Paraguay
]

# Sectors for classification
SECTORS = [
    "beef", "poultry", "pork", "salmon", "seafood",
    "soy", "corn", "wheat", "sugar", "coffee",
    "wine", "fruit", "vegetables", "honey", "dairy",
    "lithium", "niobium", "copper", "iron", "minerals",
    "machinery", "automotive", "chemicals", "textiles",
]

# Output field schema
OUTPUT_SCHEMA = [
    "name",
    "country",
    "sector",
    "website",
    "email",
    "phone",
    "address",
    "capacity",
    "source",
    "scraped_at",
]

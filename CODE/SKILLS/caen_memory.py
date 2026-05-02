#!/usr/bin/env python3
"""
CAEN/NACE Code Memory Cache - In-memory lookup for business classification codes

CAEN (Romania) = NACE Rev.2 (EU) = ISIC Rev.4 (UN)
All three systems use the same 4-digit codes.

Usage:
    from caen_memory import CAEN, get_description, get_sector, search_caen

    # Lookup
    desc = get_description("5510")  # "Hotels and similar accommodation"
    sector = get_sector("5510")     # "HORECA"

    # Search
    codes = search_caen("hotel")    # All hotel-related codes
    codes = search_caen("construct")# All construction codes

    # Sector listing
    horeca_codes = SECTORS["HORECA"]

    # International
    from caen_memory import NACE, ISIC  # Same as CAEN
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load CAEN descriptions
CAEN_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/caen_descriptions.json")

# Master CAEN dictionary - loaded once into memory
CAEN: Dict[str, str] = {}
if CAEN_FILE.exists():
    CAEN = json.loads(CAEN_FILE.read_text())

# NACE and ISIC are identical to CAEN (same EU/UN classification)
NACE = CAEN
ISIC = CAEN

# ============================================================
# SECTOR GROUPINGS - Key business sectors with CAEN codes
# ============================================================

SECTORS = {
    # HORECA - Hotels, Restaurants, Catering
    "HORECA": {
        "name": "Hotels, Restaurants & Catering",
        "codes": ["5510", "5520", "5530", "5590", "5610", "5621", "5629", "5630"],
        "patterns": ["55*", "56*"],
        "keywords": ["hotel", "restaurant", "catering", "accommodation", "food service", "bar", "cafe"],
    },

    # CONSTRUCTION
    "CONSTRUCTION": {
        "name": "Construction & Building",
        "codes": ["4110", "4120", "4211", "4212", "4213", "4221", "4222", "4291", "4299",
                  "4311", "4312", "4313", "4321", "4322", "4329", "4331", "4332", "4333",
                  "4334", "4339", "4391", "4399"],
        "patterns": ["41*", "42*", "43*"],
        "keywords": ["construction", "building", "civil engineering", "demolition", "electrical", "plumbing"],
    },

    # MANUFACTURING
    "MANUFACTURING": {
        "name": "Manufacturing & Production",
        "codes": [],  # Too many - use patterns
        "patterns": ["10*", "11*", "12*", "13*", "14*", "15*", "16*", "17*", "18*",
                     "19*", "20*", "21*", "22*", "23*", "24*", "25*", "26*", "27*",
                     "28*", "29*", "30*", "31*", "32*", "33*"],
        "keywords": ["manufacturing", "production", "factory", "plant", "industrial"],
    },

    # AGRICULTURE
    "AGRICULTURE": {
        "name": "Agriculture, Forestry & Fishing",
        "codes": [],
        "patterns": ["01*", "02*", "03*"],
        "keywords": ["agriculture", "farming", "forestry", "fishing", "crop", "livestock"],
    },

    # TRANSPORT & LOGISTICS
    "TRANSPORT": {
        "name": "Transport & Logistics",
        "codes": ["4910", "4920", "4931", "4932", "4939", "4941", "4942", "4950",
                  "5010", "5020", "5030", "5040", "5110", "5121", "5122",
                  "5210", "5221", "5222", "5223", "5224", "5229"],
        "patterns": ["49*", "50*", "51*", "52*"],
        "keywords": ["transport", "logistics", "freight", "shipping", "warehouse", "storage"],
    },

    # IT & TECHNOLOGY
    "IT": {
        "name": "Information Technology",
        "codes": ["6201", "6202", "6203", "6209", "6311", "6312", "6391", "6399"],
        "patterns": ["62*", "63*"],
        "keywords": ["software", "programming", "IT", "computer", "data", "hosting"],
    },

    # RETAIL & WHOLESALE
    "TRADE": {
        "name": "Wholesale & Retail Trade",
        "codes": [],
        "patterns": ["45*", "46*", "47*"],
        "keywords": ["wholesale", "retail", "trade", "shop", "store", "sale"],
    },

    # EMPLOYMENT & HR
    "EMPLOYMENT": {
        "name": "Employment & Staffing Agencies",
        "codes": ["7810", "7820", "7830"],
        "patterns": ["78*"],
        "keywords": ["employment", "staffing", "recruitment", "agency", "temporary", "personnel"],
    },

    # CALL CENTERS & BPO
    "CALL_CENTER": {
        "name": "Call Centers & Business Process Outsourcing",
        "codes": ["8220"],
        "patterns": ["8220"],
        "keywords": ["call center", "call centre", "BPO", "customer service", "telemarketing"],
    },

    # HEALTHCARE
    "HEALTHCARE": {
        "name": "Healthcare & Social Services",
        "codes": ["8610", "8621", "8622", "8623", "8690", "8710", "8720", "8730", "8790",
                  "8810", "8891", "8899"],
        "patterns": ["86*", "87*", "88*"],
        "keywords": ["hospital", "medical", "healthcare", "nursing", "care", "elderly"],
    },

    # FOOD PROCESSING
    "FOOD_PROCESSING": {
        "name": "Food & Beverage Manufacturing",
        "codes": ["1011", "1012", "1013", "1020", "1031", "1032", "1039", "1041", "1042",
                  "1051", "1052", "1061", "1062", "1071", "1072", "1073", "1081", "1082",
                  "1083", "1084", "1085", "1086", "1089", "1091", "1092"],
        "patterns": ["10*", "11*"],
        "keywords": ["food", "meat", "bakery", "dairy", "beverage", "processing"],
    },

    # CLEANING & FACILITY SERVICES
    "CLEANING": {
        "name": "Cleaning & Facility Services",
        "codes": ["8121", "8122", "8129", "8110"],
        "patterns": ["81*"],
        "keywords": ["cleaning", "janitorial", "facility", "maintenance", "sanitation"],
    },

    # SECURITY
    "SECURITY": {
        "name": "Security & Investigation",
        "codes": ["8010", "8020", "8030"],
        "patterns": ["80*"],
        "keywords": ["security", "guard", "surveillance", "investigation", "protection"],
    },
}

# ============================================================
# INTERNATIONAL EQUIVALENTS
# ============================================================

INTERNATIONAL = {
    # Country-specific naming (all use same codes)
    "RO": "CAEN",      # Romania - Clasificarea Activitatilor din Economia Nationala
    "EU": "NACE",      # Europe - Nomenclature of Economic Activities
    "UN": "ISIC",      # UN - International Standard Industrial Classification
    "UK": "SIC",       # UK - Standard Industrial Classification (similar but 5 digits)
    "US": "NAICS",     # US - North American Industry Classification System (different)
    "DE": "WZ",        # Germany - Wirtschaftszweige (same as NACE)
    "FR": "NAF",       # France - Nomenclature d'Activités Française (same as NACE)
    "PL": "PKD",       # Poland - Polska Klasyfikacja Działalności (same as NACE)
    "ES": "CNAE",      # Spain - Clasificación Nacional de Actividades Económicas (same as NACE)
    "IT": "ATECO",     # Italy - Attività Economiche (same as NACE)
}

# ============================================================
# LOOKUP FUNCTIONS
# ============================================================

def get_description(code: str) -> Optional[str]:
    """Get description for a CAEN/NACE code"""
    return CAEN.get(code.zfill(4))


def get_sector(code: str) -> Optional[str]:
    """Get sector name for a CAEN code"""
    code = code.zfill(4)
    prefix = code[:2]

    for sector_id, sector in SECTORS.items():
        # Check exact codes
        if code in sector.get("codes", []):
            return sector_id
        # Check patterns
        for pattern in sector.get("patterns", []):
            if pattern.endswith("*"):
                if code.startswith(pattern[:-1]):
                    return sector_id
            elif code == pattern:
                return sector_id
    return None


def search_caen(keyword: str, limit: int = 50) -> List[Tuple[str, str, str]]:
    """Search CAEN codes by keyword. Returns [(code, description, sector), ...]"""
    keyword = keyword.lower()
    results = []

    for code, desc in CAEN.items():
        if keyword in desc.lower():
            sector = get_sector(code) or "OTHER"
            results.append((code, desc, sector))
            if len(results) >= limit:
                break

    return results


def get_codes_by_sector(sector: str) -> List[str]:
    """Get all CAEN codes for a sector"""
    if sector not in SECTORS:
        return []

    sector_data = SECTORS[sector]
    codes = list(sector_data.get("codes", []))

    # Expand patterns
    for pattern in sector_data.get("patterns", []):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            for code in CAEN.keys():
                if code.startswith(prefix) and code not in codes:
                    codes.append(code)

    return sorted(codes)


def get_sector_info(sector: str) -> Optional[Dict]:
    """Get full sector information"""
    if sector not in SECTORS:
        return None

    info = SECTORS[sector].copy()
    info["all_codes"] = get_codes_by_sector(sector)
    info["code_count"] = len(info["all_codes"])
    return info


def list_sectors() -> List[str]:
    """List all defined sectors"""
    return list(SECTORS.keys())


def get_all_codes() -> Dict[str, str]:
    """Get all CAEN codes with descriptions"""
    return CAEN.copy()


# ============================================================
# QUICK REFERENCE - Most common codes
# ============================================================

COMMON_CODES = {
    # HORECA
    "5510": "Hotels and similar accommodation",
    "5610": "Restaurants and mobile food service",
    "5630": "Beverage serving activities (bars)",

    # Construction
    "4120": "Construction of buildings",
    "4321": "Electrical installation",
    "4322": "Plumbing, heat and air-conditioning",

    # Manufacturing
    "1011": "Processing and preserving of meat",
    "2511": "Manufacture of metal structures",

    # Transport
    "4941": "Freight transport by road",
    "5210": "Warehousing and storage",

    # IT
    "6201": "Computer programming activities",
    "6202": "Computer consultancy activities",

    # Employment
    "7810": "Activities of employment placement agencies",
    "7820": "Temporary employment agency activities",

    # Call centers
    "8220": "Activities of call centres",

    # Healthcare
    "8710": "Residential nursing care activities",
    "8810": "Social work activities without accommodation for elderly",
}


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("CAEN/NACE Memory Cache")
        print("=" * 50)
        print(f"Total codes loaded: {len(CAEN)}")
        print(f"Sectors defined: {len(SECTORS)}")
        print()
        print("Sectors:")
        for sid, s in SECTORS.items():
            codes = get_codes_by_sector(sid)
            print(f"  {sid:15} - {s['name'][:35]:35} ({len(codes)} codes)")
        print()
        print("Usage:")
        print("  python3 caen_memory.py lookup 5510")
        print("  python3 caen_memory.py search hotel")
        print("  python3 caen_memory.py sector HORECA")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "lookup" and len(sys.argv) > 2:
        code = sys.argv[2]
        desc = get_description(code)
        sector = get_sector(code)
        print(f"Code: {code}")
        print(f"Description: {desc or 'Not found'}")
        print(f"Sector: {sector or 'Unknown'}")

    elif cmd == "search" and len(sys.argv) > 2:
        keyword = " ".join(sys.argv[2:])
        results = search_caen(keyword)
        print(f"Search: '{keyword}' - {len(results)} results")
        for code, desc, sector in results[:20]:
            print(f"  {code}: {desc[:50]} [{sector}]")

    elif cmd == "sector" and len(sys.argv) > 2:
        sector = sys.argv[2].upper()
        info = get_sector_info(sector)
        if info:
            print(f"Sector: {sector}")
            print(f"Name: {info['name']}")
            print(f"Patterns: {info.get('patterns', [])}")
            print(f"Keywords: {info.get('keywords', [])}")
            print(f"Total codes: {info['code_count']}")
            print("Codes:")
            for code in info["all_codes"][:20]:
                print(f"  {code}: {get_description(code)}")
            if info["code_count"] > 20:
                print(f"  ... and {info['code_count'] - 20} more")
        else:
            print(f"Sector not found: {sector}")
            print(f"Available: {', '.join(list_sectors())}")

    elif cmd == "stats":
        print("CAEN Memory Statistics")
        print("=" * 50)
        print(f"Total codes: {len(CAEN)}")
        print(f"Sectors: {len(SECTORS)}")
        for sid in list_sectors():
            codes = get_codes_by_sector(sid)
            print(f"  {sid}: {len(codes)} codes")

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: lookup, search, sector, stats")

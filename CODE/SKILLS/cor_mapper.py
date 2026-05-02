#!/usr/bin/env python3
"""
COR Code Campaign Mapper

Maps Romanian COR (Clasificarea Ocupatiilor din Romania) codes to campaigns.

COR Structure:
- 1st digit: Major group
- 2nd digit: Sub-major group
- 3rd digit: Minor group
- 4th-6th: Specific occupation

Usage:
    from cor_mapper import get_campaigns_for_cor

    campaigns = get_campaigns_for_cor("711301")  # Returns ['BUILDJOBS_RO']
"""

# COR code prefixes -> Campaign mappings
COR_MAPPINGS = {
    # BUILDJOBS_RO - Construction workers
    'BUILDJOBS_RO': [
        '711',   # Building frame workers (zidari, betonisti)
        '712',   # Building finishers (tencuitori, zugravi)
        '713',   # Painters, cleaners
        '7124',  # Instalatori
        '7126',  # Instalatori apa/gaz
        '7212',  # Sudori, oxigenisti
        '7213',  # Tinichigii constructii
        '7411',  # Electricieni constructii
        '8342',  # Operatori utilaje terasamente
        '9312',  # Muncitori constructii civile
        '9313',  # Muncitori constructii drumuri
    ],

    # FACTORYJOBS_RO - Factory/Manufacturing workers
    'FACTORYJOBS_RO': [
        '721',   # Metal workers
        '722',   # Blacksmiths, toolmakers
        '723',   # Machinery mechanics
        '741',   # Electrical equipment installers (non-construction)
        '742',   # Electronics installers
        '751',   # Food processing
        '752',   # Wood treaters
        '753',   # Garment workers
        '754',   # Other craft workers
        '811',   # Mining/mineral processing operators
        '812',   # Metal processing operators
        '813',   # Chemical products operators
        '814',   # Rubber/plastic operators
        '815',   # Textile/fur operators
        '816',   # Food products operators
        '817',   # Wood processing operators
        '818',   # Other stationary plant operators
        '821',   # Assemblers
        '831',   # Locomotive operators
        '832',   # Car/van drivers
        '833',   # Heavy truck drivers
        '834',   # Mobile plant operators
        '932',   # Manufacturing labourers
        '933',   # Transport labourers
    ],

    # CAREWORKERS_RO - Healthcare/Care workers
    'CAREWORKERS_RO': [
        '222',   # Nursing professionals
        '226',   # Other health professionals
        '321',   # Medical technicians
        '322',   # Nursing/midwifery associates
        '323',   # Traditional medicine practitioners
        '324',   # Veterinary technicians
        '325',   # Other health associates
        '531',   # Child care workers
        '532',   # Personal care workers
    ],

    # HORECA_RO - Hotels/Restaurants/Catering
    'HORECA_RO': [
        '141',   # Hotel/restaurant managers
        '343',   # Artistic/cultural associates
        '512',   # Cooks
        '513',   # Waiters, bartenders
        '515',   # Building caretakers
        '516',   # Other personal service workers
        '941',   # Food preparation assistants
        '942',   # Street vendors
    ],

    # DRIVERS_RO - Transport/Logistics
    'DRIVERS_RO': [
        '831',   # Locomotive operators
        '832',   # Car/van/motorcycle drivers
        '833',   # Heavy truck/bus drivers
        '834',   # Mobile plant operators
        '835',   # Ships deck crews
        '933',   # Transport/storage labourers
    ],

    # WAREHOUSE_RO - Warehouse/Logistics
    'WAREHOUSE_RO': [
        '432',   # Material recording clerks
        '4321',  # Stock clerks
        '4322',  # Production clerks
        '8344',  # Forklift operators
        '933',   # Transport/storage labourers
        '9331',  # Hand packers
        '9332',  # Hand labellers
        '9333',  # Freight handlers
        '9334',  # Shelf fillers
        '9621',  # Messengers/package deliverers
    ],
}


def parse_cor_code(cor_string):
    """Extract COR code from string like '711301 - ZIDAR'"""
    if not cor_string:
        return None
    # Try to find 6-digit code at start
    import re
    match = re.match(r'^(\d{6})', str(cor_string).strip())
    if match:
        return match.group(1)
    # Try finding any 6-digit sequence
    match = re.search(r'(\d{6})', str(cor_string))
    if match:
        return match.group(1)
    return None


def get_campaigns_for_cor(cor_code):
    """
    Get list of campaigns matching a COR code.

    Args:
        cor_code: 6-digit COR code or string containing it

    Returns:
        List of campaign names (e.g., ['BUILDJOBS_RO', 'FACTORYJOBS_RO'])
    """
    code = parse_cor_code(cor_code)
    if not code:
        return []

    campaigns = []
    for campaign, prefixes in COR_MAPPINGS.items():
        for prefix in prefixes:
            if code.startswith(prefix):
                campaigns.append(campaign)
                break

    return campaigns


def get_primary_campaign(cor_code):
    """Get the most specific campaign for a COR code."""
    campaigns = get_campaigns_for_cor(cor_code)
    return campaigns[0] if campaigns else None


# Quick test
if __name__ == '__main__':
    test_codes = [
        '711301 - ZIDAR',
        '812101 - OPERATOR MASINI PRELUCRARE METALE',
        '833101 - SOFER AUTOCAMION',
        '512001 - BUCATAR',
        '532103 - INGRIJITOR BATRANI',
    ]

    for code in test_codes:
        campaigns = get_campaigns_for_cor(code)
        print(f"{code[:20]:20} -> {campaigns}")

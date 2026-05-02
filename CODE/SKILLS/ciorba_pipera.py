#!/usr/bin/env python3
"""
Ciorba la Punga - Business Plan Quick Reference

Usage:
    python3 ciorba_pipera.py          # Show summary
    python3 ciorba_pipera.py --full   # Show full plan
    python3 ciorba_pipera.py --target # Show target companies
"""

import sys

SUMMARY = """
=== CIORBA LA PUNGA - CARMOLIMP ===

CONTACT: +40 753 046 260 (Daniel Feraru)
EMAIL: daniel.feraru@carmolimp.ro
WEB: carmolimp.ro

PRETURI (en-gros):
- Ciorba legume: 3.3 RON/portie
- Ciorba burta: 5.9 RON/portie
- Vanzare: 10-15 RON (marja 40-60%)

MODELE:
1. Distribuitor HoReCa (marja 40-60%)
2. Easy-Box operator (automat gratuit)
3. Abonament B2C (39-99 RON/sapt)
4. Contract B2B firme
5. Export Moldova (piata GOALA!)

TARGET PIPERA:
- Oracle: 4,150 angajati
- DB Global Tech: 1,800 angajati
- Ubisoft: 1,557 angajati
- Total potential: 28,500 angajati

PLAN COMPLET: /opt/ACTIVE/IDEAS/FOOD/CIORBA_PUNGA_MASTER.txt
"""

TARGETS = """
=== FIRME TARGET PIPERA ===

TIER 1 (1000+ angajati):
- Oracle Romania: 4,150 | 021 301 5000
- DB Global Technology: 1,800 | UpGround BOB Tower
- Ubisoft Romania: 1,557 | 021 206 9700
- Deloitte: 1,056 | Oregon Park B

CLADIRI:
- UpGround: 9,800 angajati | office@globalworth.com
- Oregon Park: 5,000+ | info@oregon-park.ro
- Green Court: 3,800
- Tower Center: 2,000

CALCUL POTENTIAL:
- 28,500 angajati x 1-2% adoptie = 285-570 clienti
- 1,400-2,800 ciorbe/saptamana
- 56,000-112,000 RON profit/luna
"""

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--full':
            with open('/opt/ACTIVE/IDEAS/FOOD/CIORBA_PUNGA_MASTER.txt') as f:
                print(f.read())
        elif sys.argv[1] == '--target':
            print(TARGETS)
        else:
            print(SUMMARY)
    else:
        print(SUMMARY)

if __name__ == '__main__':
    main()

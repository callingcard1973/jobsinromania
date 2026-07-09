#!/usr/bin/env python3
"""Brazil Producer Scraper - Major Exporters by Sector"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_brazil_producers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known Brazilian exporters by sector - Brazil is the biggest Mercosur economy
KNOWN_EXPORTERS = {
    "beef_poultry": [
        "JBS S.A.", "Marfrig Global Foods", "Minerva Foods", "BRF S.A.",
        "Seara Alimentos", "Aurora Alimentos", "Frigorifico Marba",
        "GTFoods", "Cooperativa Lar", "Copacol", "Frimesa",
        "Coopavel", "C.Vale", "Alibem", "Frigorifico Mataboi"
    ],
    "soy_grains": [
        "Bunge Brasil", "Cargill Brasil", "ADM Brasil", "Louis Dreyfus Brasil",
        "COFCO International", "Amaggi", "Caramuru Alimentos", "Granol",
        "Selecta", "ABC Industria", "Imcopa", "Bianchini", "Camera Agroalimentos",
        "Oleoplan", "Giovelli"
    ],
    "sugar_ethanol": [
        "Raizen", "Cosan", "Sao Martinho", "Biosev", "Tereos Brasil",
        "BP Bunge Bioenergia", "Usina Coruripe", "Usina Colombo",
        "Usina Santa Terezinha", "Usina Jalles Machado", "Usina da Barra",
        "Usina Ester", "Usina Furlan", "Grupo Moreno", "Grupo Toledo"
    ],
    "coffee": [
        "Cooxupe", "Ipanema Coffees", "Cafe Bom Dia", "Daterra Coffee",
        "Fazenda Santa Ines", "Stockler Cafe", "Atlantica Coffee",
        "Cafe Iguacu", "Melitta Brasil", "3 Coracoes", "Cafe Brasileiro",
        "Cafe Damasco", "Tristao Comercio", "Cocapec", "Coocafe"
    ],
    "orange_juice": [
        "Citrosuco", "Louis Dreyfus Citrus", "Cutrale", "Citrovita",
        "Montecitrus", "Sucorrico", "Coagrosol", "Citrusvale"
    ],
    "pulp_paper": [
        "Suzano", "Klabin", "Bracell", "Eldorado Brasil", "Cenibra",
        "Veracel", "Fibria", "International Paper Brasil"
    ],
    "iron_steel": [
        "Vale S.A.", "CSN (Companhia Siderurgica Nacional)", "Gerdau",
        "Usiminas", "ArcelorMittal Brasil", "Ternium Brasil",
        "Acos Villares", "Votorantim Siderurgia"
    ],
    "aluminum": [
        "Albras", "Alcoa Brasil", "CBA", "Novelis Brasil", "Alunorte",
        "Alumar", "Valesul"
    ],
    "lithium_minerals": [
        "Sigma Lithium", "CBL (Companhia Brasileira de Litio)", "AMG Lithium",
        "Latin Resources", "Lithium Ionic", "Atlas Lithium"
    ],
    "niobium": [
        "CBMM", "CMOC Niobras", "Mineracao Taboca", "Anglo American Niobio"
    ],
    "machinery": [
        "WEG", "Embraer", "Randon", "Marcopolo", "AGCO Brasil",
        "John Deere Brasil", "CNH Industrial Brasil", "Jacto",
        "Metalfrio", "Romi"
    ],
    "chemicals": [
        "Braskem", "Oxiteno", "Rhodia Brasil", "Elekeiroz", "Carbocloro",
        "Unipar", "Solvay Brasil", "Innova"
    ],
    "footwear_leather": [
        "Alpargatas", "Grendene", "Arezzo", "Via Uno", "Bibi Calcados",
        "Dakota", "Paqueta", "Vulcabras", "Usaflex", "Piccadilly"
    ],
    "textiles": [
        "Coteminas", "Santista Textil", "Vicunha", "Cedro Textil",
        "Karsten", "Teka", "Dohler", "Buettner"
    ],
    "tobacco": [
        "Souza Cruz", "Universal Leaf Tabacos", "Alliance One Brasil",
        "CTA Continental", "Brasfumo"
    ],
    "honey": [
        "CONAP Brasil", "Prodapys", "Apiarios Girassol", "Breyer",
        "Casa Apis", "NaturApis", "COAPIS", "Apis Flora"
    ],
    "seafood": [
        "Pescados Gomes da Costa", "Cais do Porto", "Netuno",
        "Kowalski", "Pioneira Pescados", "Salte"
    ],
    "fruits": [
        "Vale do Sao Francisco Frutas", "Agrícola Famosa", "Itaueira",
        "Queiroz Galvao Alimentos", "Special Fruit", "Univeg Brasil",
        "Del Monte Brasil", "Dole Brasil", "Fazenda Tamanduá"
    ],
    "wine": [
        "Casa Valduga", "Miolo Wine Group", "Aurora Wines", "Salton",
        "Cooperativa Vinícola Garibaldi", "Boscato", "Don Laurindo",
        "Pizzato", "Lídio Carraro", "Cave Geisse"
    ]
}

def build_from_known():
    """Build list from known exporters"""
    companies = []

    for sector, names in KNOWN_EXPORTERS.items():
        for name in names:
            companies.append({
                "name": name,
                "country": "Brazil",
                "sector": sector,
                "source": "Known Exporter"
            })

    return companies

def main():
    print("=== Brazil Producer Scraper ===")

    all_companies = build_from_known()

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"brazil_producers_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    # Summary by sector
    sectors = {}
    for c in unique:
        s = c["sector"]
        sectors[s] = sectors.get(s, 0) + 1

    print(f"\nTotal unique: {len(unique)}")
    print("\nBy sector:")
    for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
        print(f"  {sector}: {count}")
    print(f"\nSaved to {output_file}")

    return unique

if __name__ == "__main__":
    main()

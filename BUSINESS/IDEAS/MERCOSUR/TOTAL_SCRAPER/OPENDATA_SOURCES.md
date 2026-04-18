# MERCOSUR OPEN DATA SOURCES

## READY TO USE (APIs / Downloads)

### 1. UN COMTRADE (Trade Flows)
```bash
# Get Brazil exports to EU
curl "https://comtradeapi.un.org/public/v1/preview/C/A/HS/068/ALL?reporterCode=076&partnerCode=97"
```
- 200M+ trade records
- By country, HS code, year
- Free API key required

### 2. BRAZIL COMEXSTAT (Customs)
```bash
# Brazilian exports by company
curl "https://api.comexstat.mdic.gov.br/cities/2024"
```
- All Brazilian exporters
- HS codes, values, destinations
- Monthly updates

### 3. WORLD BANK WITS
- URL: https://wits.worldbank.org/data/public/
- Tariff data, trade agreements
- CSV downloads available

### 4. ITC TRADE MAP
- URL: https://www.trademap.org/
- Export/import statistics
- Company-level data (paid)

### 5. ARGENTINA INDEC
```bash
curl "https://datos.gob.ar/dataset/sspm-exportaciones-bienes"
```
- Argentine export statistics
- By product, country, company
- Open data portal

### 6. BRAZIL DATA.GOV.BR
- URL: https://dados.gov.br/
- Company registries (CNPJ)
- Export permits, certifications

### 7. MERCOSUR STATISTICS
- URL: https://estadisticas.mercosur.int/
- Intra-bloc trade data
- Economic indicators

### 8. EU TED (Already Have)
- 1.57M contract winners in DB
- 375K with emails
- Filter by CPV codes for buyers

## DOWNLOAD NOW

### Brazilian Exporters (SECEX)
```bash
wget "https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/EXP_COMPLETA.zip"
# ~2GB - all Brazilian exports since 1997
```

### Argentine Exporters (INDEC)
```bash
wget "https://www.indec.gob.ar/ftp/cuadros/economia/sh_expo_pais.xls"
```

### Chilean Exporters (Aduana)
```bash
wget "https://www.aduana.cl/exportaciones/prontus_aduana/site/artic/20150527/asocfile/exportaciones_por_producto.xlsx"
```

### Uruguay Exports (BCU)
```bash
wget "https://www.bcu.gub.uy/Estadisticas-e-Indicadores/ComercioExterior_ICB/Exportaciones_2024.xlsx"
```

## API KEYS NEEDED

| Source | Free Tier | Rate Limit |
|--------|-----------|------------|
| UN Comtrade | Yes | 100/hour |
| World Bank | Yes | Unlimited |
| Brazil MDIC | Yes | 1000/day |
| ITC Trade Map | No | N/A |

## PRIORITY DOWNLOADS

1. COMEXSTAT Brazil - 50K exporters with HS codes
2. INDEC Argentina - 15K exporters
3. UN Comtrade - Trade flows for matching
4. TED Winners (already have) - 375K EU buyers

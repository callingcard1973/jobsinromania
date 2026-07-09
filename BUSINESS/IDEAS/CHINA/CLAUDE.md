# CLAUDE.md - China Open Data Project

| category | status | owner | updated |
| other | active | tudor | 2026-03-22 |

## Collected Open Data

### 1. Chinese Industrial Enterprise Database (Figshare)
- **Source:** https://figshare.com/articles/dataset/12192207
- **License:** CC BY 4.0 (Open)
- **Size:** 933 MB (.dta Stata format)
- **Records:** ~2.5M+ industrial enterprises (1998-2007)
- **Path:** `/opt/ACTIVE/IDEAS/CHINA/data/opendata/`

| Column | Description |
| year | Year (1998-2007) |
| b011 | Enterprise ID |
| f112 | Fixed assets |
| f115 | Total assets |
| f13 | Total revenue |
| f23 | Total wages |
| f410 | Profit |
| f416 | Total tax |

### 2. NBS China Statistics (API - No Auth)
- **Source:** https://data.stats.gov.cn/english/
- **Path:** `/opt/ACTIVE/IDEAS/CHINA/data/nbs/`

| File | Records | Data |
| china_trade_2020_2024.csv | 104 | Export/import growth |
| gdp_20260322.csv | 192 | Quarterly GDP |
| cpi_20260322.csv | 230 | Consumer Price Index |
| industrial_output_20260322.csv | 22 | Industrial production |

## Available API/Scripts

{TODO: Add content}

## Open Data Sources Summary

### FREE - Downloaded

| Source | Type | Format | Size |
| Figshare Chinese IE DB | Enterprise data | .dta | 933MB |
| NBS China | Trade statistics | CSV | 15KB |

### FREE - Available (Requires Registration)

| Source | URL | Data |
| World Bank Enterprise Survey | microdata.worldbank.org | 2,700 firms |

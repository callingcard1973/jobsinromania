# Ecological Agriculture Producers Scraper

A Python scraper for collecting data about certified organic agriculture producers in Romania from https://www.agriculturaecologica.ro/

## Overview

This scraper extracts comprehensive information about ecological (organic) agriculture producers registered in Romania, including contact details, products, activities, locations, and financial data.

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository
2. Navigate to the project directory:
```bash
cd CODE
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the scraper with default settings:
```bash
python scraper.py
```

This will:
- Scrape all pages from https://www.agriculturaecologica.ro/producatori/
- Save results to `../DATA/producers.csv` and `../DATA/producers.json`
- Generate statistics in `../DATA/stats.json`
- Log progress to `../DATA/scraper.log`

## Output Files

### 1. ../DATA/producers.csv
Comma-separated values file with all producers. Columns include:
- name: Producer name/company
- company_name: Business legal name
- location_city: City name
- location_county: County name
- full_address: Complete address
- postal_code: Postal/ZIP code
- phone: Contact phone number(s)
- website: Company website URL
- facebook: Facebook page URL
- products: List of ecological products
- activities: Type of activities (Production, Processing, Distribution)
- caen_code: Economic activity classification code
- caen_description: Activity description
- certification_date: Last certification date
- revenue: Net sales revenue (RON)
- profit: Net profit (RON)
- employees: Average number of employees
- link: Direct link to producer page

### 2. ../DATA/producers.json
Structured JSON format with the same data

### 3. ../DATA/stats.json
Summary statistics about the scraped data

### 4. ../DATA/scraper.log
Detailed log of all operations

## Data Fields Explained

| Field | Description |
|-------|-------------|
| name | Full registered name of producer |
| location_city | City where producer operates |
| location_county | County (district) name |
| phone | Contact phone number(s) |
| website | Company website |
| facebook | Facebook business page |
| products | Certified organic products (comma-separated) |
| activities | Production, Processing, Distribution, etc. |
| caen_code | CAEN economic classification code |
| certification_date | Date of ecological certification |
| revenue | Annual net sales (RON) |
| profit | Annual net profit (RON) |
| employees | Average number of employees |

## Features

 Automatic pagination handling (supports 339+ pages)
 Rate limiting (0.5s between requests)
 Error handling and retry logic
 Progress logging
 Data validation
 Multiple output formats (CSV, JSON)
 Statistics generation
 ASCII-safe formatting

## Troubleshooting

### Issue: "No module named 'requests'"
**Solution**: Run `pip install -r requirements.txt`

### Issue: Slow performance
**Solution**: Check your internet connection. The script waits between requests on purpose.

### Issue: Encoding problems with CSV
**Solution**: Open with UTF-8 encoding in Excel (Data -> From Text/CSV)

## Legal Notice

This scraper is created for educational and legitimate data analysis purposes. 
- Respects robots.txt and rate limiting
- Does not overload the server
- Follows ethical web scraping practices

## Version History

- v2.1 (2026-03-08): ASCII encoding
  - All files converted to ASCII format
  - Organized CODE and DATA directories
  - Full pagination support (339+ pages)
  
- v1.0 (2026-03-08): Initial release

## License

Free to use and modify for personal/research use.

# Ecological Agriculture Producers Scraper

## Project Description
This project scrapes the registry of certified ecological agriculture producers from **https://www.agriculturaecologica.ro/** to collect comprehensive data about Romanian organic producers.

## Data Target
- **Website**: https://www.agriculturaecologica.ro/producatori/
- **Pages**: All 339+ pages
- **Registry**: Registry of agricultural producers registered in ecological agriculture

## Data Fields to Extract
For each producer, the scraper collects:
1. **Company Name** - Business name
2. **Contact Person/Owner** - Name of responsible person
3. **Location** - City, County, Address
4. **Phone** - Contact phone number(s)
5. **Website** - Company website URL
6. **Facebook** - Facebook page link
7. **Products** - List of ecological products
8. **Activities** - Type of activities (Production, Processing, Distribution)
9. **Postal Code** - Zip code
10. **Address** - Full address
11. **Financial Data** - Revenue, profit, employees (if available)
12. **Certification Date** - Last certification date
13. **CAEN Code** - Activity classification

## Output Format
- **CSV file** with all producers and their information
- **JSON file** for programmatic access
- **Excel spreadsheet** (optional) with multiple sheets by county

## Script Features
- Pagination support (handles all 339+ pages)
- Error handling and retry logic
- Rate limiting to respect server
- Data cleaning and validation
- Duplicate detection
- Progress logging

## Technologies
- Python 3.x
- BeautifulSoup4 - HTML parsing
- Requests - HTTP requests
- Pandas - Data processing
- Openpyxl - Excel export

## Usage
```bash
python scraper.py
```

## Output Files
- `../DATA/producers.csv` - All producers in CSV format
- `../DATA/producers.json` - All producers in JSON format
- `../DATA/stats.json` - Statistics about the scrape
- `../DATA/scraper.log` - Detailed operation log

## Deployment
The code and data can be deployed to remote machines via SSH. A convenience script (`deploy_to_pis.sh`) copies the `CODE/` and `DATA/` directories to targets such as `tudor@raspibig` or `raspi`.

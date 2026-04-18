# Laptop Version: Email Scraping with EmailGrabber 2

## Tool: EmailGrabber 2 (GUI, portable, licensed)
- **Path:** Installed on laptop, run EmailGrabber2.exe
- **License:** Tudor Seicarescu / DUD3-DOE4-5NDE-6UE8
- **Use for:** Large batches on laptop when laptop is ON

## Step 1: Prepare URL lists (one URL per line, .txt file)

Run this to extract websites from each CSV into EmailGrabber-ready .txt files:

```bash
cd "D:/MEMORY/AIR TICKETS"

# France hotels (20,801 websites)
python3 -c "
import csv
with open('D:/MEMORY/CLAUDE/OPT/DATA/EU_TOURISM/france_hebergements_20251220.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
urls = set()
for r in rows:
    for v in r.values():
        v = str(v).strip()
        if v.startswith('http') or v.startswith('www'):
            if not v.startswith('http'): v = 'https://' + v
            urls.add(v)
with open('EMAILGRABBER_INPUT/france_hotels_urls.txt', 'w') as f:
    f.write('\n'.join(sorted(urls)))
print(f'France: {len(urls)} URLs')
"

# OSM hotels (6,089 websites)
python3 -c "
import csv
with open('TOURISM_DATA/osm_hotels_europe_9652.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
urls = [r['website'].strip() for r in rows if r.get('website','').strip()]
urls = ['https://'+u if not u.startswith('http') else u for u in urls]
with open('EMAILGRABBER_INPUT/osm_hotels_urls.txt', 'w') as f:
    f.write('\n'.join(sorted(set(urls))))
print(f'OSM: {len(set(urls))} URLs')
"

# Wikidata hotels (8,254 websites)
python3 -c "
import csv
with open('TOURISM_DATA/wikidata_hotels_30000.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
urls = [r['website'].strip() for r in rows if r.get('website','').strip()]
urls = ['https://'+u if not u.startswith('http') else u for u in urls]
with open('EMAILGRABBER_INPUT/wikidata_hotels_urls.txt', 'w') as f:
    f.write('\n'.join(sorted(set(urls))))
print(f'Wikidata: {len(set(urls))} URLs')
"

# Italy agencies WITHOUT email (3,048 need scraping)
python3 -c "
import csv
with open('TOURISM_DATA/italy_agencies_15769.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
no_email = [r for r in rows if '@' not in str(r.get('Email',''))]
urls = []
for r in no_email:
    for k in r:
        v = str(r[k]).strip()
        if 'http' in v or 'www' in v:
            if not v.startswith('http'): v = 'https://' + v
            urls.append(v)
with open('EMAILGRABBER_INPUT/italy_no_email_urls.txt', 'w') as f:
    f.write('\n'.join(sorted(set(urls))))
print(f'Italy (no email): {len(set(urls))} URLs')
"
```

## Step 2: Load into EmailGrabber 2

1. Open EmailGrabber2.exe
2. File → Import URL List
3. Select the .txt file (e.g., france_hotels_urls.txt)
4. Settings:
   - Crawl depth: 2 (homepage + one level = catches /contact pages)
   - Timeout: 10 seconds
   - Threads: 10-20 (laptop has limited CPU)
5. Start

## Step 3: Export results

1. When done → File → Export → CSV
2. Save to `D:\MEMORY\AIR TICKETS\EMAILGRABBER_OUTPUT\`
3. Name: `france_hotels_emails.csv`, `osm_hotels_emails.csv`, etc.

## Step 4: Merge back with original data

```bash
python3 -c "
import csv
# Merge EmailGrabber output with original CSV by URL
# Adjust column names based on EmailGrabber export format
print('Merge script — adjust after seeing EmailGrabber output format')
"
```

## Processing Order (by value)
1. **France hotels** (20,801 URLs) — biggest batch, run overnight
2. **Wikidata hotels** (8,254 URLs) — global hotels
3. **OSM hotels** (6,089 URLs) — EU hotels
4. **Italy no-email agencies** (~3,048 URLs) — fill gaps in INFOTRAV data

"""Compare laptop vs raspibig OpenData sources and find duplicates."""
import json, re

# Parse laptop sources
laptop = {}
with open("I:/OPENDATA/continuous_downloader.py") as f:
    code = f.read()
# Find all URL assignments
for m in re.finditer(r'"([a-z_]+)":\s*\{[^}]*"url":\s*"([^"]*)"', code, re.DOTALL):
    name, url = m.group(1), m.group(2)
    if url and name not in ("timeout",):
        laptop[name] = url

print(f"LAPTOP: {len(laptop)} sources")
for k,v in sorted(laptop.items()):
    print(f"  {k:25s} {v[:70]}")

# Read raspibig sources from saved copy or parse
print()
raspi_code = open("D:/MEMORY/EMAIL/CODE/_tmp_downloader_full.py", encoding="utf-8").read()
raspi = {}
for m in re.finditer(r'"([a-z_]+)":\s*\{[^}]*"url":\s*"([^"]*)"', raspi_code, re.DOTALL):
    name, url = m.group(1), m.group(2)
    if url and name not in ("timeout",):
        raspi[name] = url

print(f"RASPIBIG: {len(raspi)} sources")
for k,v in sorted(raspi.items()):
    print(f"  {k:25s} {v[:70]}")

# Find duplicates by URL
print(f"\n=== DUPLICATES (same URL on both) ===")
laptop_urls = {v: k for k, v in laptop.items()}
raspi_urls = {v: k for k, v in raspi.items()}
dupes = 0
for url in set(laptop_urls) & set(raspi_urls):
    if url in ("", "dynamic"):
        continue
    print(f"  DUPE: laptop={laptop_urls[url]:20s} raspi={raspi_urls[url]:25s} {url[:60]}")
    dupes += 1

print(f"\n{dupes} duplicate URLs")

print(f"\n=== LAPTOP ONLY ===")
for url, name in sorted(laptop_urls.items()):
    if url not in raspi_urls and url not in ("", "dynamic"):
        print(f"  {name:25s} {url[:70]}")

print(f"\n=== RASPIBIG ONLY ===")
for url, name in sorted(raspi_urls.items()):
    if url not in laptop_urls and url not in ("", "dynamic"):
        print(f"  {name:25s} {url[:70]}")

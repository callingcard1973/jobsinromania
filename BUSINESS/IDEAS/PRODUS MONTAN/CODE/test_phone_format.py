#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re

try:
    print("Fetching page...")
    response = requests.get('https://www.agriculturaecologica.ro/producatori/', timeout=10)
    print(f"Status: {response.status_code}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    producers = soup.find_all('article')
    print(f"Found {len(producers)} producers")
    
    # Check first 3 producers for ANY numeric patterns
    for i, producer in enumerate(producers[:3]):
        text = producer.get_text()
        print(f"\n=== Producer {i+1} ===")
        print(f"Text length: {len(text)}")
        print(f"First 500 chars:\n{text[:500]}")
        
        # Look for any sequence of digits
        digits_pattern = re.findall(r'[0-9]{3,}', text)
        if digits_pattern:
            print(f"Number sequences found: {digits_pattern[:5]}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re

response = requests.get('https://www.agriculturaecologica.ro/producatori/')
soup = BeautifulSoup(response.content, 'html.parser')

producer = soup.find('article')
if producer:
    text = producer.get_text()
    print("=== PRODUCER TEXT (first 1500 chars) ===")
    print(text[:1500])
    print("\n=== FULL HTML (first 1500 chars) ===")
    print(producer.prettify()[:1500])
    print("\n=== LOOKING FOR PHONE PATTERNS ===")
    patterns = [
        (r'[+]?40[\s.-]?[0-9]{2,4}[\s.-]?[0-9]{3}[\s.-]?[0-9]{3}', 'International +40'),
        (r'0[\s.-]?[0-9]{2,4}[\s.-]?[0-9]{3}[\s.-]?[0-9]{3}', 'Domestic 0'),
        (r'[0-9]{3}[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}', 'Generic pattern'),
    ]
    for pattern, name in patterns:
        matches = re.findall(pattern, text)
        if matches:
            print(f"{name}: {matches[:3]}")
        else:
            print(f"{name}: NOT FOUND")

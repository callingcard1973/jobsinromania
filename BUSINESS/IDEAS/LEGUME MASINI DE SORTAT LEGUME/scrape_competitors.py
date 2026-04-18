import requests, re
from bs4 import BeautifulSoup

urls = {
    'AGRITECH': 'https://www.agritech.com.ro/category/recoltare-si-ambalare/masini-de-recoltat-legume/',
    'GreenGarden': 'https://www.greengarden.ro',
    'MARCOSER': 'https://www.marcoser.ro',
    'Equinto': 'https://www.eqinto.eu',
    'Agrialianta': 'https://agrialianta.com',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
}

for name, url in urls.items():
    print('\n' + '=' * 60)
    print(f'{name}: {url}')
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else ''
        print('Title:', title)

        paragraphs = []
        for p in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p']):
            txt = p.get_text(' ', strip=True)
            if txt and len(txt) > 30 and re.search(r'legum|sort|ambal', txt, re.I):
                paragraphs.append(txt)
                if len(paragraphs) >= 6:
                    break

        print('Key texts:')
        for i, p in enumerate(paragraphs, 1):
            print(f' {i}.', p)

        found = set(re.findall(r'\d[\d\s\.,]*\s*(?:EUR|eur|Eur|RON|lei|Lei|EURO|€)', r.text))
        if found:
            print('Price hints:')
            for f in sorted(found)[:10]:
                print(' -', f)
        else:
            print('Price hints: none found')

    except Exception as e:
        print('ERROR:', str(e))

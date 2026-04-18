# Step-by-step: Bypass Cloudflare JS challenge with browser automation

## 1. Install Python dependencies

```bash
pip install selenium webdriver-manager
```

## 2. Download Chrome or Edge browser (if not installed)
- Chrome: https://www.google.com/chrome/
- Edge: https://www.microsoft.com/edge

## 3. Example Python script (Selenium + Chrome)

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument('--headless=new')  # Remove for visible browser
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')

# Start browser
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get('https://listafirme.ro/')
    time.sleep(10)  # Wait for Cloudflare JS challenge to pass
    # Save page source
    with open('listafirme_ro_real.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print('Page source saved.')
finally:
    driver.quit()
```

## 4. Inspect the saved HTML (listafirme_ro_real.html)
- Open in VS Code or browser
- Search for <script>, <link>, and tech stack clues

## 5. (Optional) Extract loaded JS/CSS URLs
- Use BeautifulSoup or browser DevTools for further analysis

---

**Note:**
- This method simulates a real browser, bypassing Cloudflare's JS/cookie challenge.
- For Puppeteer (Node.js), a similar approach applies.
- If Cloudflare presents a CAPTCHA, manual intervention may be required.

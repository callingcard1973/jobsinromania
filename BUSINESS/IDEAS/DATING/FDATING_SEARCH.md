# fdating.com — Profile Search Project

## Status: PLANNED

## What
Use Tudor's existing fdating.com account to search, filter, and organize profiles of interesting women.

## Tech Assessment (2026-04-12)
- No Cloudflare, no CAPTCHA — simple HTML scraping
- Custom AJAX (xajax), server-rendered pages
- Quick Search: gender, age 18-99, 200+ countries, photo filter
- 30 profiles per page
- Photo paths: `/images/photos/U###/C###/`
- No API — BeautifulSoup scraping sufficient

## TODO
- Define criteria (age, country, language, preferences)
- Scrape matching profiles into CSV (name, age, country, photo, profile URL)
- Review and shortlist
- Draft personalized messages for selected profiles

## Notes
- Tudor has an active account
- Personal project, not business

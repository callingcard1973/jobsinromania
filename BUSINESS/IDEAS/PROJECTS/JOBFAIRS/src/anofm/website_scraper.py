"""
ANOFM Website Scraper

Scrapes job fair events from the Romanian National Employment Agency (ANOFM) website.
Handles Romanian HTML content, date parsing, and region detection.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as dateparse

from config import get_config


class ANOFMWebsiteScraper:
    """
    Web scraper for ANOFM website to extract job fair events.

    Features:
    - Parse Romanian HTML content
    - Extract event details (name, date, location, contacts)
    - Handle multiple date formats and Romanian month names
    - Detect Romanian regions/counties from text
    - Validate event content (filter out non-job-fair events)
    """

    # Romanian month names mapping
    ROMANIAN_MONTHS = {
        'ianuarie': 'january', 'februarie': 'february', 'martie': 'march',
        'aprilie': 'april', 'mai': 'may', 'iunie': 'june',
        'iulie': 'july', 'august': 'august', 'septembrie': 'september',
        'octombrie': 'october', 'noiembrie': 'november', 'decembrie': 'december',
        'ian': 'jan', 'feb': 'feb', 'mar': 'mar', 'apr': 'apr',
        'iun': 'jun', 'iul': 'jul', 'aug': 'aug', 'sep': 'sep',
        'oct': 'oct', 'noi': 'nov', 'dec': 'dec'
    }

    # Romanian counties for region detection
    ROMANIAN_COUNTIES = [
        'Alba', 'Arad', 'Argeș', 'Bacău', 'Bihor', 'Bistrița-Năsăud', 'Botoșani',
        'Brașov', 'Brăila', 'București', 'Buzău', 'Caraș-Severin', 'Călărași',
        'Cluj', 'Constanța', 'Covasna', 'Dâmbovița', 'Dolj', 'Galați', 'Giurgiu',
        'Gorj', 'Harghita', 'Hunedoara', 'Ialomița', 'Iași', 'Ilfov', 'Maramureș',
        'Mehedinți', 'Mureș', 'Neamț', 'Olt', 'Prahova', 'Satu Mare', 'Sălaj',
        'Sibiu', 'Suceava', 'Teleorman', 'Timiș', 'Tulcea', 'Vaslui', 'Vâlcea', 'Vrancea'
    ]

    # Job fair keywords (Romanian)
    JOB_FAIR_KEYWORDS = [
        'bursa', 'burse', 'locuri de munca', 'angajare', 'angajari', 'recrutare',
        'cariera', 'job fair', 'fair', 'târg', 'târgul', 'evenimente', 'eveniment'
    ]

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the scraper with configuration."""
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)

        # HTTP session for efficient requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def scrape_events(self, max_pages: int = 5) -> List[Dict]:
        """
        Scrape job fair events from ANOFM website.

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            List of event dictionaries with extracted data
        """
        events = []
        base_url = self.config.anofm.base_url
        job_fairs_path = self.config.anofm.job_fairs_path

        try:
            for page in range(1, max_pages + 1):
                self.logger.info(f"Scraping ANOFM events page {page}")

                # Construct URL for current page
                if page == 1:
                    url = urljoin(base_url, job_fairs_path)
                else:
                    url = f"{urljoin(base_url, job_fairs_path)}?page={page}"

                page_events = self._scrape_page(url)
                if not page_events:
                    self.logger.info(f"No events found on page {page}, stopping")
                    break

                events.extend(page_events)
                self.logger.info(f"Found {len(page_events)} events on page {page}")

        except Exception as e:
            self.logger.error(f"Error scraping ANOFM website: {e}")

        self.logger.info(f"Total events scraped: {len(events)}")
        return events

    def _scrape_page(self, url: str) -> List[Dict]:
        """Scrape events from a single page."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            return self._extract_events_from_soup(soup, url)

        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to parse page {url}: {e}")
            return []

    def _extract_events_from_soup(self, soup: BeautifulSoup, source_url: str) -> List[Dict]:
        """Extract event data from parsed HTML."""
        events = []

        # Try multiple selectors for event containers
        event_selectors = [
            '.event-item', '.event', '.article-item', '.news-item',
            '.content-item', '[class*="event"]', '[class*="bursa"]',
            'article', '.post', '.entry'
        ]

        event_elements = []
        for selector in event_selectors:
            elements = soup.select(selector)
            if elements:
                event_elements = elements
                self.logger.debug(f"Found {len(elements)} potential events using selector: {selector}")
                break

        # If no specific event containers found, look for general content
        if not event_elements:
            # Look for content with job fair keywords
            all_elements = soup.find_all(['div', 'article', 'section'], string=True)
            for element in all_elements:
                text = element.get_text(strip=True).lower()
                if any(keyword in text for keyword in self.JOB_FAIR_KEYWORDS):
                    event_elements.append(element)

        for element in event_elements:
            try:
                event_data = self._extract_event_data(element, source_url)
                if event_data and self._is_valid_job_fair_event(event_data):
                    events.append(event_data)
            except Exception as e:
                self.logger.warning(f"Failed to extract event data from element: {e}")
                continue

        return events

    def _extract_event_data(self, element: BeautifulSoup, source_url: str) -> Optional[Dict]:
        """Extract structured data from an event element."""
        # Get all text content
        text = element.get_text(separator=' ', strip=True)
        if len(text) < 20:  # Skip very short content
            return None

        # Extract event name (usually the first heading or title)
        name = self._extract_event_name(element)
        if not name:
            return None

        # Extract dates
        event_date, end_date, registration_deadline = self._extract_dates(text)

        # Extract location and region
        location, region = self._extract_location_and_region(text)

        # Extract contact information
        contacts = self._extract_contact_info(text)

        # Extract URL if available
        event_url = self._extract_event_url(element, source_url)

        return {
            'name': name,
            'date': event_date,
            'end_date': end_date,
            'location': location,
            'region': region,
            'organizer_email': contacts.get('email'),
            'organizer_phone': contacts.get('phone'),
            'organizer_contact': contacts.get('contact_person'),
            'registration_deadline': registration_deadline,
            'anofm_url': event_url,
            'raw_text': text,  # Keep raw text for debugging
            'last_scraped': datetime.now()
        }

    def _extract_event_name(self, element: BeautifulSoup) -> Optional[str]:
        """Extract event name from element."""
        # Try heading tags first
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            heading = element.find(tag)
            if heading:
                name = heading.get_text(strip=True)
                if len(name) > 10 and any(keyword in name.lower() for keyword in self.JOB_FAIR_KEYWORDS):
                    return name

        # Try title attribute
        if element.get('title'):
            return element.get('title').strip()

        # Try first line of text that contains job fair keywords
        lines = element.get_text(separator='\n').split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if len(line) > 10 and any(keyword in line.lower() for keyword in self.JOB_FAIR_KEYWORDS):
                return line

        return None

    def _extract_dates(self, text: str) -> Tuple[Optional[date], Optional[date], Optional[date]]:
        """Extract event dates from text."""
        event_date = None
        end_date = None
        registration_deadline = None

        # Normalize Romanian text for date parsing
        normalized_text = self._normalize_romanian_dates(text)

        # Date patterns (Romanian)
        date_patterns = [
            r'(\d{1,2})\s+(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie)\s+(\d{4})',
            r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})',
            r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',
            r'(\d{1,2})\s+(ian|feb|mar|apr|mai|iun|iul|aug|sep|oct|noi|dec)\s+(\d{4})',
        ]

        dates_found = []

        for pattern in date_patterns:
            matches = re.finditer(pattern, normalized_text, re.IGNORECASE)
            for match in matches:
                try:
                    parsed_date = self._parse_romanian_date(match.group())
                    if parsed_date and parsed_date >= date.today():
                        dates_found.append(parsed_date)
                except:
                    continue

        # Sort dates and assign roles
        dates_found = sorted(set(dates_found))

        if len(dates_found) >= 1:
            event_date = dates_found[0]
        if len(dates_found) >= 2:
            end_date = dates_found[1]

        # Look for registration deadline keywords
        deadline_text = re.search(r'(înscrier|înscriere|termen|limita).*?(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})', text, re.IGNORECASE)
        if deadline_text:
            try:
                registration_deadline = self._parse_romanian_date(deadline_text.group(2))
            except:
                pass

        return event_date, end_date, registration_deadline

    def _normalize_romanian_dates(self, text: str) -> str:
        """Normalize Romanian month names for parsing."""
        normalized = text
        for ro_month, en_month in self.ROMANIAN_MONTHS.items():
            normalized = re.sub(rf'\b{re.escape(ro_month)}\b', en_month, normalized, flags=re.IGNORECASE)
        return normalized

    def _parse_romanian_date(self, date_str: str) -> Optional[date]:
        """Parse a Romanian date string."""
        try:
            # First try manual parsing for common Romanian formats to ensure correct DD.MM interpretation
            patterns = [
                r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})',  # DD.MM.YYYY or DD/MM/YYYY
                r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',  # YYYY-MM-DD
            ]

            for pattern in patterns:
                match = re.search(pattern, date_str)
                if match:
                    try:
                        # Determine format based on first group length
                        if len(match.group(1)) <= 2:
                            # DD.MM.YYYY format (Romanian standard)
                            day, month, year = match.groups()
                        else:
                            # YYYY-MM-DD format (ISO)
                            year, month, day = match.groups()

                        return date(int(year), int(month), int(day))
                    except (ValueError, TypeError):
                        continue

            # If manual parsing fails, try dateutil with normalized Romanian text
            normalized = self._normalize_romanian_dates(date_str)
            parsed = dateparse(normalized, fuzzy=True)
            if parsed:
                return parsed.date()

        except Exception:
            pass

        return None

    def _extract_location_and_region(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract location and Romanian region from text."""
        location = None
        region = None

        # Look for county names in text
        text_lower = text.lower()
        for county in self.ROMANIAN_COUNTIES:
            if county.lower() in text_lower:
                region = county
                break

        # Extract location using common patterns
        location_patterns = [
            r'(?:la|în|la)\s+([A-Z][a-záăîșțâ\s]+)',
            r'(?:oraș|comuna|municipiul)\s+([A-Z][a-záăîșțâ\s]+)',
            r'(?:adresa|locația|location):\s*([A-Za-záăîșțâ\s,]+)',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_location = match.group(1).strip()
                if len(potential_location) > 3 and len(potential_location) < 100:
                    location = potential_location
                    break

        return location, region

    def _extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information from text."""
        contacts = {
            'email': None,
            'phone': None,
            'contact_person': None
        }

        # Email pattern
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            contacts['email'] = email_match.group()

        # Phone pattern (Romanian format)
        phone_patterns = [
            r'(\+40|0040)?\s*[23478]\d{8}',
            r'(\+40|0040)?\s*[23478]\d{2}[\s\-\.]\d{3}[\s\-\.]\d{3}',
            r'tel[:\s]*(\+?40)?[\s\-\.]?[23478]\d{2}[\s\-\.]\d{3}[\s\-\.]\d{3}'
        ]

        for pattern in phone_patterns:
            phone_match = re.search(pattern, text, re.IGNORECASE)
            if phone_match:
                contacts['phone'] = phone_match.group().strip()
                break

        # Contact person (look for names after contact keywords)
        contact_patterns = [
            r'(?:contact|persoana de contact|responsabil):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'(?:domnul|doamna)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]

        for pattern in contact_patterns:
            contact_match = re.search(pattern, text, re.IGNORECASE)
            if contact_match:
                contacts['contact_person'] = contact_match.group(1).strip()
                break

        return contacts

    def _extract_event_url(self, element: BeautifulSoup, source_url: str) -> Optional[str]:
        """Extract event-specific URL if available."""
        # Look for links in the element
        link = element.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('http'):
                return href
            else:
                return urljoin(source_url, href)

        return source_url  # Return source URL as fallback

    def _is_valid_job_fair_event(self, event_data: Dict) -> bool:
        """
        Validate if the extracted data represents a valid job fair event.

        Filters out non-job-fair events like general announcements,
        training programs, or administrative notices.
        """
        if not event_data.get('name') or not event_data.get('date'):
            return False

        name_lower = event_data['name'].lower()
        text_lower = event_data.get('raw_text', '').lower()

        # Must contain job fair keywords
        if not any(keyword in name_lower or keyword in text_lower for keyword in self.JOB_FAIR_KEYWORDS):
            return False

        # Exclude non-event content
        exclude_keywords = [
            'anunț', 'anunturi', 'comunicat', 'hotărâre', 'regulament',
            'metodologie', 'ghid', 'formular', 'cerere', 'raport'
        ]

        if any(keyword in name_lower for keyword in exclude_keywords):
            return False

        # Event should have a future date
        if event_data['date'] < date.today():
            return False

        # Should have a valid Romanian region if region is detected
        if event_data.get('region') and event_data['region'] not in self.ROMANIAN_COUNTIES:
            return False

        return True

    def test_scraping(self, url: Optional[str] = None) -> Dict:
        """Test the scraping functionality on a specific URL or default ANOFM page."""
        if not url:
            url = urljoin(self.config.anofm.base_url, self.config.anofm.job_fairs_path)

        self.logger.info(f"Testing scraping on: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            events = self._extract_events_from_soup(soup, url)

            return {
                'url': url,
                'status_code': response.status_code,
                'page_title': soup.title.string if soup.title else 'No title',
                'events_found': len(events),
                'events': events,
                'success': True
            }
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'success': False
            }
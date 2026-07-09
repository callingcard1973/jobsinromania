#!/usr/bin/env python3
"""
Scraper for Ecological Agriculture Producers Registry
Scrapes https://www.agriculturaecologica.ro/producatori/
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
from urllib.parse import urljoin
from typing import List, Dict, Optional
import logging
from datetime import datetime
import os
import sys

# Configure logging to save in DATA directory
data_dir = os.path.join(os.path.dirname(__file__), '..', 'DATA')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

log_file = os.path.join(data_dir, 'scraper.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProducerScraper:
    """Scraper for ecological agriculture producers"""
    
    def __init__(self, base_url: str = "https://www.agriculturaecologica.ro"):
        self.base_url = base_url
        self.producers_url = urljoin(base_url, "/producatori/")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.producers = []
        self.rate_limit_delay = 0.5  # seconds between requests
        
    def fetch_page(self, page_num: int = 1) -> Optional[BeautifulSoup]:
        """Fetch and parse a single page"""
        try:
            if page_num == 1:
                url = self.producers_url
            else:
                url = f"{self.producers_url}page/{page_num}/"
            
            logger.info(f"Fetching page {page_num}: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            time.sleep(self.rate_limit_delay)
            return BeautifulSoup(response.content, 'html.parser')
        
        except requests.RequestException as e:
            logger.error(f"Error fetching page {page_num}: {e}")
            return None
    
    def extract_producer_info(self, producer_html) -> Dict[str, str]:
        """Extract information from a producer section"""
        info = {
            'name': '',
            'company_name': '',
            'location_city': '',
            'location_county': '',
            'full_address': '',
            'postal_code': '',
            'phone': '',
            'website': '',
            'facebook': '',
            'products': '',
            'activities': '',
            'caen_code': '',
            'caen_description': '',
            'certification_date': '',
            'revenue': '',
            'profit': '',
            'employees': '',
            'link': ''
        }
        
        try:
            # Main heading with link
            h3 = producer_html.find('h3')
            if h3 and h3.a:
                info['name'] = h3.a.get_text(strip=True)
                info['link'] = h3.a.get('href', '')
            
            # Location info
            location_links = producer_html.find_all('a', href=True)
            county_text = ""
            city_text = ""
            
            for link in location_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if '/localitate/' in href:
                    if 'judetul' in href or 'judet' in text.lower():
                        county_text = text
                    else:
                        city_text = text
            
            info['location_county'] = county_text
            info['location_city'] = city_text
            
            # Extract all links from the section
            all_links = producer_html.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Website
                if href.startswith(('http://', 'https://')) and '/localitate/' not in href and 'facebook.com' not in href and 'agriculturaecologica.ro' not in href:
                    if 'vbio.ro' in href or 'store.ro' in href or '.ro' in href:
                        info['website'] = href
                
                # Facebook
                if 'facebook.com' in href:
                    info['facebook'] = href
                
                # Products
                if '/produs-ecologic/' in href:
                    if info['products']:
                        info['products'] += f", {text}"
                    else:
                        info['products'] = text
                
                # Activities
                if '/tipul-activitatii/' in href:
                    if info['activities']:
                        info['activities'] += f", {text}"
                    else:
                        info['activities'] = text
                
                # CAEN code
                if '/caen/' in href:
                    caen_match = href.split('/caen/')[1].split('-')[0] if '/caen/' in href else ''
                    if caen_match:
                        info['caen_code'] = caen_match
                    info['caen_description'] = text
            
            # Financial data and other info from text
            text_full = producer_html.get_text()
            import re
            
            # Extract postal code and address
            postal_match = re.search(r'\d{6}', text_full)
            if postal_match:
                info['postal_code'] = postal_match.group()
            
            # Extract financial info
            if 'Cifra de afaceri neta' in text_full:
                revenue_match = re.search(r'Cifra de afaceri neta\s+([\d.,\s]+)\s*RON', text_full)
                if revenue_match:
                    info['revenue'] = revenue_match.group(1).strip()
            
            if 'Profit net' in text_full:
                profit_match = re.search(r'Profit net\s+([\d.,\s-]+)\s*RON', text_full)
                if profit_match:
                    info['profit'] = profit_match.group(1).strip()
            
            if 'Nr. mediu salariati' in text_full:
                emp_match = re.search(r'Nr. mediu salariati\s+(\d+)', text_full)
                if emp_match:
                    info['employees'] = emp_match.group(1)
            
            # Certification date
            if 'ianuarie 202' in text_full:
                date_match = re.search(r'(\d+ ianuarie 202\d)', text_full)
                if date_match:
                    info['certification_date'] = date_match.group(1)
            
        except Exception as e:
            logger.warning(f"Error extracting producer info: {e}")
        
        return info
    
    def scrape_all_pages(self, max_pages: Optional[int] = None) -> List[Dict]:
        """Scrape all pages of producers"""
        page = 1
        consecutive_empty_pages = 0
        
        while max_pages is None or page <= max_pages:
            soup = self.fetch_page(page)
            if not soup:
                logger.warning(f"Failed to fetch page {page}")
                page += 1
                continue
            
            # Find all producer articles
            producer_sections = soup.find_all('article')
            
            if not producer_sections:
                consecutive_empty_pages += 1
                logger.info(f"No producers found on page {page}")
                
                # Allow some empty pages in case of sparse pagination
                if consecutive_empty_pages >= 5:
                    logger.info("5 consecutive empty pages, stopping")
                    break
                page += 1
                continue
            
            consecutive_empty_pages = 0
            logger.info(f"Found {len(producer_sections)} producers on page {page}")
            
            for section in producer_sections:
                producer_info = self.extract_producer_info(section)
                if producer_info.get('name'):
                    self.producers.append(producer_info)
            
            # Try multiple ways to detect if there are more pages
            has_next_page = False
            
            # Method 1: Look for rel='next'
            next_button = soup.find('a', rel='next')
            if next_button:
                has_next_page = True
            
            # Method 2: Look for pagination links with page numbers
            if not has_next_page:
                page_links = soup.find_all('a', href=True)
                for link in page_links:
                    href = link.get('href', '')
                    if f'/page/{page + 1}/' in href:
                        has_next_page = True
                        break
            
            # Method 3: Just try the next page (pagination might be continuous)
            if not has_next_page and page < 400:
                has_next_page = True
            elif page >= 400:
                logger.info("Reached page limit of 400")
                break
            
            if not has_next_page and consecutive_empty_pages == 0:
                logger.info("No pagination indicators found, stopping")
                break
            
            page += 1
        
        logger.info(f"Total producers scraped: {len(self.producers)}")
        return self.producers
    
    def save_to_csv(self, filepath: str = None) -> None:
        """Save producers to CSV file"""
        if filepath is None:
            filepath = os.path.join(data_dir, 'producers.csv')
        
        if not self.producers:
            logger.warning("No producers to save")
            return
        
        try:
            fieldnames = list(self.producers[0].keys())
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.producers)
            
            logger.info(f"Saved {len(self.producers)} producers to {filepath}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
    
    def save_to_json(self, filepath: str = None) -> None:
        """Save producers to JSON file"""
        if filepath is None:
            filepath = os.path.join(data_dir, 'producers.json')
        
        if not self.producers:
            logger.warning("No producers to save")
            return
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.producers, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self.producers)} producers to {filepath}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def save_stats(self, filepath: str = None) -> None:
        """Save statistics about scraped data"""
        if filepath is None:
            filepath = os.path.join(data_dir, 'stats.json')
        
        if not self.producers:
            return
        
        stats = {
            'total_producers': len(self.producers),
            'scrape_date': datetime.now().isoformat(),
            'producers_with_website': sum(1 for p in self.producers if p.get('website')),
            'producers_with_phone': sum(1 for p in self.producers if p.get('phone')),
            'producers_with_facebook': sum(1 for p in self.producers if p.get('facebook')),
            'unique_counties': len(set(p.get('location_county', '') for p in self.producers if p.get('location_county'))),
            'unique_cities': len(set(p.get('location_city', '') for p in self.producers if p.get('location_city'))),
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved statistics to {filepath}")
        except Exception as e:
            logger.error(f"Error saving stats: {e}")


def main():
    """Main execution"""
    logger.info("Starting scraper for ecological agriculture producers")
    
    scraper = ProducerScraper()
    scraper.scrape_all_pages()
    scraper.save_to_csv()
    scraper.save_to_json()
    scraper.save_stats()
    
    logger.info("Scraping completed successfully")


if __name__ == "__main__":
    main()

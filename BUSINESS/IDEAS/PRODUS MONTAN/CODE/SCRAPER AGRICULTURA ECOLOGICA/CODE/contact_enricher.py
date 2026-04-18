#!/usr/bin/env python3
"""
Enhanced scraper that fetches individual producer pages for contact details
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import re
from typing import Optional, List, Dict
import logging
from datetime import datetime
import os

# Configure logging
data_dir = os.path.join(os.path.dirname(__file__), '..', 'DATA')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(data_dir, 'contact_enricher.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContactEnricher:
    """Enriches producer data with contact details from detail pages"""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.producers = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.rate_limit_delay = 0.3  # seconds between requests
    
    def load_csv(self):
        """Load existing CSV data"""
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.producers = list(reader)
        logger.info(f"Loaded {len(self.producers)} producers from CSV")
    
    def normalize_phone(self, phone: str) -> Optional[str]:
        """Normalize phone number to format: +40 XXX XXX XXX"""
        if not phone or not isinstance(phone, str):
            return None
        
        # Remove all spaces, dashes, dots, parentheses
        normalized = re.sub(r'[\s()\-.]', '', phone.strip())
        
        # Extract digits only
        digits_only = re.sub(r'\D', '', normalized)
        
        # Skip if too short
        if len(digits_only) < 9:
            return None
        
        # Handle different patterns
        if normalized.startswith('+40'):
            # International format already
            digits = digits_only[2:]  # Remove country code
        elif normalized.startswith('+'):
            # Keep other international formats as-is
            return phone.strip()
        elif normalized.startswith('0040') or normalized.startswith('00'):
            # International without +
            digits = digits_only[2:]
        elif normalized.startswith('0'):
            # Domestic format
            digits = digits_only[1:]
        else:
            # Assume domestic if just digits
            digits = digits_only
        
        # Ensure we have enough digits
        if len(digits) < 9:
            return None
        
        # Format as +40 XXX XXX XXX
        digits = digits[:9]
        return f"+40 {digits[0:3]} {digits[3:6]} {digits[6:9]}"
    
    def extract_contact_from_detail_page(self, detail_url: str) -> Dict[str, str]:
        """Fetch and extract contact details from a producer's detail page"""
        contact_info = {
            'phone': '',
            'email': '',
            'address': ''
        }
        
        try:
            logger.debug(f"Fetching detail page: {detail_url}")
            response = self.session.get(detail_url, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            # Extract phone numbers using multiple patterns
            phone_patterns = [
                r'\+?40[\s\-.]?[0-9]{2}[\s\-.]?[0-9]{3}[\s\-.]?[0-9]{3}',  # +40 or 40 format
                r'0[\s\-.]?[0-9]{2}[\s\-.]?[0-9]{3}[\s\-.]?[0-9]{3}',  # 0XX XXX XXX
                r'\+?40\s?[0-9]{9}',  # +40 without formatting
                r'0[0-9]{9}',  # 0 without formatting
            ]
            
            phones_found = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    normalized = self.normalize_phone(match)
                    if normalized and normalized not in phones_found:
                        phones_found.append(normalized)
            
            if phones_found:
                contact_info['phone'] = ', '.join(phones_found[:2])  # Max 2 phones
            
            # Extract email addresses
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails_found = re.findall(email_pattern, page_text)
            if emails_found:
                contact_info['email'] = ', '.join(list(set(emails_found))[:2])
            
            # Extract address (look for postal code and text before it)
            postal_pattern = r'[0-9]{6}'
            postal_match = re.search(postal_pattern, page_text)
            if postal_match:
                contact_info['address'] = page_text[max(0, postal_match.start()-200):postal_match.end()+50].strip()
                # Clean up the address
                contact_info['address'] = re.sub(r'\s+', ' ', contact_info['address'])[:150]
            
        except Exception as e:
            logger.warning(f"Error fetching detail page {detail_url}: {e}")
        
        return contact_info
    
    def enrich_producer(self, producer: Dict, index: int) -> Dict:
        """Enrich a single producer with contact details"""
        if not producer.get('link'):
            return producer
        
        if (index + 1) % 100 == 0:
            logger.info(f"Processing producer {index + 1}/{len(self.producers)}")
        
        contact_info = self.extract_contact_from_detail_page(producer['link'])
        
        # Update producer data, preferring newly extracted data
        if contact_info['phone'] and not producer.get('phone'):
            producer['phone'] = contact_info['phone']
        if contact_info['email'] and not producer.get('email'):
            producer['email'] = contact_info['email']
        if contact_info['address'] and not producer.get('full_address'):
            producer['full_address'] = contact_info['address']
        
        return producer
    
    def enrich_all(self, max_producers: Optional[int] = None):
        """Enrich all producers with contact details"""
        limit = min(max_producers or len(self.producers), len(self.producers))
        logger.info(f"Starting to enrich {limit} producers with contact details...")
        
        for i, producer in enumerate(self.producers[:limit]):
            try:
                self.producers[i] = self.enrich_producer(producer, i)
            except Exception as e:
                logger.error(f"Error processing producer {i}: {e}")
                continue
        
        logger.info(f"Completed enrichment of {limit} producers")
    
    def save_enriched_csv(self, output_file: str = None):
        """Save enriched data to CSV"""
        if output_file is None:
            output_file = os.path.join(data_dir, 'producers_enriched.csv')
        
        if not self.producers:
            logger.warning("No producers to save")
            return
        
        try:
            fieldnames = list(self.producers[0].keys())
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.producers)
            
            logger.info(f"Saved {len(self.producers)} enriched producers to {output_file}")
        except Exception as e:
            logger.error(f"Error saving enriched CSV: {e}")
    
    def generate_stats(self):
        """Generate statistics about enrichment"""
        stats = {
            'total_producers': len(self.producers),
            'producers_with_phone': sum(1 for p in self.producers if p.get('phone', '').strip()),
            'producers_with_email': sum(1 for p in self.producers if p.get('email', '').strip()),
            'producers_with_address': sum(1 for p in self.producers if p.get('full_address', '').strip()),
            'enrichment_date': datetime.now().isoformat()
        }
        
        stats_file = os.path.join(data_dir, 'enrichment_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Statistics: {stats['producers_with_phone']} with phone, {stats['producers_with_email']} with email")
        return stats


def main():
    """Main execution"""
    csv_file = os.path.join(data_dir, 'producers.csv')
    
    enricher = ContactEnricher(csv_file)
    enricher.load_csv()
    enricher.enrich_all(max_producers=None)  # Process ALL producers
    enricher.save_enriched_csv()
    enricher.generate_stats()


if __name__ == "__main__":
    main()

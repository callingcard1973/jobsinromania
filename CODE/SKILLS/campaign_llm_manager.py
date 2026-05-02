#!/usr/bin/env python3
"""
Campaign LLM Manager - Intelligent campaign automation with LLM-powered error fixing.

Features:
1. Auto-loads CSV into campaigns when running low (< 100 contacts)
2. Start/stop campaigns via dashboard API (port 8088)
3. LLM escalation: rules -> llama-3.2-3b -> Cerebras 70b -> human (Telegram)
4. Auto-fixes common script errors using patterns + LLM

Usage:
    python3 campaign_llm_manager.py --status         # Check all campaigns
    python3 campaign_llm_manager.py --check          # Run one check cycle
    python3 campaign_llm_manager.py --watch          # Continuous monitoring
    python3 campaign_llm_manager.py --feed CAMPAIGN  # Feed specific campaign
    python3 campaign_llm_manager.py --start CAMPAIGN # Start campaign
    python3 campaign_llm_manager.py --stop CAMPAIGN  # Stop campaign

Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/LLM/AI')

import os
import json
import csv
import time
import argparse
import logging
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

# ============================================================
# CONSTANTS - DO NOT MODIFY THESE PATHS
# ============================================================
CAMPAIGNS_ROOT = "/opt/ACTIVE/EMAIL/CAMPAIGNS"
CAMPAIGNS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS"
ORCHESTRATOR_SCRIPT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_24_7.py"
SCRAPER_DATA_ROOT = "/mnt/hdd/SCRAPER_DATA"
SKILLS_DIR = "/opt/ACTIVE/INFRA/SKILLS"
SHARED_DIR = "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED"
SCRAPER_TO_CAMPAIGNS = "/opt/ACTIVE/INFRA/SKILLS/scraper_to_campaigns.py"
PATH_FIXER = "/opt/ACTIVE/INFRA/SKILLS/path_fixer.py"
LOG_DIR = "/opt/ACTIVE/INFRA/LOGS/campaign_llm"
STATE_FILE = "/opt/ACTIVE/INFRA/SKILLS/data/campaign_llm_state.json"

# ANOFM Automation
ANOFM_AUTOFEED = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/run_anofm_autofeed.sh"
ANOFM_TARGETS = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/anofm_targets.py"
ANOFM_SEGMENTS = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/anofm_segments.py"
ANOFM_DATA_DIR = "/mnt/hdd/SCRAPER_DATA/csv/ANOFM"
ANOFM_MAX_AGE_HOURS = 24  # Run ANOFM if data older than this

# Dashboard API
DASHBOARD_URL = "http://localhost:8088"
DASHBOARD_API = f"{DASHBOARD_URL}/api"

# LLM Endpoints
LOCAL_LLM_URL = "http://localhost:1234/v1/chat/completions"
LOCAL_LLM_MODELS_URL = "http://localhost:1234/v1/models"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "llama-3.3-70b"

# Local LLM Models - use best model for each task (prioritize small/fast for Pi)
# Sorted by size: tiny < smol < code < gemma < general < reasoning
LOCAL_LLM_MODELS = {
    "tiny": "tinyllama-1.1b-chat",                # Ultra-fast (0.7 GB, ~1s)
    "smol": "smollm-1.7b-instruct",               # Fast classification (1.0 GB, ~1-2s)
    "spam": "spam-classifier-3b-v1",              # Spam detection (0.9 GB, ~3s)
    "code": "qwen2.5-coder-1.5b-instruct",        # Code fixes (1.0 GB, ~2s)
    "gemma": "gemma-2-2b-instruct",               # Smart classification (1.5 GB, ~2-3s)
    "default": "lfm2.5-1.2b-instruct",            # Benchmark winner (1.25 GB, ~1.2 tok/s)
    "fast": "lfm2.5-1.2b-instruct",               # Fastest with good quality
    "reasoning": "phi-3.5-mini-instruct",         # Complex reasoning (2.2 GB, ~4-5s)
    "code_large": "qwen2.5-coder-7b-instruct",    # Heavy code (4.4 GB, too slow)
    "embed": "text-embedding-nomic-embed-text-v1.5"  # Embeddings (0.1 GB)
}

# Thresholds
LOW_CONTACTS_THRESHOLD = 100
LLM_TIMEOUT_LOCAL = 20  # Increased for larger models
LLM_TIMEOUT_CLOUD = 30
CHECK_INTERVAL = 300  # 5 minutes

# EURES Universal Fallback - feeds any campaign when other sources fail
EURES_MASTER = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/master_contacts_50.csv"
EURES_FIELDS = {
    "email": "email_1",
    "company": "company_name",
    "phone": "phone_1",
    "city": "company_city",
    "country": "country"  # Not country_name which is often empty
}

# EURES country filters (which EURES countries to include by campaign type)
EURES_RICH_COUNTRIES = {
    "germany", "austria", "switzerland", "netherlands", "belgium",
    "luxembourg", "france", "ireland", "norway", "sweden", "finland",
    "denmark", "iceland", "uk", "united kingdom"
}

# Campaign type -> EURES occupation keywords (for filtering)
CAMPAIGN_KEYWORDS = {
    "FACTORY": ["factory", "production", "assembly", "machine", "operator", "manufacturing", "industrial"],
    "HORECA": ["hotel", "restaurant", "cook", "chef", "waiter", "kitchen", "hospitality", "catering"],
    "WAREHOUSE": ["warehouse", "logistics", "storage", "picker", "packer", "forklift", "inventory"],
    "CONSTRUCTION": ["construction", "builder", "carpenter", "electrician", "plumber", "welder", "mason"],
    "AGRI": ["agriculture", "farm", "harvest", "greenhouse", "livestock", "dairy"],
    "TRANSPORT": ["transport", "driver", "logistics", "trucking", "shipping", "delivery"],
    "CARE": ["care", "nurse", "healthcare", "elderly", "medical", "hospital"],
    "RETAIL": ["retail", "shop", "store", "sales", "cashier"],
}

# Scraper data locations to search for auto-mapping
SCRAPER_SEARCH_PATHS = [
    "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE",      # Country scrapers
    "/mnt/hdd/SCRAPER_DATA/csv",                # USB scraper data
    "/mnt/hdd/SCRAPER_DATA",                    # USB root
    "/opt/ACTIVE/OPENDATA/DATA",                # OpenData
]

# Common email field names (for auto-detection)
EMAIL_FIELD_NAMES = ['email', 'email_1', 'email1', 'contact_email', 'e-mail', 'mail']
COMPANY_FIELD_NAMES = ['company', 'company_name', 'name', 'employer', 'organization', 'firma']
PHONE_FIELD_NAMES = ['phone', 'phone_1', 'phone1', 'contact_phone', 'tel', 'telefon']
CITY_FIELD_NAMES = ['city', 'location', 'address', 'company_city', 'oras', 'localitate']
COUNTRY_FIELD_NAMES = ['country', 'country_name', 'tara']

# Import shared modules after path setup
from skills_common import to_ascii
from alerting import send_telegram, send_alert

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure log directory exists
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


# ============================================================
# ERROR FIX PATTERNS (TIER 1)
# ============================================================
ERROR_FIXES = {
    "No module named skills_common": {
        "type": "path_fix",
        "fix": f"sys.path.insert(0, '{SHARED_DIR}')",
        "description": "Add shared directory to Python path"
    },
    "No module named campaign_sender": {
        "type": "path_fix",
        "fix": f"sys.path.insert(0, '{SHARED_DIR}')",
        "description": "Add shared directory to Python path"
    },
    "No module named email_sender_rules": {
        "type": "path_fix",
        "fix": f"sys.path.insert(0, '{SHARED_DIR}')",
        "description": "Add shared directory to Python path"
    },
    "FileNotFoundError: contacts.csv": {
        "type": "action",
        "action": "run_csv_feed",
        "description": "Run CSV auto-feed for campaign"
    },
    "FileNotFoundError: No such file or directory: '/opt/venv/bin/python3'": {
        "type": "action",
        "action": "run_path_fixer",
        "description": "Fix broken Python symlinks"
    },
    "python3: not found": {
        "type": "action",
        "action": "run_path_fixer",
        "description": "Fix broken Python symlinks"
    },
    "No such file or directory": {
        "type": "action",
        "action": "run_path_fixer",
        "description": "Fix broken paths/symlinks"
    },
    "Connection refused": {
        "type": "info",
        "description": "Service not running - may need restart"
    },
    "Permission denied": {
        "type": "info",
        "description": "File permission issue - check ownership"
    },
    "SMTP error": {
        "type": "retry",
        "description": "SMTP temporary error - will retry"
    },
    "Rate limit": {
        "type": "wait",
        "wait_minutes": 30,
        "description": "Rate limited - wait before retry"
    },
}


class AutoMapper:
    """
    Automatically find scraper data and create mappings for campaigns.

    Uses pattern matching and LLM to:
    1. Search for CSV files matching campaign name
    2. Analyze CSV headers to detect email/company/phone fields
    3. Create and apply mapping to feed campaign
    """

    def __init__(self, llm_engine=None):
        self.llm = llm_engine
        self.mappings_file = Path(SCRAPER_TO_CAMPAIGNS)

    def find_scraper_data(self, campaign_name: str) -> List[Dict]:
        """
        Search for CSV files that might contain data for this campaign.
        Returns list of candidates with path, headers, row count.
        """
        candidates = []
        search_terms = self._get_search_terms(campaign_name)

        for search_path in SCRAPER_SEARCH_PATHS:
            path = Path(search_path)
            if not path.exists():
                continue

            # Search recursively for matching directories/files
            for term in search_terms:
                # Search for directories matching campaign name
                for match_dir in path.glob(f"**/*{term}*"):
                    if match_dir.is_dir():
                        # Look for CSV files in this directory
                        for csv_file in match_dir.glob("*.csv"):
                            candidate = self._analyze_csv(csv_file)
                            if candidate:
                                candidates.append(candidate)

                # Also search for CSV files directly
                for csv_file in path.glob(f"**/*{term}*.csv"):
                    candidate = self._analyze_csv(csv_file)
                    if candidate:
                        candidates.append(candidate)

        # Deduplicate and sort by row count (most data first)
        seen = set()
        unique = []
        for c in candidates:
            if c['path'] not in seen:
                seen.add(c['path'])
                unique.append(c)

        unique.sort(key=lambda x: x.get('rows', 0), reverse=True)
        return unique[:10]  # Top 10 candidates

    def _get_search_terms(self, campaign_name: str) -> List[str]:
        """Generate search terms from campaign name."""
        terms = [campaign_name.lower()]

        # Split by underscore and add parts
        parts = campaign_name.lower().split('_')
        terms.extend(parts)

        # Common variations
        variations = {
            'horeca': ['hotel', 'restaurant', 'accommodation', 'hospitality'],
            'factory': ['manufacturing', 'production', 'industrial'],
            'agri': ['agriculture', 'farm', 'agricultural'],
            'transport': ['logistics', 'shipping', 'trucking'],
            'warehouse': ['logistics', 'storage'],
            'care': ['healthcare', 'nursing', 'elderly'],
            'construction': ['building', 'construct'],
        }

        for part in parts:
            if part in variations:
                terms.extend(variations[part])

        return list(set(terms))

    def _analyze_csv(self, csv_path: Path) -> Optional[Dict]:
        """Analyze a CSV file to check if it has email data."""
        try:
            # Check file age (skip files older than 30 days)
            age_days = (datetime.now().timestamp() - csv_path.stat().st_mtime) / 86400
            if age_days > 30:
                return None

            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if not headers:
                    return None

                # Count rows (sample first 1000)
                rows = sum(1 for _ in reader)

            headers_lower = [h.lower().strip() for h in headers]

            # Check for email field
            email_field = None
            for field in EMAIL_FIELD_NAMES:
                if field in headers_lower:
                    email_field = headers[headers_lower.index(field)]
                    break

            if not email_field:
                return None  # No email field found

            # Find other fields
            company_field = self._find_field(headers, headers_lower, COMPANY_FIELD_NAMES)
            phone_field = self._find_field(headers, headers_lower, PHONE_FIELD_NAMES)
            city_field = self._find_field(headers, headers_lower, CITY_FIELD_NAMES)
            country_field = self._find_field(headers, headers_lower, COUNTRY_FIELD_NAMES)

            return {
                'path': str(csv_path),
                'directory': str(csv_path.parent),
                'filename': csv_path.name,
                'headers': headers,
                'rows': rows,
                'age_days': round(age_days, 1),
                'fields': {
                    'email': email_field,
                    'company': company_field,
                    'phone': phone_field,
                    'city': city_field,
                    'country': country_field
                }
            }
        except Exception as e:
            logger.debug(f"Error analyzing {csv_path}: {e}")
            return None

    def _find_field(self, headers: List[str], headers_lower: List[str], candidates: List[str]) -> Optional[str]:
        """Find a field from list of candidate names."""
        for field in candidates:
            if field in headers_lower:
                return headers[headers_lower.index(field)]
        return None

    def create_mapping(self, campaign_name: str, candidate: Dict) -> Dict:
        """Create a mapping configuration from a candidate CSV."""
        fields = candidate['fields']

        # Determine file pattern
        filename = candidate['filename']
        # Convert specific date to wildcard: malta_20260215.csv -> malta_*.csv
        import re
        pattern = re.sub(r'\d{8}', '*', filename)
        pattern = re.sub(r'\d{6}', '*', pattern)

        # Infer country from path or campaign name
        country = None
        path_lower = candidate['path'].lower()
        country_hints = {
            'malta': 'Malta', 'bulgaria': 'Bulgaria', 'poland': 'Poland',
            'norway': 'Norway', 'sweden': 'Sweden', 'denmark': 'Denmark',
            'finland': 'Finland', 'germany': 'Germany', 'romania': 'Romania',
            'uk': 'United Kingdom', 'spain': 'Spain', 'france': 'France',
            'italy': 'Italy', 'netherlands': 'Netherlands'
        }
        for hint, country_name in country_hints.items():
            if hint in path_lower or hint in campaign_name.lower():
                country = country_name
                break

        mapping = {
            'campaign': campaign_name,
            'scraper_path': candidate['directory'],
            'file_pattern': pattern,
            'source_fields': {
                'email': fields['email'],
                'company': fields['company'] or 'name',
                'phone': fields['phone'] or 'phone',
                'city': fields['city'] or 'address',
                'country': fields['country'] or 'country'
            },
            'contacts_file': 'contacts.csv',
            'country': country,
            'rows_available': candidate['rows']
        }

        return mapping

    def apply_mapping_and_feed(self, campaign_name: str, mapping: Dict) -> Dict:
        """Apply mapping by directly feeding contacts to campaign."""
        result = {
            'campaign': campaign_name,
            'success': False,
            'added': 0,
            'source': mapping['scraper_path']
        }

        try:
            # Import the feed logic
            sys.path.insert(0, SKILLS_DIR)
            from scraper_to_campaigns import ScraperToCampaigns, MAPPINGS, TARGET_HEADERS

            # Temporarily add our mapping
            temp_mapping = {
                'scraper_path': Path(mapping['scraper_path']),
                'file_pattern': mapping['file_pattern'],
                'source_fields': mapping['source_fields'],
                'contacts_file': mapping['contacts_file'],
                'country': mapping['country']
            }

            # Add to MAPPINGS temporarily
            MAPPINGS[campaign_name] = temp_mapping

            # Run the feed
            feeder = ScraperToCampaigns(dry_run=False)
            feed_result = feeder.feed_campaign(campaign_name)

            result['success'] = feed_result.get('added', 0) > 0 or 'error' not in feed_result
            result['added'] = feed_result.get('added', 0)
            result['total'] = feed_result.get('total', 0)

            # If successful, persist the mapping
            if result['added'] > 0:
                self._persist_mapping(campaign_name, temp_mapping)
                logger.info(f"Auto-mapped {campaign_name}: +{result['added']} contacts from {mapping['file_pattern']}")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Auto-mapping failed for {campaign_name}: {e}")

        return result

    def _persist_mapping(self, campaign_name: str, mapping: Dict):
        """Add mapping to scraper_to_campaigns.py for future use."""
        # Read current file
        content = self.mappings_file.read_text()

        # Check if mapping already exists
        if f'"{campaign_name}"' in content or f"'{campaign_name}'" in content:
            return  # Already exists

        # Find the end of MAPPINGS dict and insert before it
        # Look for the pattern: })\n}\n\n# Target format
        insert_marker = '}\n\n# Target format'

        if insert_marker not in content:
            logger.warning("Could not find insertion point in scraper_to_campaigns.py")
            return

        # Build the new mapping entry
        new_entry = f'''    "{campaign_name}": {{
        "scraper_path": Path("{mapping['scraper_path']}"),
        "file_pattern": "{mapping['file_pattern']}",
        "source_fields": {{
            "email": "{mapping['source_fields']['email']}",
            "company": "{mapping['source_fields']['company']}",
            "phone": "{mapping['source_fields']['phone']}",
            "city": "{mapping['source_fields']['city']}",
            "country": "{mapping['source_fields']['country']}"
        }},
        "contacts_file": "{mapping['contacts_file']}",
        "country": {f'"{mapping["country"]}"' if mapping['country'] else 'None'}
    }},
'''

        # Insert the new mapping
        new_content = content.replace(
            insert_marker,
            new_entry + insert_marker
        )

        self.mappings_file.write_text(new_content)
        logger.info(f"Persisted mapping for {campaign_name} to scraper_to_campaigns.py")

    def auto_map_campaign(self, campaign_name: str) -> Dict:
        """
        Full auto-mapping workflow:
        1. Find candidate data sources
        2. Pick best candidate
        3. Create mapping
        4. Feed campaign
        5. Persist mapping for future
        """
        result = {
            'campaign': campaign_name,
            'success': False,
            'candidates_found': 0,
            'mapping': None
        }

        # Step 1: Find candidates
        candidates = self.find_scraper_data(campaign_name)
        result['candidates_found'] = len(candidates)

        if not candidates:
            result['error'] = f"No scraper data found for {campaign_name}"
            logger.warning(result['error'])
            return result

        # Step 2: Pick best candidate (most rows, newest)
        best = candidates[0]
        result['best_candidate'] = {
            'path': best['path'],
            'rows': best['rows'],
            'age_days': best['age_days']
        }

        # Step 3: Create mapping
        mapping = self.create_mapping(campaign_name, best)
        result['mapping'] = mapping

        # Step 4: Apply and feed
        feed_result = self.apply_mapping_and_feed(campaign_name, mapping)
        result['success'] = feed_result.get('success', False)
        result['added'] = feed_result.get('added', 0)

        if result['success']:
            logger.info(f"Auto-mapped {campaign_name}: found {len(candidates)} candidates, added {result['added']} contacts")
        else:
            result['error'] = feed_result.get('error', 'Feed failed')

        return result


class EURESFallback:
    """
    Universal EURES fallback - feeds any campaign from EURES master data.

    EURES has 3800+ contacts from rich EU countries. When campaign-specific
    scrapers have no data, EURES provides a universal backup source.
    """

    def __init__(self):
        self.master_file = Path(EURES_MASTER)
        self._cache = None
        self._cache_time = None

    def _load_eures_data(self) -> List[Dict]:
        """Load EURES master data with caching (1 hour)."""
        if self._cache and self._cache_time:
            age = (datetime.now() - self._cache_time).seconds
            if age < 3600:  # 1 hour cache
                return self._cache

        if not self.master_file.exists():
            logger.warning(f"EURES master not found: {self.master_file}")
            return []

        contacts = []
        try:
            with open(self.master_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get(EURES_FIELDS['email'], '').strip().lower()
                    if email and '@' in email:
                        contacts.append({
                            'email': email,
                            'company': row.get(EURES_FIELDS['company'], ''),
                            'phone': row.get(EURES_FIELDS['phone'], ''),
                            'city': row.get(EURES_FIELDS['city'], ''),
                            'country': row.get(EURES_FIELDS['country'], ''),
                            'job_title': row.get('job_title', ''),
                            'occupation': row.get('occupation', ''),
                            'sector': row.get('sector', '')
                        })

            self._cache = contacts
            self._cache_time = datetime.now()
            logger.info(f"Loaded {len(contacts)} EURES contacts")
        except Exception as e:
            logger.error(f"Error loading EURES data: {e}")

        return contacts

    def _detect_campaign_type(self, campaign_name: str) -> Optional[str]:
        """Detect campaign type from name."""
        name_upper = campaign_name.upper()
        for campaign_type in CAMPAIGN_KEYWORDS.keys():
            if campaign_type in name_upper:
                return campaign_type
        return None

    def _filter_contacts(self, contacts: List[Dict], campaign_name: str,
                         country_filter: str = None, limit: int = 500) -> List[Dict]:
        """
        Filter EURES contacts for a specific campaign.

        Filters by:
        1. Country (if specified or detected from campaign name)
        2. Keywords (based on campaign type)
        3. Rich countries only (unless specific country requested)
        """
        filtered = []
        campaign_type = self._detect_campaign_type(campaign_name)
        keywords = CAMPAIGN_KEYWORDS.get(campaign_type, [])

        # Country detection from campaign name
        name_lower = campaign_name.lower()
        detected_country = None
        country_hints = {
            'norway': 'norway', 'sweden': 'sweden', 'denmark': 'denmark',
            'finland': 'finland', 'germany': 'germany', 'poland': 'poland',
            'malta': 'malta', 'bulgaria': 'bulgaria', 'uk': 'united kingdom',
            'nordic': None,  # Multiple countries
            'eu': None,  # All EU
        }
        for hint, country in country_hints.items():
            if hint in name_lower:
                detected_country = country
                break

        use_country = country_filter or detected_country

        for contact in contacts:
            country = contact.get('country', '').lower()

            # Country filter
            if use_country:
                if use_country.lower() not in country:
                    continue
            else:
                # Default to rich countries
                if not any(rc in country for rc in EURES_RICH_COUNTRIES):
                    continue

            # Keyword filter (if we have keywords for this campaign type)
            if keywords:
                job_text = f"{contact.get('job_title', '')} {contact.get('occupation', '')} {contact.get('sector', '')}".lower()
                if not any(kw in job_text for kw in keywords):
                    continue

            filtered.append(contact)
            if len(filtered) >= limit:
                break

        return filtered

    def feed_campaign(self, campaign_name: str, limit: int = 200,
                      country: str = None) -> Dict:
        """
        Feed a campaign with EURES contacts.

        Returns: {success, added, source, filtered_count}
        """
        result = {
            'success': False,
            'added': 0,
            'campaign': campaign_name,
            'source': 'EURES',
            'eures_fallback': True
        }

        # Load EURES data
        all_contacts = self._load_eures_data()
        if not all_contacts:
            result['error'] = "EURES data not available"
            return result

        result['eures_total'] = len(all_contacts)

        # Filter for this campaign
        filtered = self._filter_contacts(all_contacts, campaign_name, country, limit)
        result['filtered_count'] = len(filtered)

        if not filtered:
            result['error'] = f"No EURES contacts match {campaign_name} criteria"
            return result

        # Feed to campaign
        campaign_dir = Path(CAMPAIGNS_DIR) / campaign_name
        if not campaign_dir.exists():
            result['error'] = f"Campaign directory not found: {campaign_dir}"
            return result

        # Determine contacts file location
        contacts_dir = campaign_dir / "contacts"
        if contacts_dir.exists():
            contacts_file = contacts_dir / "eures_contacts.csv"
        else:
            contacts_file = campaign_dir / "contacts.csv"

        # Load existing emails to avoid duplicates
        existing_emails = set()

        # Check all CSV files in campaign for existing emails
        for csv_path in campaign_dir.glob("**/*.csv"):
            try:
                with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = row.get('email', '').strip().lower()
                        if email:
                            existing_emails.add(email)
            except Exception:
                pass

        # Check state.json for sent emails
        state_file = campaign_dir / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                sent = state.get('sent', [])
                if isinstance(sent, list):
                    existing_emails.update(e.lower() for e in sent if e)
                elif isinstance(sent, dict):
                    existing_emails.update(e.lower() for e in sent.keys() if e)
            except Exception:
                pass

        # Filter out duplicates
        new_contacts = [c for c in filtered if c['email'].lower() not in existing_emails]
        result['duplicates_skipped'] = len(filtered) - len(new_contacts)

        if not new_contacts:
            result['error'] = "All EURES contacts already in campaign"
            return result

        # Write new contacts
        try:
            # Check if file exists to determine if we need header
            file_exists = contacts_file.exists()

            contacts_file.parent.mkdir(parents=True, exist_ok=True)

            with open(contacts_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['email', 'company', 'country', 'city', 'phone'])
                if not file_exists:
                    writer.writeheader()

                for contact in new_contacts:
                    writer.writerow({
                        'email': to_ascii(contact['email']),
                        'company': to_ascii(contact.get('company', '')),
                        'country': to_ascii(contact.get('country', '')),
                        'city': to_ascii(contact.get('city', '')),
                        'phone': to_ascii(contact.get('phone', ''))
                    })

            result['success'] = True
            result['added'] = len(new_contacts)
            logger.info(f"EURES fallback: fed {campaign_name} with {len(new_contacts)} contacts")

        except Exception as e:
            result['error'] = f"Error writing contacts: {e}"
            logger.error(result['error'])

        return result


class LocalLLMTasks:
    """
    Tasks that run on local llama-3.2-3b to save tokens.

    Fast, free inference for routine tasks using the best model for each task:
    - phi-3.5-mini: Quick tasks (subject optimization, classification)
    - spam-classifier-3b: Spam detection (specialized)
    - qwen2.5-coder-7b: Code fixes, error analysis
    - llama-3.2-3b: General fallback
    """

    def __init__(self):
        self.url = LOCAL_LLM_URL
        self.available_models = self._get_available_models()
        self.available = len(self.available_models) > 0

    def _get_available_models(self) -> List[str]:
        """Get list of available models from LM Studio."""
        try:
            r = requests.get(LOCAL_LLM_MODELS_URL, timeout=2)
            if r.status_code == 200:
                data = r.json()
                return [m['id'] for m in data.get('data', [])]
        except:
            pass
        return []

    def _select_model(self, task: str) -> str:
        """Select best available model for task (prefer small/fast on Pi)."""
        # Task -> preferred model mapping (smallest/fastest first for Pi)
        preferences = {
            'tiny': ['spam-classifier-3b-v1', 'lfm2.5-1.2b-instruct'],
            'fast': ['spam-classifier-3b-v1', 'lfm2.5-1.2b-instruct'],
            'spam': ['spam-classifier-3b-v1', 'lfm2.5-1.2b-instruct', 'llama-3.2-3b-instruct'],
            'code': ['qwen2.5-coder-1.5b-instruct', 'lfm2.5-1.2b-instruct'],
            'classify': ['spam-classifier-3b-v1', 'lfm2.5-1.2b-instruct'],
            'reasoning': ['granite-4.0-h-micro', 'lfm2.5-1.2b-instruct'],
            'default': ['lfm2.5-1.2b-instruct', 'granite-4.0-h-micro']
        }

        candidates = preferences.get(task, preferences['default'])
        for model in candidates:
            if model in self.available_models:
                return model

        # Fallback to first available (excluding embed model)
        for m in self.available_models:
            if 'embed' not in m.lower():
                return m
        return 'lfm2.5-1.2b-instruct'

    def _query(self, prompt: str, model: str = None, max_tokens: int = 200,
               temperature: float = 0.3, task: str = 'default') -> Optional[str]:
        """Query local LLM with specific model."""
        if not self.available:
            return None

        # Select model based on task
        use_model = model or self._select_model(task)

        try:
            response = requests.post(
                self.url,
                json={
                    "model": use_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=LLM_TIMEOUT_LOCAL
            )

            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content'].strip()
                logger.debug(f"LLM [{use_model}]: {len(result)} chars")
                return result
        except requests.exceptions.Timeout:
            logger.debug(f"LLM [{use_model}] timeout after {LLM_TIMEOUT_LOCAL}s")
        except Exception as e:
            logger.debug(f"LLM [{use_model}] failed: {e}")

        return None

    def get_status(self) -> Dict:
        """Get detailed LLM status."""
        return {
            'available': self.available,
            'models': self.available_models,
            'recommended': {
                'spam': self._select_model('spam'),
                'fast': self._select_model('fast'),
                'code': self._select_model('code'),
                'default': self._select_model('default')
            }
        }

    def optimize_subject(self, subject: str, campaign_type: str = "recruitment") -> Optional[str]:
        """
        Optimize email subject line for better open rates.
        Uses: phi-3.5-mini (fast model)

        Input: "We are hiring workers for Norway"
        Output: "Norway Jobs: Immediate Positions Available"
        """
        # Simpler prompt for faster response
        prompt = f"Rewrite this email subject to be more compelling (max 60 chars, no emojis): {subject}"

        result = self._query(prompt, max_tokens=50, task='fast')
        if result:
            # Clean up the response
            result = result.strip('"\'').strip()
            # Take first line only
            result = result.split('\n')[0].strip()
            if len(result) > 10 and len(result) < 100:
                return result
        return None

    def score_spam(self, template: str) -> Dict:
        """
        Predict spam score for email template.
        Uses keyword-based detection with LLM fallback for edge cases.

        Focuses on SCAM indicators, not normal promotional language.
        Recruitment emails are expected to be promotional - that's NOT spam.

        Returns: {score: 0-100, triggers: [list]}
        """
        # Keyword-based scoring (fast, reliable)
        text_lower = template.lower()

        # Scam/fraud triggers (heavy weight) - things that indicate malicious intent
        scam_words = {
            'free money': 30, 'click here': 15, 'act now': 20, 'limited time': 15,
            'you have won': 35, 'winner': 25, 'prize': 20, 'lottery': 35,
            'nigerian': 40, 'inheritance': 30, 'western union': 35,
            'bitcoin': 15, 'crypto': 10, 'wire transfer': 20,
            'password': 25, 'verify your account': 25, 'suspended': 20,
            'unsubscribe below': 5, 'opt out': 5  # Normal, low score
        }

        # Aggressive formatting triggers
        aggressive_patterns = {
            '!!!': 15, '???': 10, 'FREE': 10, 'WIN': 15, 'URGENT': 15,
            '$$$': 20, '€€€': 20, '100%': 10, 'GUARANTEED': 15
        }

        score = 0
        triggers = []

        # Check scam words
        for word, weight in scam_words.items():
            if word in text_lower:
                score += weight
                triggers.append(word)

        # Check aggressive formatting
        for pattern, weight in aggressive_patterns.items():
            if pattern in template:
                score += weight
                triggers.append(pattern)

        # Cap at 100
        score = min(100, score)

        return {'score': score, 'triggers': triggers, 'model': 'keyword-based'}

    def score_lead(self, company: str, country: str, email_domain: str) -> Dict:
        """
        Score a lead 1-5 based on quality signals.
        Uses: phi-3.5-mini (fast model)

        Returns: {score: 1-5, reason: str}
        """
        prompt = f"Rate 1-5 for B2B outreach. 5=valuable company. Format: SCORE: N REASON: text\nCompany: {company}, Country: {country}, Domain: {email_domain}"

        result = self._query(prompt, max_tokens=40, task='fast')
        parsed = {'score': 3, 'reason': 'Unknown', 'model': self._select_model('fast')}

        if result:
            if 'SCORE:' in result.upper():
                try:
                    for c in result.split(':')[1]:
                        if c.isdigit():
                            parsed['score'] = min(5, max(1, int(c)))
                            break
                except:
                    pass
            if 'REASON:' in result.upper():
                parsed['reason'] = result.upper().split('REASON:')[1].strip()[:100]

        return parsed

    def classify_response(self, email_body: str) -> str:
        """
        Classify email reply intent.
        Uses: llama-3.2-3b (best accuracy)

        Returns: interested | not_interested | unsubscribe | ooo | bounce | spam_complaint | unknown
        """
        # More explicit prompt with examples
        prompt = f"""Classify this email into exactly ONE category:

- not_interested = decline, rejection, "no thank you", "not interested"
- interested = wants info, asking questions, positive response
- unsubscribe = wants to stop emails, "remove me", "unsubscribe"
- ooo = out of office, vacation, auto-reply about absence
- bounce = delivery failed, "user unknown", "mailbox full"
- spam_complaint = angry, threatening, "stop spamming", "report you"
- unknown = unclear

Email: "{email_body[:300]}"

Answer with ONE word only:"""

        result = self._query(prompt, max_tokens=10, temperature=0.0, task='default')

        # Order matters! Check longer/specific categories FIRST
        valid = ['not_interested', 'spam_complaint', 'unsubscribe', 'interested', 'ooo', 'bounce', 'unknown']
        if result:
            result_lower = result.lower().strip().replace('_', '').replace('-', '').replace(' ', '')

            # Check for exact matches first
            for cat in valid:
                cat_normalized = cat.replace('_', '')
                if result_lower == cat_normalized or result_lower.startswith(cat_normalized):
                    return cat

            # Check for partial matches (longer categories first)
            for cat in valid:
                cat_normalized = cat.replace('_', '')
                if cat_normalized in result_lower:
                    return cat

            # Check for common alternatives
            if any(w in result_lower for w in ['decline', 'reject', 'nothanks', 'no']):
                return 'not_interested'
            if any(w in result_lower for w in ['yes', 'positive', 'info', 'more']):
                return 'interested'
            if 'office' in result_lower or 'away' in result_lower or 'vacation' in result_lower:
                return 'ooo'
            if 'spam' in result_lower or 'angry' in result_lower or 'stop' in result_lower:
                return 'spam_complaint'

        return 'unknown'

    def parse_bounce(self, bounce_message: str) -> Dict:
        """
        Parse bounce message to extract type and action.
        Uses: phi-3.5-mini (fast parsing)

        Returns: {type: hard|soft, reason: str, action: remove|retry|ignore}
        """
        prompt = f"Parse bounce. Format: TYPE: hard|soft, REASON: text, ACTION: remove|retry|ignore\n\nBounce: {bounce_message[:250]}"

        result = self._query(prompt, max_tokens=40, task='fast')
        parsed = {'type': 'soft', 'reason': 'Unknown', 'action': 'ignore', 'model': self._select_model('fast')}

        if result:
            result_upper = result.upper()
            for line in result.split('\n'):
                line_upper = line.upper()
                if 'TYPE:' in line_upper:
                    if 'hard' in line.lower():
                        parsed['type'] = 'hard'
                    elif 'soft' in line.lower():
                        parsed['type'] = 'soft'
                elif 'REASON:' in line_upper:
                    parsed['reason'] = line.split(':')[1].strip()[:50]
                elif 'ACTION:' in line_upper:
                    for a in ['remove', 'retry', 'ignore']:
                        if a in line.lower():
                            parsed['action'] = a
                            break

        return parsed

    def analyze_error(self, error_text: str) -> Dict:
        """
        Analyze script error and suggest fix.
        Uses: qwen2.5-coder-7b (code model)

        Returns: {fixable: bool, fix: str, explanation: str}
        """
        prompt = f"Analyze this Python error and suggest a one-line fix.\nFIXABLE: yes|no\nFIX: code\nEXPLAIN: text\n\nError:\n{error_text[:500]}"

        result = self._query(prompt, max_tokens=100, task='code')
        parsed = {'fixable': False, 'fix': None, 'explanation': 'Unknown', 'model': self._select_model('code')}

        if result:
            for line in result.split('\n'):
                line_upper = line.upper()
                if 'FIXABLE:' in line_upper:
                    parsed['fixable'] = 'yes' in line.lower()
                elif 'FIX:' in line_upper:
                    parsed['fix'] = line.split(':', 1)[1].strip()
                elif 'EXPLAIN:' in line_upper:
                    parsed['explanation'] = line.split(':', 1)[1].strip()[:100]

        return parsed

    def generate_daily_summary(self, metrics: Dict) -> str:
        """
        Generate natural language summary of campaign metrics.

        Input: {campaign: {sent: N, opens: N, clicks: N, bounces: N}}
        Output: Human-readable summary with recommendations
        """
        metrics_text = json.dumps(metrics, indent=2)

        prompt = f"""Summarize these email campaign metrics. Be concise.
Highlight issues. Suggest 1-2 improvements.

Metrics:
{metrics_text}

Summary (2-3 sentences):"""

        result = self._query(prompt, max_tokens=150)
        return result or "Metrics summary unavailable."


class CampaignMonitor:
    """Monitor all campaigns for status, errors, and low contacts."""

    def __init__(self):
        self.campaigns_dir = Path(CAMPAIGNS_DIR)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load persistent state."""
        state_path = Path(STATE_FILE)
        if state_path.exists():
            try:
                return json.loads(state_path.read_text())
            except Exception as e:
                logger.warning(f"Could not load state: {e}")
        return {
            "last_check": None,
            "fixes_applied": [],
            "alerts_sent": [],
            "campaigns_fed": {}
        }

    def _save_state(self):
        """Save persistent state."""
        self.state["last_check"] = datetime.now().isoformat()
        state_path = Path(STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.state, indent=2))

    def get_campaign_status(self, campaign_name: str) -> Optional[Dict]:
        """Get status for a single campaign."""
        campaign_dir = self.campaigns_dir / campaign_name
        if not campaign_dir.is_dir():
            return None

        state_file = campaign_dir / "state.json"
        if not state_file.exists():
            return None

        try:
            with open(state_file) as f:
                state = json.load(f)
        except Exception as e:
            return {"name": campaign_name, "error": str(e)}

        # Count contacts - check both contacts/ subdirectory and root-level CSVs
        total_contacts = 0

        # Check contacts/ subdirectory (standard structure)
        contacts_dir = campaign_dir / "contacts"
        if contacts_dir.exists():
            for csv_file in contacts_dir.glob("*.csv"):
                try:
                    with open(csv_file) as f:
                        total_contacts = max(total_contacts, sum(1 for _ in f) - 1)
                except Exception:
                    pass

        # Also check root-level contacts.csv (legacy structure)
        root_csv = campaign_dir / "contacts.csv"
        if root_csv.exists():
            try:
                with open(root_csv) as f:
                    total_contacts = max(total_contacts, sum(1 for _ in f) - 1)
            except Exception:
                pass

        sent = len(state.get("sent", []))
        failed = len(state.get("failed", []))
        remaining = total_contacts - sent
        daily_sent = state.get("daily_sent", 0)

        # Check running status
        is_running = False
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"send_{campaign_name.lower()}"],
                capture_output=True, text=True
            )
            is_running = bool(result.stdout.strip())
        except Exception:
            pass

        # Check pause lock
        is_paused = (campaign_dir / ".pause.lock").exists()

        return {
            "name": campaign_name,
            "total": total_contacts,
            "sent": sent,
            "failed": failed,
            "remaining": remaining,
            "daily_sent": daily_sent,
            "is_running": is_running,
            "is_paused": is_paused,
            "low_contacts": remaining < LOW_CONTACTS_THRESHOLD,
            "last_send": state.get("last_send", "Never")
        }

    def get_all_campaigns(self) -> List[Dict]:
        """Get status for all campaigns."""
        campaigns = []
        for d in self.campaigns_dir.iterdir():
            if not d.is_dir():
                continue
            if d.name.startswith('.') or d.name in ['dashboard', 'TEMPLATES', '__pycache__', 'ARCHIVE', 'SCRIPTS', 'DATA']:
                continue

            status = self.get_campaign_status(d.name)
            if status:
                campaigns.append(status)

        # Sort by remaining contacts (lowest first)
        campaigns.sort(key=lambda x: x.get("remaining", 0))
        return campaigns

    def get_low_contact_campaigns(self) -> List[Dict]:
        """Get campaigns with low contact count."""
        return [c for c in self.get_all_campaigns() if c.get("low_contacts", False)]

    def check_recent_errors(self, campaign_name: str) -> List[str]:
        """Check for recent errors in campaign logs."""
        errors = []
        campaign_dir = self.campaigns_dir / campaign_name
        log_dir = campaign_dir / "logs"

        if not log_dir.exists():
            return errors

        # Check last 24 hours of logs
        cutoff = datetime.now() - timedelta(hours=24)

        for log_file in log_dir.glob("*.log"):
            try:
                if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                    continue

                content = log_file.read_text()
                for line in content.split('\n')[-100:]:  # Last 100 lines
                    lower_line = line.lower()
                    if any(kw in lower_line for kw in ['error', 'exception', 'traceback', 'failed']):
                        errors.append(line.strip())
            except Exception:
                pass

        return errors[-10:]  # Last 10 errors


class CSVAutoLoader:
    """Auto-load contacts into campaigns when running low."""

    def __init__(self, monitor: CampaignMonitor):
        self.monitor = monitor
        self.auto_mapper = AutoMapper()
        self.eures_fallback = EURESFallback()

    def feed_campaign(self, campaign_name: str, try_auto_map: bool = True,
                      try_eures: bool = True) -> Dict:
        """
        Feed a specific campaign with fresh contacts.

        3-step fallback:
        1. Standard mapping (scraper_to_campaigns.py)
        2. Auto-discover and map new data sources
        3. EURES universal fallback (3800+ EU contacts)
        """
        logger.info(f"Feeding campaign: {campaign_name}")

        # Step 1: Try standard feed via scraper_to_campaigns.py
        result = self._standard_feed(campaign_name)

        # Step 2: If no contacts added and auto-map enabled, try auto-mapping
        if result.get('added', 0) == 0 and try_auto_map:
            logger.info(f"No mapping found for {campaign_name}, trying auto-map...")
            auto_result = self.auto_mapper.auto_map_campaign(campaign_name)

            if auto_result.get('success') and auto_result.get('added', 0) > 0:
                result = {
                    "success": True,
                    "campaign": campaign_name,
                    "added": auto_result['added'],
                    "auto_mapped": True,
                    "source": auto_result.get('mapping', {}).get('scraper_path', 'auto'),
                    "candidates_found": auto_result.get('candidates_found', 0)
                }
                logger.info(f"Auto-mapped {campaign_name}: +{result['added']} contacts")
            elif auto_result.get('candidates_found', 0) == 0:
                result['no_data_source'] = True
                result['message'] = f"No scraper data found for {campaign_name}"

        # Step 3: If still no contacts and EURES enabled, try EURES universal fallback
        if result.get('added', 0) == 0 and try_eures:
            logger.info(f"Trying EURES fallback for {campaign_name}...")
            eures_result = self.eures_fallback.feed_campaign(campaign_name)

            if eures_result.get('success') and eures_result.get('added', 0) > 0:
                result = {
                    "success": True,
                    "campaign": campaign_name,
                    "added": eures_result['added'],
                    "eures_fallback": True,
                    "source": "EURES",
                    "eures_total": eures_result.get('eures_total', 0),
                    "filtered_count": eures_result.get('filtered_count', 0),
                    "duplicates_skipped": eures_result.get('duplicates_skipped', 0)
                }
                logger.info(f"EURES fallback fed {campaign_name}: +{result['added']} contacts")
            else:
                result['eures_tried'] = True
                result['eures_error'] = eures_result.get('error', 'No matching EURES contacts')

        # Update state
        self.monitor.state["campaigns_fed"][campaign_name] = {
            "last_feed": datetime.now().isoformat(),
            "added": result.get('added', 0),
            "success": result.get('success', False),
            "auto_mapped": result.get('auto_mapped', False),
            "eures_fallback": result.get('eures_fallback', False)
        }
        self.monitor._save_state()

        return result

    def feed_from_eures(self, campaign_name: str, limit: int = 200,
                        country: str = None) -> Dict:
        """Feed a campaign directly from EURES (skip other sources)."""
        logger.info(f"Direct EURES feed for {campaign_name}")
        result = self.eures_fallback.feed_campaign(campaign_name, limit, country)

        # Update state
        self.monitor.state["campaigns_fed"][campaign_name] = {
            "last_feed": datetime.now().isoformat(),
            "added": result.get('added', 0),
            "success": result.get('success', False),
            "eures_fallback": True
        }
        self.monitor._save_state()

        return result

    def _standard_feed(self, campaign_name: str) -> Dict:
        """Run standard feed via scraper_to_campaigns.py."""
        try:
            result = subprocess.run(
                ["/usr/bin/python3", SCRAPER_TO_CAMPAIGNS, "--campaign", campaign_name],
                capture_output=True,
                text=True,
                timeout=300
            )

            success = result.returncode == 0
            output = result.stdout + result.stderr

            # Parse output for stats
            added = 0
            for line in output.split('\n'):
                if 'ADDED' in line:
                    try:
                        added = int(line.split('ADDED')[1].split()[0])
                    except:
                        pass

            return {
                "success": success,
                "campaign": campaign_name,
                "added": added,
                "output": output[-500:] if output else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "campaign": campaign_name, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "campaign": campaign_name, "error": str(e)}

    def feed_all_low(self) -> List[Dict]:
        """Feed all campaigns with low contacts."""
        results = []
        low_campaigns = self.monitor.get_low_contact_campaigns()

        for campaign in low_campaigns:
            result = self.feed_campaign(campaign["name"])
            results.append(result)

            if result["success"] and result.get("added", 0) > 0:
                logger.info(f"Fed {campaign['name']}: +{result['added']} contacts")

        return results


class LLMDecisionEngine:
    """4-tier LLM escalation for error analysis and fixes."""

    def __init__(self):
        self.local_available = self._check_local_llm()
        self.cerebras_key = self._get_cerebras_key()

    def _check_local_llm(self) -> bool:
        """Check if local LM Studio is available."""
        try:
            r = requests.get("http://localhost:1234/v1/models", timeout=2)
            return r.status_code == 200
        except:
            return False

    def _get_cerebras_key(self) -> Optional[str]:
        """Get Cerebras API key from env file."""
        env_file = Path("/opt/ACTIVE/LLM/AI/.env")
        if env_file.exists():
            for line in env_file.read_text().split('\n'):
                if line.startswith('CEREBRAS_API_KEY='):
                    return line.split('=', 1)[1].strip()
        return os.getenv('CEREBRAS_API_KEY')

    def analyze_error(self, error_text: str) -> Dict:
        """
        Analyze error using 4-tier escalation:
        1. Pattern matching (instant)
        2. Local LLM (15s)
        3. Cerebras cloud (30s)
        4. Human via Telegram
        """
        result = {
            "tier": 0,
            "fix": None,
            "action": None,
            "description": "",
            "needs_human": False
        }

        # Tier 1: Pattern matching
        fix = self._tier1_pattern_match(error_text)
        if fix:
            result.update(fix)
            result["tier"] = 1
            return result

        # Tier 2: Local LLM
        if self.local_available:
            fix = self._tier2_local_llm(error_text)
            if fix:
                result.update(fix)
                result["tier"] = 2
                return result

        # Tier 3: Cerebras cloud
        if self.cerebras_key:
            fix = self._tier3_cerebras(error_text)
            if fix:
                result.update(fix)
                result["tier"] = 3
                return result

        # Tier 4: Human intervention needed
        result["tier"] = 4
        result["needs_human"] = True
        result["description"] = "Could not auto-fix. Human review required."
        return result

    def _tier1_pattern_match(self, error_text: str) -> Optional[Dict]:
        """Tier 1: Pattern matching against known errors."""
        for pattern, fix_info in ERROR_FIXES.items():
            if pattern.lower() in error_text.lower():
                return {
                    "fix": fix_info.get("fix"),
                    "action": fix_info.get("action"),
                    "description": fix_info.get("description", ""),
                    "type": fix_info.get("type", "info")
                }
        return None

    def _tier2_local_llm(self, error_text: str) -> Optional[Dict]:
        """Tier 2: Query local LLM for fix suggestion."""
        prompt = f"""Analyze this Python error and suggest a fix.
Error: {error_text[:500]}

Respond in JSON format:
{{"fix": "code or command to fix", "description": "brief explanation"}}

If you cannot determine a fix, respond: {{"fix": null, "description": "unable to determine"}}
"""
        try:
            response = requests.post(
                LOCAL_LLM_URL,
                json={
                    "model": LOCAL_LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=LLM_TIMEOUT_LOCAL
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                # Try to parse JSON from response
                try:
                    # Find JSON in response
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        fix_data = json.loads(json_match.group())
                        if fix_data.get("fix"):
                            return fix_data
                except:
                    pass
        except Exception as e:
            logger.debug(f"Local LLM error: {e}")

        return None

    def _tier3_cerebras(self, error_text: str) -> Optional[Dict]:
        """Tier 3: Query Cerebras cloud for fix suggestion."""
        if not self.cerebras_key:
            return None

        prompt = f"""You are an expert Python developer. Analyze this error and provide a fix.

Error: {error_text[:800]}

Respond ONLY with JSON in this exact format:
{{"fix": "the fix code or command", "description": "brief explanation of the fix"}}

If you cannot determine a fix, respond: {{"fix": null, "description": "unable to determine"}}
"""
        try:
            response = requests.post(
                CEREBRAS_URL,
                headers={
                    "Authorization": f"Bearer {self.cerebras_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=LLM_TIMEOUT_CLOUD
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                try:
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        fix_data = json.loads(json_match.group())
                        if fix_data.get("fix"):
                            return fix_data
                except:
                    pass
        except Exception as e:
            logger.debug(f"Cerebras error: {e}")

        return None


class AutoFixer:
    """Apply fixes to campaign scripts and configurations."""

    def __init__(self, llm_engine: LLMDecisionEngine, monitor: CampaignMonitor):
        self.llm = llm_engine
        self.monitor = monitor

    def fix_error(self, campaign_name: str, error_text: str) -> Dict:
        """Analyze and fix an error."""
        result = {
            "campaign": campaign_name,
            "error": error_text[:200],
            "fixed": False,
            "action_taken": None
        }

        analysis = self.llm.analyze_error(error_text)
        result["tier"] = analysis["tier"]
        result["description"] = analysis.get("description", "")

        # Handle different fix types
        action = analysis.get("action")

        if action == "run_csv_feed":
            loader = CSVAutoLoader(self.monitor)
            feed_result = loader.feed_campaign(campaign_name)
            result["fixed"] = feed_result.get("success", False)
            result["action_taken"] = f"Fed campaign: {feed_result}"

        elif action == "run_path_fixer":
            try:
                subprocess.run(
                    ["/usr/bin/python3", PATH_FIXER, "--fix"],
                    capture_output=True,
                    timeout=60
                )
                result["fixed"] = True
                result["action_taken"] = "Ran path_fixer.py --fix"
            except Exception as e:
                result["action_taken"] = f"path_fixer failed: {e}"

        elif analysis.get("needs_human"):
            # Send Telegram alert
            alert_msg = f"Campaign {campaign_name} needs human intervention:\n{error_text[:300]}"
            send_telegram(alert_msg)
            result["action_taken"] = "Sent Telegram alert"

        elif analysis.get("fix"):
            result["suggested_fix"] = analysis["fix"]
            result["action_taken"] = "Fix suggested but not auto-applied"

        # Log the fix attempt
        self._log_fix(campaign_name, error_text, analysis, result)

        return result

    def _log_fix(self, campaign: str, error: str, analysis: Dict, result: Dict):
        """Log fix attempts."""
        log_file = Path(LOG_DIR) / f"fixes_{datetime.now().strftime('%Y%m%d')}.log"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "campaign": campaign,
            "error": error[:200],
            "tier": analysis.get("tier"),
            "fixed": result.get("fixed"),
            "action": result.get("action_taken")
        }

        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")


class DashboardClient:
    """Client for interacting with campaign dashboard API."""

    def __init__(self, base_url: str = DASHBOARD_URL):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request."""
        url = f"{self.api_url}/{endpoint}"
        try:
            if method == "GET":
                r = requests.get(url, timeout=10)
            else:
                r = requests.post(url, json=data or {}, timeout=30)

            return r.json()
        except requests.exceptions.ConnectionError:
            return {"error": "Dashboard not available"}
        except Exception as e:
            return {"error": str(e)}

    def get_campaigns(self) -> List[Dict]:
        """Get all campaigns from dashboard."""
        result = self._request("GET", "campaigns")
        if isinstance(result, list):
            return result
        return []

    def start_campaign(self, name: str, limit: int = 50) -> Dict:
        """Start a campaign (requires SEND confirmation)."""
        return self._request("POST", f"campaign/{name}/start", {
            "confirm": "SEND",
            "limit": limit
        })

    def stop_campaign(self, name: str) -> Dict:
        """Stop a running campaign."""
        return self._request("POST", f"campaign/{name}/stop")

    def pause_campaign(self, name: str) -> Dict:
        """Pause a campaign."""
        return self._request("POST", f"campaign/{name}/pause")

    def resume_campaign(self, name: str) -> Dict:
        """Resume a paused campaign."""
        return self._request("POST", f"campaign/{name}/resume")

    def test_campaign(self, name: str) -> Dict:
        """Run campaign test (dry run)."""
        return self._request("POST", f"campaign/{name}/test")


class CampaignLLMManager:
    """Main manager class coordinating all components."""

    def __init__(self):
        self.monitor = CampaignMonitor()
        self.loader = CSVAutoLoader(self.monitor)
        self.llm = LLMDecisionEngine()
        self.fixer = AutoFixer(self.llm, self.monitor)
        self.dashboard = DashboardClient()

    def _check_fresh_scraper_data(self) -> List[Dict]:
        """Check for fresh scraper data (< 1 hour old) and auto-feed to campaigns."""
        results = []
        scraper_mappings = {
            "ANOFM": ("/mnt/hdd/SCRAPER_DATA/csv/ANOFM", "anofm_*.csv"),
            "IAJOB": ("/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/IAJOB/output", "jobs*.csv"),
        }

        # Track what we've already fed to avoid duplicates
        fed_key = "last_fed_files"
        if fed_key not in self.monitor.state:
            self.monitor.state[fed_key] = {}

        for campaign, (path, pattern) in scraper_mappings.items():
            try:
                import glob
                from pathlib import Path
                files = sorted(glob.glob(f"{path}/{pattern}"), key=lambda x: Path(x).stat().st_mtime, reverse=True)
                if not files:
                    continue

                latest = files[0]
                mtime = Path(latest).stat().st_mtime
                age_hours = (time.time() - mtime) / 3600

                # Only feed if < 1 hour old and not already fed
                last_fed = self.monitor.state[fed_key].get(campaign, {}).get("file")
                if age_hours < 1.0 and latest != last_fed:
                    logger.info(f"Fresh scraper data detected for {campaign}: {latest} ({age_hours:.1f}h old)")
                    feed_result = self.loader.feed_campaign(campaign)

                    # Track what we fed
                    self.monitor.state[fed_key][campaign] = {
                        "file": latest,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.monitor._save_state()

                    results.append({
                        "campaign": campaign,
                        "file": latest,
                        "age_hours": age_hours,
                        **feed_result
                    })
            except Exception as e:
                logger.debug(f"Error checking scraper data for {campaign}: {e}")

        return results

    def status(self) -> Dict:
        """Get overall system status."""
        campaigns = self.monitor.get_all_campaigns()
        low_campaigns = [c for c in campaigns if c.get("low_contacts")]
        running = [c for c in campaigns if c.get("is_running")]

        return {
            "timestamp": datetime.now().isoformat(),
            "total_campaigns": len(campaigns),
            "running": len(running),
            "low_contacts": len(low_campaigns),
            "local_llm": self.llm.local_available,
            "cerebras": bool(self.llm.cerebras_key),
            "campaigns": campaigns,
            "low_contact_campaigns": [c["name"] for c in low_campaigns],
            "running_campaigns": [c["name"] for c in running]
        }

    def _check_anofm_needs_scrape(self) -> bool:
        """Check if ANOFM data is stale and needs re-scraping."""
        try:
            import glob
            files = sorted(glob.glob(f"{ANOFM_DATA_DIR}/anofm_*.csv"),
                          key=lambda x: Path(x).stat().st_mtime, reverse=True)
            if not files:
                return True
            latest = Path(files[0])
            age_hours = (time.time() - latest.stat().st_mtime) / 3600
            return age_hours > ANOFM_MAX_AGE_HOURS
        except:
            return False

    def _run_anofm_pipeline(self) -> Dict:
        """Run full ANOFM pipeline: scrape, segment, find targets, feed."""
        logger.info("Running ANOFM pipeline...")
        try:
            result = subprocess.run(
                ["/bin/bash", ANOFM_AUTOFEED],
                capture_output=True, text=True, timeout=1200
            )
            success = result.returncode == 0
            logger.info(f"ANOFM pipeline {'completed' if success else 'failed'}")
            return {"success": success, "output": result.stdout[-500:] if result.stdout else ""}
        except Exception as e:
            logger.error(f"ANOFM pipeline error: {e}")
            return {"success": False, "error": str(e)}

    def check_cycle(self) -> Dict:
        """Run one check cycle: check status, feed low campaigns, fix errors."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "actions": []
        }

        # 0a. Check if ANOFM needs scraping (data older than 24h)
        if self._check_anofm_needs_scrape():
            logger.info("ANOFM data is stale, triggering pipeline...")
            anofm_result = self._run_anofm_pipeline()
            results["actions"].append({
                "type": "anofm_pipeline",
                "result": anofm_result
            })

        # 0b. Check for fresh scraper data and auto-feed
        fresh_feeds = self._check_fresh_scraper_data()
        for feed in fresh_feeds:
            results["actions"].append({
                "type": "auto_feed",
                "campaign": feed["campaign"],
                "result": feed
            })

        # 1. Check all campaigns
        campaigns = self.monitor.get_all_campaigns()

        # 2. Feed campaigns with low contacts
        low_campaigns = [c for c in campaigns if c.get("low_contacts")]
        for campaign in low_campaigns:
            feed_result = self.loader.feed_campaign(campaign["name"])
            results["actions"].append({
                "type": "feed",
                "campaign": campaign["name"],
                "result": feed_result
            })

        # 3. Check for errors in running campaigns
        running = [c for c in campaigns if c.get("is_running")]
        for campaign in running:
            errors = self.monitor.check_recent_errors(campaign["name"])
            for error in errors[-3:]:  # Last 3 errors
                fix_result = self.fixer.fix_error(campaign["name"], error)
                results["actions"].append({
                    "type": "fix",
                    "campaign": campaign["name"],
                    "result": fix_result
                })

        # 4. Save state
        self.monitor._save_state()

        return results

    def watch(self, interval: int = CHECK_INTERVAL):
        """Continuous monitoring mode."""
        logger.info(f"Starting watch mode with {interval}s interval")

        while True:
            try:
                results = self.check_cycle()

                # Log summary
                actions = results.get("actions", [])
                if actions:
                    logger.info(f"Check cycle completed: {len(actions)} actions")
                    for action in actions:
                        if action.get("type") == "feed" and action.get("result", {}).get("added", 0) > 0:
                            logger.info(f"  Fed {action['campaign']}: +{action['result']['added']}")
                        elif action.get("type") == "fix" and action.get("result", {}).get("fixed"):
                            logger.info(f"  Fixed {action['campaign']}: {action['result'].get('action_taken')}")

                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Watch mode stopped")
                break
            except Exception as e:
                logger.error(f"Error in watch cycle: {e}")
                time.sleep(60)  # Wait before retry

    def feed_campaign(self, name: str) -> Dict:
        """Feed a specific campaign."""
        return self.loader.feed_campaign(name)

    def start_campaign(self, name: str, limit: int = 50) -> Dict:
        """Start a campaign via dashboard."""
        return self.dashboard.start_campaign(name, limit)

    def stop_campaign(self, name: str) -> Dict:
        """Stop a campaign via dashboard."""
        return self.dashboard.stop_campaign(name)


def print_status(status: Dict):
    """Print status in readable format."""
    print("\n" + "=" * 60)
    print("CAMPAIGN LLM MANAGER STATUS")
    print("=" * 60)
    print(f"Time: {status['timestamp']}")
    print(f"Total campaigns: {status['total_campaigns']}")
    print(f"Running: {status['running']}")
    print(f"Low contacts (<{LOW_CONTACTS_THRESHOLD}): {status['low_contacts']}")
    print(f"Local LLM: {'Available' if status['local_llm'] else 'Unavailable'}")
    print(f"Cerebras: {'Available' if status['cerebras'] else 'Unavailable'}")

    if status['running_campaigns']:
        print(f"\nRunning: {', '.join(status['running_campaigns'])}")

    if status['low_contact_campaigns']:
        print(f"\nLow contacts: {', '.join(status['low_contact_campaigns'])}")

    print("\n" + "-" * 60)
    print(f"{'Campaign':<25} {'Remaining':>10} {'Sent':>8} {'Status':<15}")
    print("-" * 60)

    for c in status['campaigns'][:15]:  # Top 15
        status_str = "RUNNING" if c.get('is_running') else ("PAUSED" if c.get('is_paused') else "READY")
        if c.get('low_contacts'):
            status_str = "LOW!"
        print(f"{c['name']:<25} {c.get('remaining', 0):>10} {c.get('sent', 0):>8} {status_str:<15}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Campaign LLM Manager')
    parser.add_argument('--status', '-s', action='store_true', help='Show status')
    parser.add_argument('--check', '-c', action='store_true', help='Run one check cycle')
    parser.add_argument('--watch', '-w', action='store_true', help='Continuous watch mode')
    parser.add_argument('--interval', '-i', type=int, default=CHECK_INTERVAL, help='Watch interval (seconds)')
    parser.add_argument('--feed', '-f', type=str, help='Feed specific campaign')
    parser.add_argument('--auto-map', '-a', type=str, help='Auto-discover and map data for campaign')
    parser.add_argument('--find-data', type=str, help='Find potential data sources for campaign')
    parser.add_argument('--start', type=str, help='Start campaign')
    parser.add_argument('--stop', type=str, help='Stop campaign')
    parser.add_argument('--limit', '-l', type=int, default=50, help='Batch limit for start')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    # EURES fallback options
    parser.add_argument('--eures', type=str, help='Feed campaign directly from EURES')
    parser.add_argument('--eures-status', action='store_true', help='Show EURES data status')
    parser.add_argument('--country', type=str, help='Country filter for EURES feed')

    # Local LLM task options
    parser.add_argument('--optimize-subject', type=str, help='Optimize email subject line')
    parser.add_argument('--spam-score', type=str, help='Check spam score for template file')
    parser.add_argument('--classify-reply', type=str, help='Classify email reply text')
    parser.add_argument('--llm-status', action='store_true', help='Show local LLM status')

    args = parser.parse_args()

    manager = CampaignLLMManager()

    if args.status:
        status = manager.status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print_status(status)

    elif args.check:
        results = manager.check_cycle()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Check cycle completed: {len(results.get('actions', []))} actions")
            for action in results.get("actions", []):
                print(f"  - {action['type']}: {action['campaign']} -> {action.get('result', {}).get('action_taken', 'completed')}")

    elif args.watch:
        manager.watch(interval=args.interval)

    elif args.feed:
        result = manager.feed_campaign(args.feed)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                msg = f"Fed {args.feed}: +{result.get('added', 0)} contacts"
                if result.get('eures_fallback'):
                    msg += f" (EURES fallback)"
                elif result.get('auto_mapped'):
                    msg += f" (auto-mapped from {result.get('source', 'auto')})"
                print(msg)
            else:
                print(f"Feed failed: {result.get('error', result.get('message', 'Unknown error'))}")
                if result.get('eures_tried'):
                    print(f"  EURES also tried: {result.get('eures_error', 'No match')}")

    elif args.auto_map:
        auto_mapper = AutoMapper()
        result = auto_mapper.auto_map_campaign(args.auto_map)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get('success'):
                print(f"Auto-mapped {args.auto_map}:")
                print(f"  Source: {result.get('mapping', {}).get('scraper_path', 'unknown')}")
                print(f"  Pattern: {result.get('mapping', {}).get('file_pattern', 'unknown')}")
                print(f"  Added: {result.get('added', 0)} contacts")
            else:
                print(f"Auto-map failed: {result.get('error', 'Unknown error')}")
                if result.get('candidates_found', 0) == 0:
                    print("  No data sources found. Check scraper paths.")

    elif args.find_data:
        auto_mapper = AutoMapper()
        candidates = auto_mapper.find_scraper_data(args.find_data)
        if args.json:
            print(json.dumps(candidates, indent=2))
        else:
            print(f"Found {len(candidates)} potential data sources for {args.find_data}:")
            for i, c in enumerate(candidates[:5], 1):
                print(f"\n  {i}. {c['filename']}")
                print(f"     Path: {c['directory']}")
                print(f"     Rows: {c['rows']}, Age: {c['age_days']} days")
                print(f"     Email field: {c['fields']['email']}")
                if c['fields']['company']:
                    print(f"     Company field: {c['fields']['company']}")

    elif args.start:
        result = manager.start_campaign(args.start, args.limit)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                print(f"Started {args.start} with limit {args.limit}")
            else:
                print(f"Start failed: {result.get('error', 'Unknown error')}")

    elif args.stop:
        result = manager.stop_campaign(args.stop)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                print(f"Stopped {args.stop}")
            else:
                print(f"Stop failed: {result.get('error', 'Unknown error')}")

    elif args.eures:
        # Direct EURES feed
        eures = EURESFallback()
        result = eures.feed_campaign(args.eures, limit=args.limit, country=args.country)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get('success'):
                print(f"EURES -> {args.eures}: +{result.get('added', 0)} contacts")
                print(f"  Total EURES: {result.get('eures_total', 0)}")
                print(f"  Filtered: {result.get('filtered_count', 0)}")
                print(f"  Duplicates skipped: {result.get('duplicates_skipped', 0)}")
            else:
                print(f"EURES feed failed: {result.get('error', 'Unknown error')}")

    elif args.eures_status:
        # Show EURES data status
        eures = EURESFallback()
        contacts = eures._load_eures_data()
        print(f"EURES Master: {EURES_MASTER}")
        print(f"Total contacts: {len(contacts)}")

        # Count by country
        countries = {}
        for c in contacts:
            country = c.get('country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1

        print("\nBy country:")
        for country, count in sorted(countries.items(), key=lambda x: -x[1])[:10]:
            print(f"  {country}: {count}")

    elif args.optimize_subject:
        # Optimize subject line using local LLM
        llm = LocalLLMTasks()
        if not llm.available:
            print("Local LLM not available. Start LM Studio on port 1234.")
            sys.exit(1)

        result = llm.optimize_subject(args.optimize_subject)
        if result:
            print(f"Original: {args.optimize_subject}")
            print(f"Optimized: {result}")
        else:
            print("Could not optimize subject line")

    elif args.spam_score:
        # Check spam score for template
        llm = LocalLLMTasks()
        if not llm.available:
            print("Local LLM not available. Start LM Studio on port 1234.")
            sys.exit(1)

        # Read template from file or use as text
        if Path(args.spam_score).exists():
            template = Path(args.spam_score).read_text()
        else:
            template = args.spam_score

        result = llm.score_spam(template)
        print(f"Spam Score: {result['score']}/100")
        if result['triggers']:
            print(f"Triggers: {', '.join(result['triggers'])}")
        if result['suggestions']:
            print(f"Suggestions: {', '.join(result['suggestions'])}")

    elif args.classify_reply:
        # Classify email reply
        llm = LocalLLMTasks()
        if not llm.available:
            print("Local LLM not available. Start LM Studio on port 1234.")
            sys.exit(1)

        result = llm.classify_response(args.classify_reply)
        print(f"Classification: {result}")

    elif args.llm_status:
        # Show detailed local LLM status
        llm = LocalLLMTasks()
        status = llm.get_status()

        print(f"Local LLM URL: {LOCAL_LLM_URL}")
        print(f"Available: {'Yes' if status['available'] else 'No'}")

        if status['available']:
            print(f"\nLoaded models ({len(status['models'])}):")
            for model in status['models']:
                print(f"  - {model}")

            print(f"\nModel selection by task:")
            for task, model in status['recommended'].items():
                print(f"  {task}: {model}")

            print(f"\nTesting each model...")
            for model in status['models']:
                if 'embed' in model.lower():
                    print(f"  {model}: (embedding model, skip)")
                    continue
                try:
                    start = time.time()
                    test = llm._query("Say OK", model=model, max_tokens=5)
                    elapsed = time.time() - start
                    print(f"  {model}: {test or 'No response'} ({elapsed:.1f}s)")
                except Exception as e:
                    print(f"  {model}: Error - {e}")

    else:
        # Default: show status
        status = manager.status()
        print_status(status)


if __name__ == "__main__":
    main()

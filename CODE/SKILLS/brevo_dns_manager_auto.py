#!/usr/bin/env python3
"""
DNS Manager for Brevo Authentication using A2 cPanel API (Non-interactive)
Uses the existing cpanel_api.py class for DNS operations
"""

import sys
import os
sys.path.append('/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/A2HOSTING')

from cpanel_api import CpanelAPI
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BrevoDNSManager:
    def __init__(self):
        """Initialize with existing cPanel API"""
        self.api = CpanelAPI()
        
        # Brevo DNS records for authentication
        self.brevo_records = {
            'txt': [
                {
                    'name': '@',
                    'type': 'TXT',
                    'txtdata': 'brevo-code:60ac5a533838d25f5d1beff54f043951',
                    'ttl': 3600
                },
                {
                    'name': 'mail._domainkey',
                    'type': 'TXT', 
                    'txtdata': 'k=rsa;p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDeMVIzrCa3T14JsNY0IRv5/2V1/v2itlviLQBwXsa7shBD6TrBkswsFUToPyMRWC9tbR/5ey0nRBH0ZVxp+lsmTxid2Y2z+FApQ6ra2VsXfbJP3HE6wAO0YTVEJt1TmeczhEd2Jiz/fcabIISgXEdSpTYJhb0ct0VJRxcg4c8c7wIDAQAB',
                    'ttl': 3600
                },
                {
                    'name': '_dmarc',
                    'type': 'TXT',
                    'txtdata': 'v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com',
                    'ttl': 3600
                }
            ]
        }
    
    def list_dns_records(self, domain='seicarescu.com'):
        """List DNS records for domain using ZoneInfo API"""
        try:
            result = self.api._api_call("ZoneInfo", {'domain': domain})
            if result and result.get('status'):
                records = result.get('data', {}).get('record', [])
                logger.info(f"Found {len(records)} DNS records for {domain}")
                return records
            else:
                logger.error(f"Failed to list DNS records: {result}")
                return []
        except Exception as e:
            logger.error(f"Error listing DNS records: {e}")
            return []
    
    def add_dns_record(self, domain, record_data):
        """Add a DNS record using ZoneEdit API"""
        try:
            params = {
                'domain': domain,
                'name': record_data['name'],
                'type': record_data['type'],
                'txtdata': record_data['txtdata'],
                'ttl': record_data['ttl']
            }
            
            result = self.api._api_call("ZoneEdit/add_zone_record", params)
            if result and result.get('status'):
                logger.info(f"Successfully added {record_data['type']} record for {record_data['name']}")
                return True
            else:
                logger.error(f"Failed to add DNS record: {result}")
                return False
        except Exception as e:
            logger.error(f"Error adding DNS record: {e}")
            return False
    
    def delete_dns_record(self, domain, record_line):
        """Delete a DNS record by line number"""
        try:
            params = {
                'domain': domain,
                'line': record_line
            }
            
            result = self.api._api_call("ZoneEdit/delete_zone_record", params)
            if result and result.get('status'):
                logger.info(f"Successfully deleted DNS record line {record_line}")
                return True
            else:
                logger.error(f"Failed to delete DNS record: {result}")
                return False
        except Exception as e:
            logger.error(f"Error deleting DNS record: {e}")
            return False
    
    def delete_dmarc_records(self, domain='seicarescu.com'):
        """Delete existing DMARC records to fix multiple DMARC issue"""
        records = self.list_dns_records(domain)
        deleted_count = 0
        
        for record in records:
            if (record.get('type') == 'TXT' and 
                record.get('name', '').startswith('_dmarc')):
                
                line = record.get('line')
                logger.info(f"Deleting DMARC record: line {line}")
                
                if self.delete_dns_record(domain, line):
                    deleted_count += 1
                    time.sleep(1)  # Small delay between deletions
        
        logger.info(f"Deleted {deleted_count} DMARC records")
        return deleted_count > 0
    
    def add_brevo_records(self, domain='seicarescu.com'):
        """Add all Brevo authentication records"""
        logger.info("Adding Brevo DNS records...")
        
        # First delete existing DMARC records to avoid conflicts
        self.delete_dmarc_records(domain)
        
        success_count = 0
        
        # Add new records
        for record_data in self.brevo_records['txt']:
            logger.info(f"Adding TXT record: {record_data['name']}")
            
            if self.add_dns_record(domain, record_data):
                success_count += 1
                time.sleep(1)  # Small delay between additions
            else:
                logger.error(f"Failed to add TXT record for {record_data['name']}")
        
        logger.info(f"Added {success_count}/{len(self.brevo_records['txt'])} Brevo records")
        return success_count == len(self.brevo_records['txt'])
    
    def verify_records(self, domain='seicarescu.com'):
        """Verify that all Brevo records are correctly configured"""
        records = self.list_dns_records(domain)
        
        required_records = {
            '@': 'brevo-code:60ac5a533838d25f5d1beff54f043951',
            'mail._domainkey': 'k=rsa;p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDeMVIzrCa3T14JsNY0IRv5/2V1/v2itlviLQBwXsa7shBD6TrBkswsFUToPyMRWC9tbR/5ey0nRBH0ZVxp+lsmTxid2Y2z+FApQ6ra2VsXfbJP3HE6wAO0YTVEJt1TmeczhEd2Jiz/fcabIISgXEdSpTYJhb0ct0VJRxcg4c8c7wIDAQAB',
            '_dmarc': 'v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com'
        }
        
        found_records = {}
        
        for record in records:
            if record.get('type') == 'TXT':
                name = record.get('name', '').split('.')[0]
                txtdata = record.get('txtdata', '')
                
                if name in required_records and required_records[name] in txtdata:
                    found_records[name] = True
                    logger.info(f"✓ Found correct TXT record for {name}")
        
        missing = [name for name in required_records if name not in found_records]
        if missing:
            logger.error(f"Missing DNS records: {missing}")
            return False
        else:
            logger.info("✓ All Brevo DNS records found and correct!")
            return True

def main():
    """Main execution function"""
    manager = BrevoDNSManager()
    domain = 'seicarescu.com'
    
    print("=== Brevo DNS Authentication Full Setup ===")
    
    print("Step 1: Deleting existing DMARC records...")
    manager.delete_dmarc_records(domain)
    time.sleep(2)
    
    print("Step 2: Adding Brevo authentication records...")
    manager.add_brevo_records(domain)
    time.sleep(2)
    
    print("Step 3: Verifying records...")
    success = manager.verify_records(domain)
    
    if success:
        print("\n✅ DNS configuration complete!")
        print("Note: DNS changes may take up to 48 hours to propagate globally.")
        print("You can now return to Brevo to verify the domain authentication.")
        print("Brevo will need to verify the DNS records once they propagate.")
    else:
        print("\n❌ DNS setup incomplete. Please check the logs above.")

if __name__ == "__main__":
    main()
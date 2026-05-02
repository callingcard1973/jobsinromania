#!/usr/bin/env python3
"""
cPanel DNS Manager Skill
Manages DNS records in cPanel for domain authentication purposes
Specifically designed for Brevo email authentication
"""

import requests
import json
import logging
import argparse
import time
from typing import Dict, List, Optional

class cPanelDNSManager:
    """Manage DNS records in cPanel for domain authentication"""
    
    def __init__(self, cpanel_url=None, username=None, api_token=None):
        """
        Initialize cPanel DNS Manager
        
        Args:
            cpanel_url (str): cPanel URL (default from config)
            username (str): cPanel username (default from config)
            api_token (str): cPanel API token (default from config)
        """
        self.cpanel_url = cpanel_url or "https://nl1-cl8-ats1.a2hosting.com:2083"
        self.username = username or "loaiidil"
        self.api_token = api_token or "2SI3BTY27666S93PA02NOOIMD4VP4OBO"
        
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
        
        # Setup logging
        self.logger = logging.getLogger('cpanel_dns_manager')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def call_cpanel_api(self, function: str, params: Dict) -> Optional[Dict]:
        """
        Call cPanel API2 function
        
        Args:
            function (str): cPanel API2 function name
            params (Dict): Parameters for the API call
            
        Returns:
            Optional[Dict]: API response data or None on failure
        """
        url = f"{self.cpanel_url}/json-api/cpanel"
        
        # Add required API parameters
        params.update({
            'cpanel_jsonapi_user': self.username,
            'cpanel_jsonapi_apiversion': '2',
            'cpanel_jsonapi_module': 'ZoneEdit',
            'cpanel_jsonapi_func': function
        })
        
        # Setup authentication headers
        headers = {
            'Authorization': f'cpanel {self.username}:{self.api_token}'
        }
        
        try:
            # Make API call with SSL verification disabled for cPanel
            response = requests.get(url, params=params, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for cPanel errors
            if 'cpanelresult' in data and data['cpanelresult'].get('error'):
                self.logger.error(f"cPanel API error: {data['cpanelresult']['error']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API call failed: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse API response: {e}")
            return None
    
    def list_current_records(self, domain: str = 'seicarescu.com') -> List[Dict]:
        """
        List current DNS records for the domain
        
        Args:
            domain (str): Domain name to query
            
        Returns:
            List[Dict]: List of DNS records
        """
        params = {
            'domain': domain
        }
        
        result = self.call_cpanel_api('fetchzone', params)
        
        if result and 'cpanelresult' in result:
            if result['cpanelresult'].get('data'):
                records = result['cpanelresult']['data'][0].get('record', [])
                self.logger.info(f"Found {len(records)} DNS records for {domain}")
                return records
        
        return []
    
    def delete_dmarc_records(self, domain: str = 'seicarescu.com') -> bool:
        """
        Delete existing DMARC records (fix multiple DMARC issue)
        
        Args:
            domain (str): Domain name
            
        Returns:
            bool: True if successful, False otherwise
        """
        records = self.list_current_records(domain)
        deleted_count = 0
        
        for record in records:
            if (record.get('type') == 'TXT' and 
                record.get('name', '').startswith('_dmarc')):
                
                self.logger.info(f"Deleting DMARC record: {record.get('line')}")
                
                params = {
                    'domain': domain,
                    'line': record.get('line')
                }
                
                result = self.call_cpanel_api('delzonerecord', params)
                if result and result.get('cpanelresult', {}).get('data'):
                    deleted_count += 1
                    self.logger.info(f"Successfully deleted DMARC record line {record.get('line')}")
                else:
                    self.logger.error(f"Failed to delete DMARC record line {record.get('line')}")
        
        self.logger.info(f"Deleted {deleted_count} DMARC records")
        return deleted_count > 0
    
    def add_brevo_records(self, domain: str = 'seicarescu.com') -> bool:
        """
        Add Brevo authentication records
        
        Args:
            domain (str): Domain name
            
        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Adding Brevo DNS records...")
        
        # First delete existing DMARC records to avoid conflicts
        self.delete_dmarc_records(domain)
        
        success_count = 0
        
        # Add new records
        for record_data in self.brevo_records['txt']:
            self.logger.info(f"Adding TXT record: {record_data['name']}")
            
            params = {
                'domain': domain,
                'name': record_data['name'],
                'type': record_data['type'],
                'txtdata': record_data['txtdata'],
                'ttl': record_data['ttl']
            }
            
            result = self.call_cpanel_api('addzonerecord', params)
            
            if result and result.get('cpanelresult', {}).get('data'):
                success_count += 1
                self.logger.info(f"Successfully added TXT record for {record_data['name']}")
            else:
                self.logger.error(f"Failed to add TXT record for {record_data['name']}")
                if result:
                    self.logger.error(f"API response: {result}")
        
        self.logger.info(f"Added {success_count}/{len(self.brevo_records['txt'])} Brevo records")
        return success_count == len(self.brevo_records['txt'])
    
    def verify_records(self, domain: str = 'seicarescu.com') -> bool:
        """
        Verify DNS records are properly set
        
        Args:
            domain (str): Domain name
            
        Returns:
            bool: True if all records are correct, False otherwise
        """
        records = self.list_current_records(domain)
        
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
                    self.logger.info(f"✓ Found correct TXT record for {name}")
        
        missing = [name for name in required_records if name not in found_records]
        if missing:
            self.logger.error(f"Missing DNS records: {missing}")
            return False
        else:
            self.logger.info("✓ All Brevo DNS records found and correct!")
            return True

def main():
    """Main execution function with CLI interface"""
    parser = argparse.ArgumentParser(description='cPanel DNS Manager for Brevo Authentication')
    parser.add_argument('--list', action='store_true', help='List current DNS records')
    parser.add_argument('--delete-dmarc', action='store_true', help='Delete existing DMARC records')
    parser.add_argument('--add-brevo', action='store_true', help='Add Brevo authentication records')
    parser.add_argument('--verify', action='store_true', help='Verify DNS records')
    parser.add_argument('--full-setup', action='store_true', help='Full setup (delete + add + verify)')
    parser.add_argument('--domain', default='seicarescu.com', help='Domain name (default: seicarescu.com)')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = cPanelDNSManager()
    
    if args.list:
        print(f"\\n=== DNS Records for {args.domain} ===")
        records = manager.list_current_records(args.domain)
        if records:
            print(f"Found {len(records)} records:")
            for record in records:
                if record.get('type') == 'TXT':
                    name = record.get('name', 'Unknown')
                    data = record.get('txtdata', '')[:80] + '...' if len(record.get('txtdata', '')) > 80 else record.get('txtdata', '')
                    print(f"  {name} (TXT): {data}")
        else:
            print("No records found or error occurred.")
    
    elif args.delete_dmarc:
        print(f"\\n=== Deleting DMARC Records for {args.domain} ===")
        success = manager.delete_dmarc_records(args.domain)
        print(f"DMARC deletion: {'SUCCESS' if success else 'FAILED'}")
    
    elif args.add_brevo:
        print(f"\\n=== Adding Brevo Records for {args.domain} ===")
        success = manager.add_brevo_records(args.domain)
        print(f"Brevo record addition: {'SUCCESS' if success else 'FAILED'}")
    
    elif args.verify:
        print(f"\\n=== Verifying DNS Records for {args.domain} ===")
        success = manager.verify_records(args.domain)
        print(f"Record verification: {'SUCCESS' if success else 'FAILED'}")
    
    elif args.full_setup:
        print(f"\\n=== Full DNS Setup for {args.domain} ===")
        print("Step 1: Deleting existing DMARC records...")
        manager.delete_dmarc_records(args.domain)
        time.sleep(2)
        
        print("Step 2: Adding Brevo authentication records...")
        manager.add_brevo_records(args.domain)
        time.sleep(2)
        
        print("Step 3: Verifying records...")
        success = manager.verify_records(args.domain)
        print(f"\\nFull setup: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            print("\\n✅ DNS configuration complete!")
            print("Note: DNS changes may take up to 48 hours to propagate globally.")
            print("You can now return to Brevo to verify the domain authentication.")
    
    else:
        # Interactive mode
        print("=== cPanel DNS Manager for Brevo Authentication ===")
        print("1. List current records")
        print("2. Delete existing DMARC records") 
        print("3. Add Brevo authentication records")
        print("4. Verify records")
        print("5. Full setup (delete + add + verify)")
        
        try:
            choice = input("\\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                records = manager.list_current_records(args.domain)
                if records:
                    print(f"\\nCurrent DNS records for {args.domain}:")
                    for record in records:
                        if record.get('type') == 'TXT':
                            name = record.get('name', 'Unknown')
                            data = record.get('txtdata', '')[:80] + '...' if len(record.get('txtdata', '')) > 80 else record.get('txtdata', '')
                            print(f"  {name} (TXT): {data}")
            
            elif choice == '2':
                success = manager.delete_dmarc_records(args.domain)
                print(f"DMARC deletion: {'SUCCESS' if success else 'FAILED'}")
            
            elif choice == '3':
                success = manager.add_brevo_records(args.domain)
                print(f"Brevo record addition: {'SUCCESS' if success else 'FAILED'}")
            
            elif choice == '4':
                success = manager.verify_records(args.domain)
                print(f"Record verification: {'SUCCESS' if success else 'FAILED'}")
            
            elif choice == '5':
                print("Running full setup...")
                manager.delete_dmarc_records(args.domain)
                time.sleep(2)
                manager.add_brevo_records(args.domain)
                time.sleep(2)
                success = manager.verify_records(args.domain)
                print(f"\\nFull setup: {'SUCCESS' if success else 'FAILED'}")
                
                if success:
                    print("\\n✅ DNS configuration complete!")
                    print("Note: DNS changes may take up to 48 hours to propagate globally.")
            
            else:
                print("Invalid choice")
                
        except KeyboardInterrupt:
            print("\\nOperation cancelled.")
        except Exception as e:
            print(f"\\nError: {e}")

if __name__ == "__main__":
    main()
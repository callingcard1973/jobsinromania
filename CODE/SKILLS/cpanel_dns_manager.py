#!/usr/bin/env python3
"""
cPanel DNS Manager for Brevo Authentication
Manages DNS records for seicarescu.com to authenticate with Brevo
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

class cPanelDNSManager:
    def __init__(self):
        self.cpanel_url = "https://nl1-cl8-ats1.a2hosting.com:2083"
        self.username = "loaiidil"  # cPanel username
        self.api_token = "2SI3BTY27666S93PA02NOOIMD4VP4OBO"  # API token
        
        # DNS records for Brevo authentication
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
    
    def call_cpanel_api(self, function, params):
        """Call cPanel API2 function"""
        url = f"{self.cpanel_url}/json-api/cpanel"
        
        params.update({
            'cpanel_jsonapi_user': self.username,
            'cpanel_jsonapi_apiversion': '2',
            'cpanel_jsonapi_module': 'ZoneEdit',
            'cpanel_jsonapi_func': function
        })
        
        headers = {
            'Authorization': f'cpanel {self.username}:{self.api_token}'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"API call failed: {e}")
            return None
    
    def list_current_records(self, domain='seicarescu.com'):
        """List current DNS records for the domain"""
        params = {
            'domain': domain
        }
        
        result = self.call_cpanel_api('fetchzone', params)
        
        if result and 'cpanelresult' in result:
            if result['cpanelresult']['data']:
                records = result['cpanelresult']['data'][0]['record']
                logging.info(f"Found {len(records)} DNS records for {domain}")
                return records
        
        return []
    
    def delete_dmarc_records(self, domain='seicarescu.com'):
        """Delete existing DMARC records"""
        records = self.list_current_records(domain)
        
        for record in records:
            if (record.get('type') == 'TXT' and 
                record.get('name', '').startswith('_dmarc')):
                
                logging.info(f"Deleting DMARC record: {record['line']}")
                
                params = {
                    'domain': domain,
                    'line': record['line']
                }
                
                result = self.call_cpanel_api('delzonerecord', params)
                if result and result.get('cpanelresult', {}).get('data'):
                    logging.info(f"Successfully deleted DMARC record line {record['line']}")
                else:
                    logging.error(f"Failed to delete DMARC record line {record['line']}")
    
    def add_brevo_records(self, domain='seicarescu.com'):
        """Add Brevo authentication records"""
        logging.info("Adding Brevo DNS records...")
        
        # First delete existing DMARC records
        self.delete_dmarc_records(domain)
        
        # Add new records
        for record_data in self.brevo_records['txt']:
            logging.info(f"Adding TXT record: {record_data['name']}")
            
            params = {
                'domain': domain,
                'name': record_data['name'],
                'type': record_data['type'],
                'txtdata': record_data['txtdata'],
                'ttl': record_data['ttl']
            }
            
            result = self.call_cpanel_api('addzonerecord', params)
            
            if result and result.get('cpanelresult', {}).get('data'):
                logging.info(f"Successfully added TXT record for {record_data['name']}")
            else:
                logging.error(f"Failed to add TXT record for {record_data['name']}")
                if result:
                    logging.error(f"API response: {result}")
    
    def verify_records(self, domain='seicarescu.com'):
        """Verify DNS records are properly set"""
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
                    logging.info(f"✓ Found correct TXT record for {name}")
        
        missing = [name for name in required_records if name not in found_records]
        if missing:
            logging.error(f"Missing DNS records: {missing}")
            return False
        else:
            logging.info("✓ All Brevo DNS records found and correct!")
            return True

def main():
    """Main execution function"""
    manager = cPanelDNSManager()
    
    print("=== cPanel DNS Manager for Brevo Authentication ===")
    print("1. List current records")
    print("2. Delete existing DMARC records") 
    print("3. Add Brevo authentication records")
    print("4. Verify records")
    print("5. Full setup (delete + add + verify)")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == '1':
        records = manager.list_current_records()
        if records:
            print("\nCurrent DNS records:")
            for record in records:
                if record.get('type') == 'TXT':
                    print(f"{record.get('name')} (TXT): {record.get('txtdata', '')[:100]}...")
    
    elif choice == '2':
        manager.delete_dmarc_records()
    
    elif choice == '3':
        manager.add_brevo_records()
    
    elif choice == '4':
        manager.verify_records()
    
    elif choice == '5':
        print("Running full setup...")
        manager.delete_dmarc_records()
        time.sleep(2)
        manager.add_brevo_records()
        time.sleep(2)
        manager.verify_records()
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    import time
    main()
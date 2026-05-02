#!/usr/bin/env python3
"""
A2 Hosting DNS Manager
Manage DNS records for domains hosted on A2 Hosting via cPanel API.

Usage:
    python3 a2_dns_manager.py list <domain>
    python3 a2_dns_manager.py add <domain> <type> <name> <value> [ttl]
    python3 a2_dns_manager.py delete <domain> <line_number>
    python3 a2_dns_manager.py find <domain> <search_term>

Examples:
    python3 a2_dns_manager.py list warehouseworkers.eu
    python3 a2_dns_manager.py add warehouseworkers.eu TXT @ "brevo-code:abc123"
    python3 a2_dns_manager.py delete warehouseworkers.eu 38
    python3 a2_dns_manager.py find warehouseworkers.eu dmarc
"""

import os
import sys
import json
import requests
import urllib3
urllib3.disable_warnings()

# Load credentials from environment or .env file
def load_credentials():
    env_file = "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"
    creds = {}

    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.strip().partition("=")
                    creds[key] = val

    return {
        "user": creds.get("A2_CPANEL_USER", "loaiidil"),
        "server": creds.get("A2_CPANEL_SERVER", "nl1-cl8-ats1.a2hosting.com"),
        "token": creds.get("A2_CPANEL_API_TOKEN_DNS", os.environ.get("A2_DNS_TOKEN", ""))
    }

class A2DNSManager:
    def __init__(self):
        creds = load_credentials()
        self.user = creds["user"]
        self.server = creds["server"]
        self.token = creds["token"]
        self.base_url = f"https://{self.server}:2083/json-api/cpanel"
        self.headers = {"Authorization": f"cpanel {self.user}:{self.token}"}

    def _api_call(self, func, params):
        """Make cPanel API call"""
        params.update({
            "cpanel_jsonapi_module": "ZoneEdit",
            "cpanel_jsonapi_func": func,
            "cpanel_jsonapi_apiversion": "2"
        })
        resp = requests.get(self.base_url, headers=self.headers, params=params,
                           verify=False, timeout=30)
        return resp.json()

    def fetch_zone(self, domain):
        """Fetch all DNS records for a domain"""
        result = self._api_call("fetchzone", {"domain": domain})
        data = result.get("cpanelresult", {}).get("data", [{}])
        if data and isinstance(data[0], dict):
            return data[0].get("record", [])
        return []

    def list_records(self, domain, record_type=None):
        """List DNS records, optionally filtered by type"""
        records = self.fetch_zone(domain)
        if record_type:
            records = [r for r in records if r.get("type") == record_type]
        return records

    def find_records(self, domain, search_term):
        """Find records containing search term in name or value"""
        records = self.fetch_zone(domain)
        search = search_term.lower()
        matches = []
        for rec in records:
            name = str(rec.get("name", "")).lower()
            txtdata = str(rec.get("txtdata", "")).lower()
            record = str(rec.get("record", "")).lower()
            if search in name or search in txtdata or search in record:
                matches.append(rec)
        return matches

    def add_record(self, domain, record_type, name, value, ttl=14400):
        """Add a DNS record"""
        params = {
            "domain": domain,
            "type": record_type,
            "name": name,
            "ttl": str(ttl)
        }

        if record_type == "TXT":
            params["txtdata"] = value
        elif record_type == "A":
            params["address"] = value
        elif record_type == "CNAME":
            params["cname"] = value
        elif record_type == "MX":
            params["exchange"] = value
            params["preference"] = "10"
        else:
            params["record"] = value

        result = self._api_call("add_zone_record", params)
        return result

    def delete_record(self, domain, line_number):
        """Delete a DNS record by line number"""
        result = self._api_call("remove_zone_record", {
            "domain": domain,
            "line": str(line_number)
        })
        status = result.get("cpanelresult", {}).get("data", [{}])[0].get("result", {})
        return status.get("status") == 1

    def print_record(self, rec):
        """Pretty print a record"""
        rtype = rec.get("type", "?")
        line = rec.get("Line", rec.get("line", "?"))
        name = rec.get("name", "")

        if rtype == "TXT":
            value = rec.get("txtdata", "")[:60]
        elif rtype == "A":
            value = rec.get("address", rec.get("record", ""))
        elif rtype == "CNAME":
            value = rec.get("cname", rec.get("record", ""))
        elif rtype == "MX":
            value = f"{rec.get('preference', '')} {rec.get('exchange', '')}"
        else:
            value = str(rec.get("record", ""))[:60]

        print(f"  [{line:3}] {rtype:5} {name[:35]:35} {value}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    domain = sys.argv[2]

    mgr = A2DNSManager()

    if cmd == "list":
        record_type = sys.argv[3] if len(sys.argv) > 3 else None
        records = mgr.list_records(domain, record_type)
        print(f"DNS Records for {domain}:")
        for rec in records:
            if rec.get("type") not in [":RAW", "$TTL"]:
                mgr.print_record(rec)

    elif cmd == "find":
        if len(sys.argv) < 4:
            print("Usage: a2_dns_manager.py find <domain> <search_term>")
            sys.exit(1)
        search = sys.argv[3]
        matches = mgr.find_records(domain, search)
        print(f"Records matching '{search}':")
        for rec in matches:
            mgr.print_record(rec)

    elif cmd == "add":
        if len(sys.argv) < 6:
            print("Usage: a2_dns_manager.py add <domain> <type> <name> <value> [ttl]")
            sys.exit(1)
        rtype = sys.argv[3]
        name = sys.argv[4]
        value = sys.argv[5]
        ttl = int(sys.argv[6]) if len(sys.argv) > 6 else 14400

        result = mgr.add_record(domain, rtype, name, value, ttl)
        status = result.get("cpanelresult", {}).get("data", [{}])[0].get("result", {})
        if status.get("status") == 1:
            print(f"Added {rtype} record: {name} = {value}")
        else:
            print(f"Failed: {status.get('statusmsg', 'Unknown error')}")

    elif cmd == "delete":
        if len(sys.argv) < 4:
            print("Usage: a2_dns_manager.py delete <domain> <line_number>")
            sys.exit(1)
        line = sys.argv[3]
        if mgr.delete_record(domain, line):
            print(f"Deleted record at line {line}")
        else:
            print(f"Failed to delete record at line {line}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Verify SPF records are propagated and switch campaigns back to original domains
Run this script after DNS propagation (wait 30-60 minutes)
"""

import dns.resolver
import time
import subprocess

def check_spf_records():
    """Check if SPF records have propagated"""
    domains = {
        "mivromania.online": "mivromania.info",
        "bppltd.co.uk": "mivromania.info"
    }

    results = {}

    for domain, backup_domain in domains.items():
        print(f"\n=== Checking {domain} ===")
        spf_found = False
        brevo_found = False

        try:
            answers = dns.resolver.resolve(domain, "TXT")

            for record in answers:
                txt = str(record).strip('"')
                if "spf1" in txt.lower():
                    print(f"✅ SPF: {txt}")
                    spf_found = True
                elif "brevo-code" in txt.lower():
                    print(f"✅ Brevo: {txt}")
                    brevo_found = True

            results[domain] = {
                'spf': spf_found,
                'brevo': brevo_found,
                'ready': spf_found and brevo_found,
                'backup': backup_domain
            }

        except Exception as e:
            print(f"❌ Error checking {domain}: {e}")
            results[domain] = {'spf': False, 'brevo': False, 'ready': False, 'backup': backup_domain}

    return results

def main():
    print("=== SPF Record Verification & Campaign Domain Switch ===")
    print("Checking if SPF records have propagated...")

    results = check_spf_records()

    print("\n=== SUMMARY ===")
    all_ready = True
    for domain, status in results.items():
        if status['ready']:
            print(f"✅ {domain}: READY (SPF + Brevo configured)")
        else:
            print(f"❌ {domain}: NOT READY (SPF: {status['spf']}, Brevo: {status['brevo']})")
            all_ready = False

    if all_ready:
        print("\n🎉 ALL DOMAINS READY! Campaigns can switch back to original domains.")
        print("\nTo update campaigns manually:")
        print("  1. Stop current campaigns")
        print("  2. Update email configurations to original domains")
        print("  3. Restart campaigns")
    else:
        print(f"\n⏳ DNS propagation still in progress. Try again in 30-60 minutes.")
        print(f"   Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n💡 Remember: All campaigns are currently working via backup domain mivromania.info")

if __name__ == "__main__":
    main()

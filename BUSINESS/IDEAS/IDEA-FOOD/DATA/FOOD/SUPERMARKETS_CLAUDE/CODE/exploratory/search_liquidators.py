#!/usr/bin/env python3
"""Search raspibig for executors and liquidators by phone number.

Run ON raspibig: python3 /tmp/search_liquidators.py --phone 0757698650

Searches interjob_master for:
- Companies with type = executor/liquidator
- Contacts with matching phone
- Organization types related to insolvency
"""

import sys
import csv
import re
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse

# Database connection
DB_HOST = "localhost"
DB_NAME = "interjob_master"
DB_USER = "postgres"
DB_PORT = 5432

def normalize_phone(phone):
    """Normalize phone number to digits only."""
    if not phone:
        return ""
    return re.sub(r'\D', '', str(phone))

def search_liquidators(phone):
    """Search for executors and liquidators with this phone."""
    
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        print("Invalid phone number")
        return
    
    print(f"Searching for phone: {phone} (normalized: {normalized_phone})")
    print("-" * 80)
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            port=DB_PORT
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Search 1: Companies table - look for executor/liquidator types
        print("\n1. SEARCHING COMPANIES TABLE FOR EXECUTOR/LIQUIDATOR TYPES:")
        print("-" * 80)
        
        query1 = """
        SELECT DISTINCT
            company_id, 
            company_name, 
            company_type,
            cui,
            phone_1,
            phone_2,
            email_1,
            email_2,
            address,
            city,
            county,
            status,
            data_updated
        FROM companies
        WHERE (
            LOWER(company_type) LIKE '%executor%'
            OR LOWER(company_type) LIKE '%lichidator%'
            OR LOWER(company_type) LIKE '%insolvency%'
            OR LOWER(company_name) LIKE '%executor%'
            OR LOWER(company_name) LIKE '%lichidator%'
        )
        AND (
            REPLACE(COALESCE(phone_1, ''), ' ', '-') LIKE '%%' || %s || '%%'
            OR REPLACE(COALESCE(phone_2, ''), ' ', '-') LIKE '%%' || %s || '%%'
        )
        LIMIT 100;
        """
        
        cur.execute(query1, (normalized_phone, normalized_phone))
        results1 = cur.fetchall()
        
        if results1:
            for row in results1:
                print(f"  Company: {row['company_name']}")
                print(f"    CUI: {row['cui']}")
                print(f"    Type: {row['company_type']}")
                print(f"    Phone 1: {row['phone_1']}")
                print(f"    Phone 2: {row['phone_2']}")
                print(f"    Email 1: {row['email_1']}")
                print(f"    Email 2: {row['email_2']}")
                print(f"    City: {row['city']}, County: {row['county']}")
                print(f"    Status: {row['status']}")
                print(f"    Updated: {row['data_updated']}")
                print()
        else:
            print("  No companies found matching executor/liquidator + phone")
        
        # Search 2: Contacts table
        print("\n2. SEARCHING CONTACTS TABLE:")
        print("-" * 80)
        
        query2 = """
        SELECT DISTINCT
            contact_id,
            contact_name,
            contact_type,
            company_name,
            company_id,
            phone,
            email,
            role
        FROM contacts
        WHERE (
            LOWER(contact_type) LIKE '%executor%'
            OR LOWER(contact_type) LIKE '%lichidator%'
            OR LOWER(role) LIKE '%executor%'
            OR LOWER(role) LIKE '%lichidator%'
            OR LOWER(role) LIKE '%insolvency%'
        )
        AND REPLACE(COALESCE(phone, ''), ' ', '-') LIKE '%%' || %s || '%%'
        LIMIT 100;
        """
        
        cur.execute(query2, (normalized_phone,))
        results2 = cur.fetchall()
        
        if results2:
            for row in results2:
                print(f"  Contact: {row['contact_name']}")
                print(f"    Company: {row['company_name']} (ID: {row['company_id']})")
                print(f"    Type: {row['contact_type']}")
                print(f"    Role: {row['role']}")
                print(f"    Phone: {row['phone']}")
                print(f"    Email: {row['email']}")
                print()
        else:
            print("  No contacts found matching executor/liquidator + phone")
        
        # Search 3: General phone search in companies
        print("\n3. GENERAL PHONE SEARCH IN COMPANIES (ANY TYPE):")
        print("-" * 80)
        
        query3 = """
        SELECT
            company_id,
            company_name,
            company_type,
            cui,
            phone_1,
            phone_2,
            email_1,
            email_2,
            city,
            county
        FROM companies
        WHERE (
            REPLACE(COALESCE(phone_1, ''), ' ', '-') LIKE '%%' || %s || '%%'
            OR REPLACE(COALESCE(phone_2, ''), ' ', '-') LIKE '%%' || %s || '%%'
        )
        LIMIT 50;
        """
        
        cur.execute(query3, (normalized_phone, normalized_phone))
        results3 = cur.fetchall()
        
        if results3:
            for row in results3:
                print(f"  Company: {row['company_name']}")
                print(f"    Type: {row['company_type']}")
                print(f"    Phone 1: {row['phone_1']}, Phone 2: {row['phone_2']}")
                print(f"    City: {row['city']}, County: {row['county']}")
                print()
        else:
            print("  No companies found with this phone number")
        
        # Summary
        print("\n" + "=" * 80)
        print(f"SUMMARY: Found {len(results1)} executor/liquidators, {len(results2)} contacts, {len(results3)} general matches")
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        print("\nNote: This script must be run ON raspibig server with database access.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search raspibig for executors/liquidators")
    parser.add_argument("--phone", required=True, help="Phone number to search (0757698650)")
    
    args = parser.parse_args()
    search_liquidators(args.phone)

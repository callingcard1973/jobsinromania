#!/usr/bin/env python3
"""
Pipeline to enrich SEAP contractors with contact info.

Sources:
1. ANOFM - direct CUI match (done)
2. ONRC - get company website from registry
3. Google - search "company name CUI site:.ro"
4. Website - extract email from company website

Output: contractors_enriched.csv with email, phone, website
"""
import pandas as pd
import httpx
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES")

def search_google_for_website(company_name: str, cui: str) -> str:
    """Search Google for company website."""
    # Use DuckDuckGo HTML (no API key needed)
    query = f"{company_name} {cui} site:.ro"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        # Extract first .ro domain
        domains = re.findall(r'https?://([a-z0-9-]+\.ro)', r.text)
        if domains:
            return f"https://{domains[0]}"
    except:
        pass
    return ""

def extract_email_from_website(url: str) -> str:
    """Extract email from website."""
    if not url:
        return ""
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)
        # Filter out common false positives
        emails = [e for e in emails if not any(x in e.lower() for x in ['example', 'test', 'domain', 'email'])]
        if emails:
            return emails[0]
    except:
        pass
    return ""

def enrich_batch(contractors_df: pd.DataFrame, start: int, batch_size: int) -> list:
    """Enrich a batch of contractors."""
    results = []
    batch = contractors_df.iloc[start:start+batch_size]
    
    for _, row in batch.iterrows():
        company = row.get('OFERTANT_CASTIGATOR', '')
        cui = str(row.get('CUI', ''))
        
        # Skip if already has email
        if pd.notna(row.get('emails')) and row.get('emails'):
            results.append(row.to_dict())
            continue
        
        # Search for website
        website = search_google_for_website(company, cui)
        time.sleep(0.5)  # Rate limit
        
        # Extract email from website
        email = extract_email_from_website(website) if website else ""
        
        result = row.to_dict()
        result['website'] = website
        result['email_scraped'] = email
        results.append(result)
        
        if email:
            print(f"Found: {company} -> {email}")
    
    return results

def main():
    # Load contractors without contacts
    contractors = pd.read_csv(OUTPUT_DIR / "all_contractors_2025.csv")
    with_contacts = pd.read_csv(OUTPUT_DIR / "contractors_with_contacts.csv")
    
    # Find contractors without email
    has_email_cui = set(with_contacts['CUI'].dropna().astype(str))
    contractors['CUI'] = contractors['CUI_OFERTANT_CASTIGATOR'].astype(str).str.extract(r'(\d+)')
    
    without_email = contractors[~contractors['CUI'].isin(has_email_cui)]
    print(f"Contractors without email: {len(without_email)}")
    
    # Enrich top 1000 by contract value (prioritize)
    # For now just do first 100 as test
    results = enrich_batch(without_email, 0, 100)
    
    # Save
    enriched_df = pd.DataFrame(results)
    enriched_df.to_csv(OUTPUT_DIR / "contractors_enriched_test.csv", index=False)
    
    found = enriched_df[enriched_df['email_scraped'].notna() & (enriched_df['email_scraped'] != '')]
    print(f"Found emails: {len(found)}")

if __name__ == "__main__":
    main()

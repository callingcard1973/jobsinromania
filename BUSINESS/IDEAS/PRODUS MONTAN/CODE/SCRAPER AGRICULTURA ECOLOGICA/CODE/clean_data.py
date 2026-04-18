#!/usr/bin/env python3
"""
Data cleaning script for producer CSV
Removes duplicates, validates data, handles missing values
"""

import csv
import re
import os
from pathlib import Path
from collections import defaultdict

data_dir = r'd:\MEMORY\IDEAS\PRODUS MONTAN\CODE\SCRAPER AGRICULTURA ECOLOGICA\DATA'
input_file = os.path.join(data_dir, 'producers_enriched.csv')
output_file = os.path.join(data_dir, 'producers_clean.csv')

def is_valid_phone(phone: str) -> bool:
    """Check if phone is in valid normalized format"""
    if not phone or not isinstance(phone, str):
        return False
    # Should be in format: +40 XXX XXX XXX
    pattern = r'^\+40\s\d{3}\s\d{3}\s\d{3}(,\s\+40\s\d{3}\s\d{3}\s\d{3})?$'
    return bool(re.match(pattern, phone.strip()))

def is_valid_email(email: str) -> bool:
    """Check if email is valid"""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def split_and_clean_phones(phone_str: str) -> str:
    """Split combined phones and validate each one"""
    if not phone_str or not isinstance(phone_str, str):
        return ''
    
    # Split by comma
    phones = [p.strip() for p in phone_str.split(',')]
    
    # Validate each phone
    valid_phones = [p for p in phones if is_valid_phone(p)]
    
    # Return unique phones joined by comma
    return ', '.join(list(dict.fromkeys(valid_phones)))

def split_and_clean_emails(email_str: str) -> str:
    """Split combined emails and validate each one"""
    if not email_str or not isinstance(email_str, str):
        return ''
    
    # Split by comma
    emails = [e.strip() for e in email_str.split(',')]
    
    # Validate each email
    valid_emails = [e for e in emails if is_valid_email(e)]
    
    # Return unique emails joined by comma
    return ', '.join(list(dict.fromkeys(valid_emails)))

def clean_name(name: str) -> str:
    """Clean producer name"""
    if not name:
        return ''
    # Remove extra whitespace
    name = ' '.join(name.split())
    # Remove HTML entities if present
    name = re.sub(r'&#?\w+;', '', name)
    return name.strip()

def clean_text_field(text: str) -> str:
    """Clean generic text field"""
    if not text:
        return ''
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove HTML entities
    text = re.sub(r'&#?\w+;', '', text)
    return text.strip()

def is_duplicate(row1: dict, row2: dict) -> bool:
    """Check if two rows represent the same producer"""
    # Same name and county = duplicate
    name1 = row1.get('name', '').lower().strip()
    name2 = row2.get('name', '').lower().strip()
    county1 = row1.get('location_county', '').lower().strip()
    county2 = row2.get('location_county', '').lower().strip()
    
    if name1 and name2 and name1 == name2 and county1 == county2:
        return True
    
    # Same link = duplicate
    link1 = row1.get('link', '').strip()
    link2 = row2.get('link', '').strip()
    if link1 and link2 and link1 == link2:
        return True
    
    return False

def clean_data():
    """Clean and validate producer data"""
    print("Loading data...")
    rows = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Loaded {len(rows)} records")
    
    # Track statistics
    stats = {
        'total_input': len(rows),
        'removed_empty_name': 0,
        'removed_duplicate': 0,
        'removed_no_location': 0,
        'cleaned_phone': 0,
        'cleaned_email': 0,
        'cleaned_whitespace': 0,
    }
    
    # Step 1: Remove rows with empty names
    rows = [r for r in rows if r.get('name', '').strip()]
    stats['removed_empty_name'] = stats['total_input'] - len(rows)
    
    # Step 2: Remove rows with no location info (both city and county empty)
    rows_with_location = []
    for r in rows:
        if r.get('location_city', '').strip() or r.get('location_county', '').strip():
            rows_with_location.append(r)
        else:
            stats['removed_no_location'] += 1
    rows = rows_with_location
    
    # Step 3: Remove duplicates (keep first occurrence)
    seen = set()
    unique_rows = []
    for row in rows:
        # Create a unique key based on name + county + link
        key = (
            row.get('name', '').lower().strip(),
            row.get('location_county', '').lower().strip(),
            row.get('link', '').strip()
        )
        
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
        else:
            stats['removed_duplicate'] += 1
    
    rows = unique_rows
    
    # Step 4: Clean and validate existing rows
    cleaned_rows = []
    for row in rows:
        # Clean name
        row['name'] = clean_name(row.get('name', ''))
        
        # Clean location fields
        row['location_city'] = clean_text_field(row.get('location_city', ''))
        row['location_county'] = clean_text_field(row.get('location_county', ''))
        
        # Clean address
        row['full_address'] = clean_text_field(row.get('full_address', ''))
        
        # Validate phone - remove invalid phones
        phone = row.get('phone', '').strip()
        if phone:
            cleaned_phone = split_and_clean_phones(phone)
            if cleaned_phone != phone:
                stats['cleaned_phone'] += 1
            row['phone'] = cleaned_phone
        
        # Validate email - remove invalid emails
        email = row.get('email', '').strip()
        if email:
            cleaned_email = split_and_clean_emails(email)
            if cleaned_email != email:
                stats['cleaned_email'] += 1
            row['email'] = cleaned_email
        
        # Clean products and activities
        row['products'] = clean_text_field(row.get('products', ''))
        row['activities'] = clean_text_field(row.get('activities', ''))
        
        # Clean whitespace in all fields
        for key in row:
            if isinstance(row[key], str):
                row[key] = row[key].strip()
        
        stats['cleaned_whitespace'] += 1
        cleaned_rows.append(row)
    
    rows = cleaned_rows
    
    # Step 5: Save cleaned data
    print("\nSaving cleaned data...")
    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    # Print statistics
    print("\n=== CLEANING STATISTICS ===")
    print(f"Input records: {stats['total_input']}")
    print(f"Empty names removed: {stats['removed_empty_name']}")
    print(f"No location removed: {stats['removed_no_location']}")
    print(f"Duplicates removed: {stats['removed_duplicate']}")
    print(f"Invalid phones cleaned: {stats['cleaned_phone']}")
    print(f"Invalid emails cleaned: {stats['cleaned_email']}")
    print(f"Records cleaned: {stats['cleaned_whitespace']}")
    print(f"\nOutput records: {len(rows)}")
    print(f"Reduction: {stats['total_input'] - len(rows)} ({100*(stats['total_input']-len(rows))/stats['total_input']:.1f}%)")
    
    # Data quality metrics
    with_phone = sum(1 for r in rows if r.get('phone', '').strip())
    with_email = sum(1 for r in rows if r.get('email', '').strip())
    with_website = sum(1 for r in rows if r.get('website', '').strip())
    with_facebook = sum(1 for r in rows if r.get('facebook', '').strip())
    
    print(f"\n=== DATA QUALITY ===")
    print(f"With phone: {with_phone} ({100*with_phone/len(rows):.1f}%)")
    print(f"With email: {with_email} ({100*with_email/len(rows):.1f}%)")
    print(f"With website: {with_website} ({100*with_website/len(rows):.1f}%)")
    print(f"With Facebook: {with_facebook} ({100*with_facebook/len(rows):.1f}%)")
    
    print(f"\nCleaned data saved to: {output_file}")

if __name__ == "__main__":
    clean_data()

#!/usr/bin/env python3
"""
Trasabilitate CLI — Simple command-line interface for producers
Optimized for Raspberry Pi deployment
"""

import argparse
import requests
import json
from datetime import datetime
from pathlib import Path
import sys

# Default API base URL (can be overridden via environment variable)
API_URL = "http://localhost:5000/api"

def create_harvest(producer_id, product, quantity_kg, harvest_date=None):
    """Create new harvest: trasabilitate create --producer 1 --product "Tomato" --qty 500"""
    
    if harvest_date is None:
        harvest_date = datetime.now().strftime('%Y-%m-%d')
    
    payload = {
        "producer_id": int(producer_id),
        "product_name": product,
        "quantity_kg": float(quantity_kg),
        "harvest_date": harvest_date
    }
    
    try:
        res = requests.post(f"{API_URL}/harvest/create", json=payload, timeout=10)
        data = res.json()
        
        if res.status_code == 201:
            print(f"✓ Harvest created: {data['harvest_id']}")
            print(f"✓ QR code: {data['qr']}")
            print(f"\nShare this link: {data['qr']}")
            return True
        else:
            print(f"✗ Error: {data.get('error', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {e}")
        return False

def sell_harvest(harvest_id, buyer_type, buyer_name, quantity_kg, price_per_kg, location):
    """Record sale: trasabilitate sell --id 260308-TOMATO-500KG --buyer-type hypermarket --buyer "Kaufland" --qty 250 --price 1.50 --location "Kaufland warehouse""""
    
    payload = {
        "buyer_type": buyer_type,
        "buyer_name": buyer_name,
        "quantity_kg": float(quantity_kg),
        "delivery_date": datetime.now().strftime('%Y-%m-%d'),
        "delivery_location": location,
        "price_per_kg": float(price_per_kg)
    }
    
    try:
        res = requests.post(f"{API_URL}/harvest/{harvest_id}/sell", json=payload, timeout=10)
        data = res.json()
        
        if res.status_code == 201:
            print(f"✓ {data['message']}")
            return True
        else:
            print(f"✗ Error: {data.get('error', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {e}")
        return False

def trace_harvest(harvest_id):
    """Trace harvest: trasabilitate trace --id 260308-TOMATO-500KG"""
    
    try:
        res = requests.get(f"{API_URL}/harvest/{harvest_id}/trace", timeout=10)
        data = res.json()
        
        if res.status_code != 200:
            print(f"✗ Error: {data.get('error', 'Harvest not found')}")
            return False
        
        print(f"\n{'='*60}")
        print(f"HARVEST TRACE — {data['harvest']['harvest_id']}")
        print(f"{'='*60}")
        
        harvest = data['harvest']
        print(f"\nProduct: {harvest['product_name']}")
        print(f"Quantity: {harvest['quantity_kg']} kg")
        print(f"Harvested: {harvest['harvest_date']}")
        print(f"Producer: {harvest['name']}")
        print(f"Location: {harvest['location']}")
        
        if data['sales']:
            print(f"\n{'='*60}")
            print(f"SALES & DELIVERIES ({len(data['sales'])} records)")
            print(f"{'='*60}")
            
            for i, sale in enumerate(data['sales'], 1):
                print(f"\n{i}. {sale['buyer_type'].upper()}: {sale['buyer_name']}")
                print(f"   Quantity: {sale['quantity_kg']} kg @ €{sale['price_per_kg']}/kg")
                print(f"   Delivered: {sale['delivery_date']}")
                print(f"   Location: {sale['delivery_location']}")
        else:
            print(f"\n(No sales recorded yet)")
        
        print(f"\n{'='*60}\n")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {e}")
        return False

def register_producer(name, producer_type, location, contact):
    """Register producer: trasabilitate register --name "Ion Popescu" --type vegetable_farmer --location "Manastiresti, Vrancea" --contact "ion@example.com"""
    
    payload = {
        "name": name,
        "type": producer_type,
        "location": location,
        "contact": contact
    }
    
    try:
        res = requests.post(f"{API_URL}/producer/register", json=payload, timeout=10)
        data = res.json()
        
        if res.status_code == 201:
            print(f"✓ Producer registered: ID {data['producer_id']}")
            print(f"Name: {name}")
            return True
        else:
            print(f"✗ Error: {data.get('error', 'Unknown error')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Trasabilitate CLI — Loose Produce Traceability',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register a producer
  trasabilitate register --name "Ion Popescu" --type vegetable_farmer --location "Manastiresti" --contact "ion@example.com"
  
  # Create a harvest
  trasabilitate create --producer 1 --product "Tomato" --qty 500
  
  # Record a sale
  trasabilitate sell --id 260308-TOMATO-500KG --buyer-type hypermarket --buyer "Kaufland" --qty 250 --price 1.50 --location "Kaufland warehouse"
  
  # Trace a harvest
  trasabilitate trace --id 260308-TOMATO-500KG
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register new producer')
    register_parser.add_argument('--name', required=True, help='Producer name')
    register_parser.add_argument('--type', required=True, help='Producer type (vegetable_farmer, fruit_farmer, mixed_farmer)')
    register_parser.add_argument('--location', required=True, help='Location')
    register_parser.add_argument('--contact', required=True, help='Email or phone')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new harvest')
    create_parser.add_argument('--producer', type=int, required=True, help='Producer ID')
    create_parser.add_argument('--product', required=True, help='Product name (e.g., Tomato)')
    create_parser.add_argument('--qty', type=float, required=True, help='Quantity in kg')
    create_parser.add_argument('--date', help='Harvest date (YYYY-MM-DD, default: today)')
    
    # Sell command
    sell_parser = subparsers.add_parser('sell', help='Record sale/delivery')
    sell_parser.add_argument('--id', required=True, help='Harvest ID')
    sell_parser.add_argument('--buyer-type', required=True, help='Buyer type (hypermarket, restaurant, wholesaler, export, etc.)')
    sell_parser.add_argument('--buyer', required=True, help='Buyer name')
    sell_parser.add_argument('--qty', type=float, required=True, help='Quantity sold in kg')
    sell_parser.add_argument('--price', type=float, required=True, help='Price per kg (€)')
    sell_parser.add_argument('--location', required=True, help='Delivery location')
    
    # Trace command
    trace_parser = subparsers.add_parser('trace', help='Trace harvest')
    trace_parser.add_argument('--id', required=True, help='Harvest ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    success = False
    
    if args.command == 'register':
        success = register_producer(args.name, args.type, args.location, args.contact)
    elif args.command == 'create':
        success = create_harvest(args.producer, args.product, args.qty, args.date)
    elif args.command == 'sell':
        success = sell_harvest(args.id, args.buyer_type, args.buyer, args.qty, args.price, args.location)
    elif args.command == 'trace':
        success = trace_harvest(args.id)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

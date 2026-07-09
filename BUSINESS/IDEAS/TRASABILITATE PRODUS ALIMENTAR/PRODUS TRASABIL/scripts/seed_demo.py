#!/usr/bin/env python3
"""
Seed database with demo data
"""

import psycopg2
import os
import sys

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://tudor:tudor@localhost:5432/trasabilitate_produce')

def seed_demo_data():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Seeding demo data...")
        
        # Add demo producers
        cur.execute("""
            INSERT INTO producers (name, type, location, contact)
            VALUES 
              ('Ion Popescu', 'vegetable_farmer', 'Manastiresti, Vrancea', 'ion@example.com'),
              ('Maria Ionescu', 'fruit_farmer', 'Pitesti, Arges', 'maria@example.com'),
              ('Gheorghe Vasile', 'mixed_farmer', 'Buzau, Buzau', 'gheorghe@example.com')
            ON CONFLICT DO NOTHING
        """)
        print("✓ Demo producers added")
        
        # Add demo harvests
        cur.execute("""
            INSERT INTO harvests (harvest_id, producer_id, product_name, quantity_kg, harvest_date, qr_code, status)
            SELECT 
              '260308-TOMATO-500KG', id, 'Tomato', 500, '2026-03-08', 'https://trasabilitate.app/harvest/260308-TOMATO-500KG', 'harvested'
            FROM producers WHERE name = 'Ion Popescu'
            ON CONFLICT DO NOTHING
        """)
        
        cur.execute("""
            INSERT INTO harvests (harvest_id, producer_id, product_name, quantity_kg, harvest_date, qr_code, status)
            SELECT 
              '260308-APPLE-300KG', id, 'Apple', 300, '2026-03-08', 'https://trasabilitate.app/harvest/260308-APPLE-300KG', 'harvested'
            FROM producers WHERE name = 'Maria Ionescu'
            ON CONFLICT DO NOTHING
        """)
        print("✓ Demo harvests added")
        
        # Add demo sales
        cur.execute("""
            INSERT INTO sales (harvest_id, buyer_type, buyer_name, quantity_kg, delivery_date, delivery_location, price_per_kg)
            SELECT 
              h.id, 'hypermarket', 'Kaufland Baneasa', 250, '2026-03-08', 'Kaufland warehouse, Sector 1', 1.50
            FROM harvests h WHERE h.harvest_id = '260308-TOMATO-500KG'
            ON CONFLICT DO NOTHING
        """)
        
        cur.execute("""
            INSERT INTO sales (harvest_id, buyer_type, buyer_name, quantity_kg, delivery_date, delivery_location, price_per_kg)
            SELECT 
              h.id, 'restaurant', 'Restaurant Bella Italia', 150, '2026-03-08', 'Restaurant address, Sector 1', 2.00
            FROM harvests h WHERE h.harvest_id = '260308-TOMATO-500KG'
            ON CONFLICT DO NOTHING
        """)
        
        cur.execute("""
            INSERT INTO sales (harvest_id, buyer_type, buyer_name, quantity_kg, delivery_date, delivery_location, price_per_kg)
            SELECT 
              h.id, 'wholesaler', 'Wholesaler ABC', 300, '2026-03-08', 'Wholesaler warehouse, Sector 3', 1.80
            FROM harvests h WHERE h.harvest_id = '260308-APPLE-300KG'
            ON CONFLICT DO NOTHING
        """)
        print("✓ Demo sales added")
        
        conn.commit()
        conn.close()
        
        print("\n✓ Demo data seeded successfully!")
        print("Test with: trasabilitate trace --id 260308-TOMATO-500KG")
        return True
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    if seed_demo_data():
        sys.exit(0)
    else:
        sys.exit(1)

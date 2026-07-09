#!/usr/bin/env python3
"""Initialize PostgreSQL database schema"""

import psycopg2
import os
import sys

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://tudor:tudor@localhost:5432/trasabilitate_produce')

def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Creating database schema...")
        
        # Producers table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS producers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                type VARCHAR(50),
                location VARCHAR(200),
                contact VARCHAR(250),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✓ Producers table created")
        
        # Harvests table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS harvests (
                id SERIAL PRIMARY KEY,
                harvest_id VARCHAR(50) UNIQUE NOT NULL,
                producer_id INT REFERENCES producers(id) ON DELETE CASCADE,
                product_name VARCHAR(100),
                quantity_kg NUMERIC(10,2),
                harvest_date DATE,
                qr_code VARCHAR(500),
                status VARCHAR(20) DEFAULT 'harvested',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✓ Harvests table created")
        
        # Sales table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                harvest_id INT REFERENCES harvests(id) ON DELETE CASCADE,
                buyer_type VARCHAR(50),
                buyer_name VARCHAR(200),
                quantity_kg NUMERIC(10,2),
                delivery_date DATE,
                delivery_location VARCHAR(200),
                price_per_kg NUMERIC(10,2),
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✓ Sales table created")
        
        # Audit log table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                harvest_id INT REFERENCES harvests(id) ON DELETE CASCADE,
                action VARCHAR(100),
                actor VARCHAR(100),
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✓ Audit log table created")
        
        # Create indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_harvest_id ON harvests(harvest_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_producer_id ON harvests(producer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_harvest ON sales(harvest_id)")
        print("✓ Indexes created")
        
        conn.commit()
        conn.close()
        
        print("\n✓ Database initialized successfully!")
        return True
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == '__main__':
    if init_db():
        sys.exit(0)
    else:
        sys.exit(1)

# 7-Day MVP Sprint — Loose Produce Traceability

**Scope**: Vegetables + Fruits ONLY (loose, weight-based tracking)
**Markets**: Hypermarket + Restaurants + Wholesalers + Export
**No**: Transformers, HACCP, temperature logging, packaging

---

## Day 1-2: Backend Infrastructure

### Task 1.1: PostgreSQL Schema (SIMPLIFIED for loose produce)
```sql
-- Producers (farmers)
CREATE TABLE producers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200),
  type VARCHAR(50),           -- "vegetable_farmer", "fruit_farmer"
  location VARCHAR(200),
  contact VARCHAR(250),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Harvests (replaces "batches" for loose produce)
CREATE TABLE harvests (
  id SERIAL PRIMARY KEY,
  harvest_id VARCHAR(50) UNIQUE,        -- "260307-TOMATO-500KG"
  producer_id INT REFERENCES producers(id),
  product_name VARCHAR(100),             -- "Tomato", "Apple"
  quantity_kg NUMERIC(10,2),
  harvest_date DATE,
  qr_code VARCHAR(500),                  -- URL to dashboard
  status VARCHAR(20),                    -- "harvested", "at_market", "sold"
  created_at TIMESTAMP DEFAULT NOW()
);

-- Sales/Deliveries (who bought it, where it went)
CREATE TABLE sales (
  id SERIAL PRIMARY KEY,
  harvest_id INT REFERENCES harvests(id),
  buyer_type VARCHAR(50),                -- "hypermarket", "restaurant", "wholesaler", "export"
  buyer_name VARCHAR(200),
  quantity_kg NUMERIC(10,2),
  delivery_date DATE,
  delivery_location VARCHAR(200),
  price_per_kg NUMERIC(10,2),
  notes TEXT
);

-- Simple audit log (proves traceability backwards 1-step)
CREATE TABLE audit_log (
  id SERIAL PRIMARY KEY,
  harvest_id INT REFERENCES harvests(id),
  action VARCHAR(100),                   -- "created", "sold", "delivered"
  actor VARCHAR(100),
  timestamp TIMESTAMP DEFAULT NOW()
);
```

### Task 1.2: Flask App Skeleton
```python
# app.py
from flask import Flask, jsonify, request
import psycopg2
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['DATABASE'] = 'postgresql://tudor:tudor@localhost:5432/trasabilitate_produce'

def get_db():
    return psycopg2.connect(app.config['DATABASE'])

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Task 1.3: Docker Setup
```dockerfile
# Backend Dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]

# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: trasabilitate_produce
      POSTGRES_USER: tudor
      POSTGRES_PASSWORD: tudor
    ports:
      - "5432:5432"
  backend:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - db
```

---

## Day 2-3: Core API Endpoints

### Task 2.1: Harvest CRUD
```python
# routes/harvests.py
import qrcode
from flask import Blueprint, request, jsonify

harvests_bp = Blueprint('harvests', __name__)

@harvests_bp.route('/harvest/create', methods=['POST'])
def create_harvest():
    """
    POST /harvest/create
    Body: {
      "producer_id": 1,
      "product_name": "Tomato",
      "quantity_kg": 500,
      "harvest_date": "2026-03-07"
    }
    """
    data = request.json
    harvest_id = f"{datetime.now().strftime('%y%m%d')}-{data['product_name'].upper()}-{int(data['quantity_kg'])}KG"
    qr_url = f"https://trasabilitate.app/harvest/{harvest_id}"
    
    # Generate QR code
    qr = qrcode.make(qr_url)
    qr.save(f"/tmp/{harvest_id}.png")
    
    # Insert into DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO harvests (harvest_id, producer_id, product_name, quantity_kg, harvest_date, qr_code, status)
      VALUES (%s, %s, %s, %s, %s, %s, 'harvested')
    """, (harvest_id, data['producer_id'], data['product_name'], data['quantity_kg'], data['harvest_date'], qr_url))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'harvest_id': harvest_id, 'qr': qr_url}), 201

@harvests_bp.route('/harvest/<harvest_id>', methods=['GET'])
def get_harvest(harvest_id):
    """GET /harvest/260307-TOMATO-500KG"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM harvests WHERE harvest_id = %s", (harvest_id,))
    harvest = cur.fetchone()
    conn.close()
    
    if not harvest:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'harvest_id': harvest[1],
        'product': harvest[3],
        'quantity_kg': harvest[4],
        'harvest_date': harvest[5].isoformat(),
        'status': harvest[7]
    })
```

### Task 2.2: Sales/Delivery Tracking
```python
@harvests_bp.route('/harvest/<harvest_id>/sell', methods=['POST'])
def record_sale(harvest_id):
    """
    POST /harvest/260307-TOMATO-500KG/sell
    Body: {
      "buyer_type": "hypermarket",
      "buyer_name": "Kaufland Baneasa",
      "quantity_kg": 250,
      "delivery_date": "2026-03-07",
      "delivery_location": "Kaufland warehouse, Sector 1",
      "price_per_kg": 1.50
    }
    """
    data = request.json
    
    conn = get_db()
    cur = conn.cursor()
    
    # Get harvest first
    cur.execute("SELECT id FROM harvests WHERE harvest_id = %s", (harvest_id,))
    harvest_rec = cur.fetchone()
    if not harvest_rec:
        return jsonify({'error': 'Harvest not found'}), 404
    
    harvest_id_pk = harvest_rec[0]
    
    # Record sale
    cur.execute("""
      INSERT INTO sales (harvest_id, buyer_type, buyer_name, quantity_kg, delivery_date, delivery_location, price_per_kg)
      VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (harvest_id_pk, data['buyer_type'], data['buyer_name'], data['quantity_kg'], 
          data['delivery_date'], data['delivery_location'], data['price_per_kg']))
    
    # Update harvest status
    cur.execute("UPDATE harvests SET status = 'sold' WHERE id = %s", (harvest_id_pk,))
    
    # Log to audit
    cur.execute("""
      INSERT INTO audit_log (harvest_id, action, actor)
      VALUES (%s, 'sold_to_%s', %s)
    """, (harvest_id_pk, data['buyer_type'], data['buyer_name']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f"Sold {data['quantity_kg']}kg to {data['buyer_name']}"}), 201

@harvests_bp.route('/harvest/<harvest_id>/trace', methods=['GET'])
def get_trace(harvest_id):
    """GET /harvest/260307-TOMATO-500KG/trace
    Returns: 1-step-back (producer) + forward (sales)
    """
    conn = get_db()
    cur = conn.cursor()
    
    # Get harvest + producer (1-step back)
    cur.execute("""
      SELECT h.harvest_id, h.product_name, h.quantity_kg, h.harvest_date, 
             p.name, p.location
      FROM harvests h
      JOIN producers p ON h.producer_id = p.id
      WHERE h.harvest_id = %s
    """, (harvest_id,))
    harvest = cur.fetchone()
    
    if not harvest:
        return jsonify({'error': 'Not found'}), 404
    
    # Get sales (forward trace)
    cur.execute("""
      SELECT buyer_type, buyer_name, quantity_kg, delivery_date, delivery_location, price_per_kg
      FROM sales
      WHERE harvest_id = (SELECT id FROM harvests WHERE harvest_id = %s)
    """, (harvest_id,))
    sales = cur.fetchall()
    conn.close()
    
    return jsonify({
        'harvest': {
            'id': harvest[0],
            'product': harvest[1],
            'quantity_kg': harvest[2],
            'date': harvest[3].isoformat(),
            'producer': harvest[4],
            'producer_location': harvest[5]
        },
        'sales': [
            {
                'buyer_type': s[0],
                'buyer_name': s[1],
                'quantity_kg': s[2],
                'delivery_date': s[3].isoformat(),
                'location': s[4],
                'price_per_kg': s[5]
            }
            for s in sales
        ]
    })
```

### Task 2.3: Producer Registration
```python
@harvests_bp.route('/producer/register', methods=['POST'])
def register_producer():
    """
    POST /producer/register
    Body: {
      "name": "Ion Popescu",
      "type": "vegetable_farmer",
      "location": "Manastiresti, Vrancea",
      "contact": "ion@example.com"
    }
    """
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO producers (name, type, location, contact)
      VALUES (%s, %s, %s, %s)
    """)
    cur.execute("INSERT INTO producers VALUES (DEFAULT, %s, %s, %s, %s, DEFAULT)", 
                (data['name'], data['type'], data['location'], data['contact']))
    conn.commit()
    conn.close()
    return jsonify({'success': True}), 201
```

---

## Day 3-4: QR Code + Frontend Bare-Bones

### Task 3.1: QR Code Display Page
```html
<!-- public/harvest.html -->
<!DOCTYPE html>
<html>
<head>
  <title>Harvest Trace</title>
  <style>
    body { font-family: Arial; margin: 20px; }
    .container { max-width: 600px; margin: 0 auto; }
    .harvest-info { background: #f0f0f0; padding: 20px; border-radius: 5px; }
    .trace { margin-top: 20px; }
    .buyer { background: #e8f5e9; padding: 10px; margin: 10px 0; border-radius: 3px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Harvest Traceability</h1>
    
    <div id="harvest-info" class="harvest-info">
      Loading...
    </div>
    
    <div id="trace" class="trace">
      <h3>Sales & Deliveries</h3>
      <div id="sales-list"></div>
    </div>
  </div>

  <script>
    const harvestId = new URL(window.location).searchParams.get('id');
    
    fetch(`/api/harvest/${harvestId}/trace`)
      .then(r => r.json())
      .then(data => {
        document.getElementById('harvest-info').innerHTML = `
          <h2>${data.harvest.product}</h2>
          <p><strong>Quantity:</strong> ${data.harvest.quantity_kg} kg</p>
          <p><strong>Harvest Date:</strong> ${data.harvest.date}</p>
          <p><strong>Producer:</strong> ${data.harvest.producer}</p>
          <p><strong>Location:</strong> ${data.harvest.producer_location}</p>
        `;
        
        let salesHtml = '';
        data.sales.forEach(sale => {
          salesHtml += `
            <div class="buyer">
              <p><strong>${sale.buyer_type.toUpperCase()}</strong>: ${sale.buyer_name}</p>
              <p>${sale.quantity_kg} kg @ €${sale.price_per_kg}/kg</p>
              <p>Delivered: ${sale.delivery_date} to ${sale.location}</p>
            </div>
          `;
        });
        document.getElementById('sales-list').innerHTML = salesHtml;
      });
  </script>
</body>
</html>
```

### Task 3.2: Simple React Dashboard (BARE MINIMUM)
```javascript
// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';

function App() {
  const [harvestId, setHarvestId] = useState('');
  const [traceData, setTraceData] = useState(null);

  const fetchTrace = async () => {
    const res = await fetch(`/api/harvest/${harvestId}/trace`);
    const data = await res.json();
    setTraceData(data);
  };

  return (
    <div className="App">
      <h1>Trasabilitate — Loose Produce</h1>
      
      <div className="search">
        <input 
          placeholder="Harvest ID (e.g., 260307-TOMATO-500KG)"
          value={harvestId}
          onChange={(e) => setHarvestId(e.target.value)}
        />
        <button onClick={fetchTrace}>Trace Harvest</button>
      </div>

      {traceData && (
        <div className="trace-result">
          <h2>{traceData.harvest.product}</h2>
          <p>{traceData.harvest.quantity_kg}kg harvested on {traceData.harvest.date}</p>
          <p>From: {traceData.harvest.producer} ({traceData.harvest.producer_location})</p>
          
          <h3>Where It Went</h3>
          {traceData.sales.map((sale, idx) => (
            <div key={idx} className="sale">
              <p><strong>{sale.buyer_type}</strong>: {sale.buyer_name}</p>
              <p>{sale.quantity_kg}kg delivered to {sale.location}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
```

---

## Day 4-5: CLI Tools (Producer-Friendly)

### Task 4.1: CLI Installer + Setup
```python
# cli/trasabilitate.py
#!/usr/bin/env python3

import argparse
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000/api"  # Will be production URL

def create_harvest(producer_id, product, quantity_kg, harvest_date):
    """trasabilitate harvest create --producer 1 --product "Tomato" --qty 500"""
    
    payload = {
        "producer_id": producer_id,
        "product_name": product,
        "quantity_kg": quantity_kg,
        "harvest_date": harvest_date
    }
    
    res = requests.post(f"{BASE_URL}/harvest/create", json=payload)
    data = res.json()
    
    print(f"✓ Harvest created: {data['harvest_id']}")
    print(f"✓ QR code: {data['qr']}")
    print(f"\nShare this link: {data['qr']}")

def sell_harvest(harvest_id, buyer_type, buyer_name, quantity_kg, price_per_kg, location):
    """trasabilitate harvest sell --id 260307-TOMATO-500KG --buyer-type hypermarket --buyer "Kaufland" --qty 250 --price 1.50"""
    
    payload = {
        "buyer_type": buyer_type,
        "buyer_name": buyer_name,
        "quantity_kg": quantity_kg,
        "delivery_date": datetime.now().strftime('%Y-%m-%d'),
        "delivery_location": location,
        "price_per_kg": price_per_kg
    }
    
    res = requests.post(f"{BASE_URL}/harvest/{harvest_id}/sell", json=payload)
    data = res.json()
    
    print(f"✓ Sale recorded: {data['message']}")

def trace_harvest(harvest_id):
    """trasabilitate trace --id 260307-TOMATO-500KG"""
    
    res = requests.get(f"{BASE_URL}/harvest/{harvest_id}/trace")
    data = res.json()
    
    print(f"\n=== HARVEST TRACE ===")
    print(f"Product: {data['harvest']['product']}")
    print(f"Quantity: {data['harvest']['quantity_kg']}kg")
    print(f"Harvested: {data['harvest']['date']}")
    print(f"Producer: {data['harvest']['producer']}")
    print(f"Location: {data['harvest']['producer_location']}")
    print(f"\n=== SALES ===")
    
    for sale in data['sales']:
        print(f"\n{sale['buyer_type'].upper()}: {sale['buyer_name']}")
        print(f"  {sale['quantity_kg']}kg @ €{sale['price_per_kg']}/kg")
        print(f"  Delivered: {sale['delivery_date']} to {sale['location']}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trasabilitate CLI')
    subparsers = parser.add_subparsers(dest='command')
    
    # harvest create
    create_parser = subparsers.add_parser('create', help='Create new harvest')
    create_parser.add_argument('--producer', type=int, required=True)
    create_parser.add_argument('--product', required=True)
    create_parser.add_argument('--qty', type=float, required=True)
    create_parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    
    # harvest sell
    sell_parser = subparsers.add_parser('sell', help='Record sale')
    sell_parser.add_argument('--id', required=True)
    sell_parser.add_argument('--buyer-type', required=True)
    sell_parser.add_argument('--buyer', required=True)
    sell_parser.add_argument('--qty', type=float, required=True)
    sell_parser.add_argument('--price', type=float, required=True)
    sell_parser.add_argument('--location', required=True)
    
    # trace
    trace_parser = subparsers.add_parser('trace', help='Trace harvest')
    trace_parser.add_argument('--id', required=True)
    
    args = parser.parse_args()
    
    if args.command == 'create':
        create_harvest(args.producer, args.product, args.qty, args.date)
    elif args.command == 'sell':
        sell_harvest(args.id, args.buyer_type, args.buyer, args.qty, args.price, args.location)
    elif args.command == 'trace':
        trace_harvest(args.id)
```

---

## Day 5-6: Testing + Deployment

### Task 5.1: Unit Tests
```python
# tests/test_harvest.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_harvest_create(client):
    res = client.post('/api/harvest/create', json={
        "producer_id": 1,
        "product_name": "Tomato",
        "quantity_kg": 500,
        "harvest_date": "2026-03-07"
    })
    assert res.status_code == 201
    assert 'harvest_id' in res.json

def test_harvest_trace(client):
    res = client.get('/api/harvest/260307-TOMATO-500KG/trace')
    assert res.status_code == 200
    assert 'harvest' in res.json

def test_sale_record(client):
    res = client.post('/api/harvest/260307-TOMATO-500KG/sell', json={
        "buyer_type": "hypermarket",
        "buyer_name": "Kaufland",
        "quantity_kg": 250,
        "delivery_date": "2026-03-07",
        "delivery_location": "Kaufland Baneasa",
        "price_per_kg": 1.50
    })
    assert res.status_code == 201
```

### Task 5.2: Deployment (Heroku or VPS)

**Option A: Heroku (easiest)**
```bash
# Procfile
web: gunicorn app:app
worker: python app.py

# requirements.txt
Flask==2.3.0
psycopg2-binary==2.9.0
qrcode==7.4.0
Pillow==9.5.0
requests==2.31.0
gunicorn==21.0.0
```

**Option B: VPS (DigitalOcean/Linode)**
```bash
#!/bin/bash
# deploy.sh

# Install dependencies
apt-get update
apt-get install -y python3 python3-pip postgresql postgresql-contrib nginx

# Copy code
cp -r /local/trasabilitate /home/app/

# Create systemd service
cat > /etc/systemd/system/trasabilitate.service << EOF
[Unit]
Description=Trasabilitate API
After=network.target

[Service]
User=app
WorkingDirectory=/home/app/trasabilitate
ExecStart=/usr/bin/python3 /home/app/trasabilitate/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl start trasabilitate
systemctl enable trasabilitate
```

---

## Day 6-7: Validation + Launch

### Task 6.1: Test Data
```python
# scripts/seed_demo.py
import psycopg2

conn = psycopg2.connect("dbname=trasabilitate_produce user=tudor password=tudor")
cur = conn.cursor()

# Add demo producer
cur.execute("""
  INSERT INTO producers (name, type, location, contact)
  VALUES ('Ion Popescu', 'vegetable_farmer', 'Manastiresti, Vrancea', 'ion@example.com')
""")

# Add demo harvest
cur.execute("""
  INSERT INTO harvests (harvest_id, producer_id, product_name, quantity_kg, harvest_date, qr_code, status)
  VALUES ('260307-TOMATO-500KG', 1, 'Tomato', 500, '2026-03-07', 'https://trasabilitate.app/harvest/260307-TOMATO-500KG', 'harvested')
""")

conn.commit()
conn.close()
print("✓ Demo data loaded")
```

### Task 6.2: Day 7 VALIDATION CALLS

**Call 1: Kaufland Procurement** (9 AM)
```
"Hi, I've built a traceability system for loose produce suppliers. 
Can producers track their vegetables from harvest → hypermarket shelf? 
Does Kaufland require this for sourcing?"

Expected: Yes/No/Maybe signals
```

**Call 2: Vegetable Farmer** (10 AM)
```
"I have a simple app where you log your harvest, get a QR code, 
and record where it goes. Would you test it for 3 free harvests?"

Expected: Yes/No/interest
```

**Call 3: Wholesaler/Restaurant** (11 AM)
```
"Can we trace produce from farmer → your kitchen? 
This helps with food safety documentation."

Expected: Interest signal
```

---

## Deliverables (End of Day 7)

- ✅ Working API (`localhost:5000`)
- ✅ CLI tool (3 commands: create, sell, trace)
- ✅ Web dashboard (bare-bones React)
- ✅ PostgreSQL database (5 tables)
- ✅ QR code generation
- ✅ Docker setup (one `docker-compose up` away)
- ✅ Deployed to Heroku or VPS (public URL)
- ✅ Validation feedback from Kaufland + farmers + wholesalers

---

## Requirements (Day 1 Start)

```
Python 3.9+
PostgreSQL 13+
Node.js 16+ (for React)
Docker (optional, for local dev)
```

```
# Python
pip install Flask psycopg2-binary qrcode Pillow requests

# Node.js
npm install -g create-react-app
```

---

## Go/No-Go Decision (End of Day 7)

| Signal | Go | Wait | No-Go |
|--------|----|----|-------|
| Kaufland: "Yes, we need this" | ✅ Launch | - | - |
| 2+ farmers: "I'll test" | ✅ Launch | - | - |
| Wholesaler: "Interested" | ✅ Launch | - | - |
| All rejections | - | - | ❌ Pivot |

**If GO**: Sign first 20 producers week 8+, target EUR 1K/month MRR by end of April.

**If WAIT/NO-GO**: Analyze feedback, pivot market or feature scope.

---

## Success Metrics (Day 7)

- [ ] API endpoints working (test with Postman)
- [ ] QR codes generate correctly
- [ ] Database stores/retrieves data
- [ ] CLI works (`trasabilitate create --producer 1 --product "Tomato" --qty 500`)
- [ ] Web dashboard loads
- [ ] At least 1 validation call successful

**Is this your plan? Start building?**

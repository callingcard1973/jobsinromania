#!/usr/bin/env python3
"""
Trasabilitate Backend — Loose Produce Traceability
Optimized for Raspberry Pi + PostgreSQL
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import qrcode
from datetime import datetime
from io import BytesIO
import logging

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)

# Configure database
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://tudor:tudor@localhost:5432/trasabilitate_produce')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
def get_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return None

# Health check
@app.route('/health', methods=['GET'])
def health():
    conn = get_db()
    if conn:
        conn.close()
        return jsonify({'status': 'healthy'}), 200
    return jsonify({'status': 'unhealthy', 'error': 'DB connection failed'}), 503

# ============ PRODUCER ROUTES ============

@app.route('/api/producer/register', methods=['POST'])
def register_producer():
    """
    POST /api/producer/register
    Body: {
      "name": "Ion Popescu",
      "type": "vegetable_farmer",
      "location": "Manastiresti, Vrancea",
      "contact": "ion@example.com"
    }
    """
    data = request.json
    conn = get_db()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO producers (name, type, location, contact)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (data['name'], data['type'], data['location'], data['contact']))
        
        producer_id = cur.fetchone()[0]
        conn.commit()
        
        logger.info(f"Producer registered: {producer_id} - {data['name']}")
        return jsonify({'success': True, 'producer_id': producer_id}), 201
    except Exception as e:
        logger.error(f"Register producer error: {e}")
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

# ============ HARVEST ROUTES ============

@app.route('/api/harvest/create', methods=['POST'])
def create_harvest():
    """
    POST /api/harvest/create
    Body: {
      "producer_id": 1,
      "product_name": "Tomato",
      "quantity_kg": 500,
      "harvest_date": "2026-03-08"
    }
    """
    data = request.json
    conn = get_db()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Generate harvest ID
        harvest_id = f"{datetime.now().strftime('%y%m%d')}-{data['product_name'].upper()}-{int(data['quantity_kg'])}KG"
        qr_url = f"https://trasabilitate.app/harvest/{harvest_id}"
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO harvests (harvest_id, producer_id, product_name, quantity_kg, harvest_date, qr_code, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'harvested')
            RETURNING id
        """, (harvest_id, data['producer_id'], data['product_name'], data['quantity_kg'], 
              data['harvest_date'], qr_url))
        
        conn.commit()
        
        logger.info(f"Harvest created: {harvest_id}")
        return jsonify({
            'success': True,
            'harvest_id': harvest_id,
            'qr': qr_url
        }), 201
    except Exception as e:
        logger.error(f"Create harvest error: {e}")
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/harvest/<harvest_id>', methods=['GET'])
def get_harvest(harvest_id):
    """GET /api/harvest/260308-TOMATO-500KG"""
    conn = get_db()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM harvests WHERE harvest_id = %s", (harvest_id,))
        harvest = cur.fetchone()
        conn.close()
        
        if not harvest:
            return jsonify({'error': 'Harvest not found'}), 404
        
        return jsonify(dict(harvest)), 200
    except Exception as e:
        logger.error(f"Get harvest error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/harvest/<harvest_id>/trace', methods=['GET'])
def get_trace(harvest_id):
    """
    GET /api/harvest/260308-TOMATO-500KG/trace
    Returns: Producer (1-step back) + Sales (forward)
    """
    conn = get_db()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get harvest + producer
        cur.execute("""
            SELECT h.harvest_id, h.product_name, h.quantity_kg, h.harvest_date, 
                   p.name, p.location, p.type
            FROM harvests h
            JOIN producers p ON h.producer_id = p.id
            WHERE h.harvest_id = %s
        """, (harvest_id,))
        harvest = cur.fetchone()
        
        if not harvest:
            conn.close()
            return jsonify({'error': 'Harvest not found'}), 404
        
        # Get sales
        cur.execute("""
            SELECT buyer_type, buyer_name, quantity_kg, delivery_date, delivery_location, price_per_kg
            FROM sales
            WHERE harvest_id = (SELECT id FROM harvests WHERE harvest_id = %s)
        """, (harvest_id,))
        sales = cur.fetchall()
        conn.close()
        
        return jsonify({
            'harvest': dict(harvest),
            'sales': [dict(s) for s in sales]
        }), 200
    except Exception as e:
        logger.error(f"Get trace error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/harvest/<harvest_id>/sell', methods=['POST'])
def record_sale(harvest_id):
    """
    POST /api/harvest/260308-TOMATO-500KG/sell
    Body: {
      "buyer_type": "hypermarket",
      "buyer_name": "Kaufland Baneasa",
      "quantity_kg": 250,
      "delivery_date": "2026-03-08",
      "delivery_location": "Kaufland warehouse, Sector 1",
      "price_per_kg": 1.50
    }
    """
    data = request.json
    conn = get_db()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get harvest ID
        cur.execute("SELECT id FROM harvests WHERE harvest_id = %s", (harvest_id,))
        harvest_rec = cur.fetchone()
        
        if not harvest_rec:
            conn.close()
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
            INSERT INTO audit_log (harvest_id, action, actor, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (harvest_id_pk, f"sold_to_{data['buyer_type']}", data['buyer_name']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Sale recorded for {harvest_id}: {data['quantity_kg']}kg to {data['buyer_name']}")
        return jsonify({
            'success': True,
            'message': f"Sold {data['quantity_kg']}kg to {data['buyer_name']}"
        }), 201
    except Exception as e:
        logger.error(f"Record sale error: {e}")
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

# ============ QR CODE ROUTES ============

@app.route('/api/qr/<harvest_id>', methods=['GET'])
def get_qr_code(harvest_id):
    """GET /api/qr/260308-TOMATO-500KG — Returns QR code PNG"""
    try:
        qr_url = f"https://trasabilitate.app/harvest/{harvest_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to bytes
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return img_io.getvalue(), 200, {'Content-Type': 'image/png'}
    except Exception as e:
        logger.error(f"QR code error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ FRONTEND ROUTES ============

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React static files"""
    if path != "" and os.path.exists(f"../frontend/build/{path}"):
        return send_from_directory("../frontend/build", path)
    else:
        return send_from_directory("../frontend/build", "index.html")

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # For Raspberry Pi: use 0.0.0.0 to allow remote connections
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_ENV') == 'development')

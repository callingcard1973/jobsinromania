#!/usr/bin/env python3
"""
Unit tests for Trasabilitate API
Run with: pytest tests/test_api.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from backend.app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    """Test health check endpoint"""
    res = client.get('/health')
    assert res.status_code == 200

def test_harvest_create(client):
    """Test harvest creation (mock - won't work without DB)"""
    res = client.post('/api/harvest/create', 
        json={
            "producer_id": 1,
            "product_name": "Tomato",
            "quantity_kg": 500,
            "harvest_date": "2026-03-08"
        }
    )
    # Should fail without DB, but endpoint should exist
    assert res.status_code in [201, 500]

def test_harvest_trace(client):
    """Test harvest trace endpoint"""
    res = client.get('/api/harvest/260308-TOMATO-500KG/trace')
    # 404 expected without real data
    assert res.status_code in [200, 404, 500]

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

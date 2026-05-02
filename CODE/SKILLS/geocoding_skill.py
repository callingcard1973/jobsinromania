#!/usr/bin/env python3
"""
OpenCage Geocoding Skill
Forward & reverse geocoding for all locations

Usage:
  python geocoding_skill.py "Bucharest, Romania"
  python geocoding_skill.py --reverse 44.426 26.104
  python geocoding_skill.py --batch cities.csv
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
# Also try common locations
for env_path in ['/opt/DATA/.env_apis', '/opt/DATA/.env', Path.home() / '.env', 'geocoding_skill.env']:
    if Path(env_path).exists():
        load_dotenv(env_path)
        break

API_KEY = os.environ.get('OPENCAGE_API_KEY')

if not API_KEY:
    print("ERROR: OPENCAGE_API_KEY not found in environment")
    sys.exit(1)

class GeocodeAPI:
    """OpenCage Geocoding API wrapper"""

    BASE_URL = "https://api.opencagedata.com/geocode/v1/json"
    TIMEOUT = 10

    @staticmethod
    def forward(query: str, limit: int = 1) -> List[Dict]:
        """
        Forward geocoding: address → coordinates

        Args:
            query: Location name (e.g., "Bucharest, Romania")
            limit: Number of results to return

        Returns:
            List of results with geometry, formatted address, etc.
        """
        params = {
            'q': query,
            'key': API_KEY,
            'limit': limit
        }

        try:
            r = requests.get(GeocodeAPI.BASE_URL, params=params, timeout=GeocodeAPI.TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                return data.get('results', [])
            else:
                print(f"Error: HTTP {r.status_code}")
                return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    @staticmethod
    def reverse(lat: float, lon: float, limit: int = 1) -> List[Dict]:
        """
        Reverse geocoding: coordinates → address

        Args:
            lat: Latitude
            lon: Longitude
            limit: Number of results

        Returns:
            List of results with address, formatted text, etc.
        """
        query = f"{lat},{lon}"
        params = {
            'q': query,
            'key': API_KEY,
            'limit': limit
        }

        try:
            r = requests.get(GeocodeAPI.BASE_URL, params=params, timeout=GeocodeAPI.TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                return data.get('results', [])
            else:
                print(f"Error: HTTP {r.status_code}")
                return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    @staticmethod
    def get_coords(query: str) -> Optional[Tuple[float, float]]:
        """Get single (lat, lon) from address"""
        results = GeocodeAPI.forward(query, limit=1)
        if results:
            geom = results[0].get('geometry', {})
            lat = geom.get('lat')
            lon = geom.get('lng') or geom.get('lon')
            return lat, lon
        return None

    @staticmethod
    def get_address(lat: float, lon: float) -> Optional[str]:
        """Get single address from coordinates"""
        results = GeocodeAPI.reverse(lat, lon, limit=1)
        if results:
            return results[0].get('formatted')
        return None

    @staticmethod
    def batch_forward(addresses: List[str]) -> Dict[str, Dict]:
        """Geocode multiple addresses"""
        results = {}
        for addr in addresses:
            res = GeocodeAPI.forward(addr, limit=1)
            if res:
                lon = res[0]['geometry'].get('lng') or res[0]['geometry'].get('lon')
                results[addr] = {
                    'lat': res[0]['geometry']['lat'],
                    'lon': lon,
                    'formatted': res[0].get('formatted')
                }
        return results


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    if sys.argv[1] == '--reverse':
        # Reverse geocoding
        if len(sys.argv) < 4:
            print("Usage: geocoding_skill.py --reverse LAT LON")
            return
        lat, lon = float(sys.argv[2]), float(sys.argv[3])
        results = GeocodeAPI.reverse(lat, lon)
        print(json.dumps(results, indent=2))

    elif sys.argv[1] == '--batch':
        # Batch geocoding from CSV
        if len(sys.argv) < 3:
            print("Usage: geocoding_skill.py --batch FILE.csv")
            return
        csv_file = sys.argv[2]
        if not Path(csv_file).exists():
            print(f"Error: {csv_file} not found")
            return

        import csv
        addresses = []
        with open(csv_file) as f:
            for row in csv.DictReader(f):
                # Assumes 'address' or 'location' column
                addr = row.get('address') or row.get('location') or row.get('city')
                if addr:
                    addresses.append(addr)

        results = GeocodeAPI.batch_forward(addresses)
        print(json.dumps(results, indent=2))

    else:
        # Forward geocoding
        query = ' '.join(sys.argv[1:])
        results = GeocodeAPI.forward(query)

        if results:
            result = results[0]
            print(f"Address: {query}")
            print(f"Formatted: {result.get('formatted')}")
            lat = result['geometry']['lat']
            lon = result['geometry'].get('lng') or result['geometry'].get('lon')
            print(f"Lat: {lat}")
            print(f"Lon: {lon}")
            print(f"Country: {result.get('components', {}).get('country')}")
        else:
            print(f"No results for: {query}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Interactive mode if no args
        print("OpenCage Geocoding Skill")
        print("=" * 40)
        print(f"API Key: {API_KEY[:20]}...")
        print()

        # Demo
        print("Demo: Geocoding 'Bucharest, Romania'")
        results = GeocodeAPI.forward("Bucharest, Romania")
        if results:
            r = results[0]
            lon = r['geometry'].get('lng') or r['geometry'].get('lon')
            print(f"  Location: {r['geometry']['lat']:.4f}, {lon:.4f}")
            print(f"  Address: {r.get('formatted')}")

    else:
        main()

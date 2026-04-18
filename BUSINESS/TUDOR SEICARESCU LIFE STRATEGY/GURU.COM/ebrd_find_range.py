#!/usr/bin/env python3
import requests
sess = requests.Session()
sess.headers['User-Agent'] = 'Mozilla/5.0'
for pid in [100, 1000, 5000, 10000, 20000, 30000, 35000, 40000, 42000, 44000, 45000, 46000, 47000, 48000, 49000, 50000, 51000, 52000, 53000, 54000, 55000, 56000, 56433, 57000]:
    try:
        r = sess.get(f"https://www.ebrd.com/home/work-with-us/projects/psd/{pid}.html", timeout=15)
        print(f"{pid}: {r.status_code}")
    except Exception as e:
        print(f"{pid}: {e}")

"""
MERCOSUR Parallel Scraping System

6 Worker Architecture:
- websites: Website contact extraction (10 threads)
- govapis: Government API discovery (5 threads)
- associations: Trade association members (5 threads + Selenium)
- registries: Bulk registry downloads (2 threads)
- tradeshows: Trade show exhibitors (3 threads + Selenium)
- enricher: Contact enrichment (8 threads)

Usage:
    python orchestrator.py --all
    python orchestrator.py --worker websites
    python merger.py
"""

__version__ = "1.0.0"

# CLAUDE.md - MERCOSUR Total Scraper System

| category | status | owner | updated |
| other | active | tudor | 2026-03-23 |

## Purpose

Comprehensive scraping infrastructure to collect Mercosur exporter data for EU-Mercosur trade agreement arbitrage. Core model: broker/matchmaker connecting EU buyers (1.57M TED winners) with Mercosur suppliers.

## Current Status (March 22, 2026)

| Metric | Value |
| Companies collected | 700 |
| With email | 246 (35%) |
| With website | 271 (39%) |
| With phone | 42 (6%) |

## What Works

| Worker/Scraper | Success Rate | Notes |
| worker_enricher.py | 71% (97/137) | Best performer - generates info@domain patterns |
| deep_scraper.py | 76 companies | ABPA poultry + CAPECO grains |
| worker_websites.py | 3% (1/30) | Many sites unreachable |
| connectamericas_web.py | 2 companies | Search API limited |

## What Doesn't Work

| Scraper | Issue |
| worker_associations.py | Needs Selenium (JS pages) |
| worker_tradeshows.py | Needs Selenium (JS pages) |
| worker_govapis.py | APIs not publicly exposed |
| kompass_latam.py | Blocked/selectors changed |
| trademap.py | Comtrade API errors |
| brazil_comex.py | Parser bug (API format changed) |

## Files

| File | Purpose |
| `TODO` | Description |

## Output

{TODO: Describe output location and format.}

## Quick Start

## Enricher Strategy (Best Approach)

The enricher generates common email patterns and verifies domain exists:

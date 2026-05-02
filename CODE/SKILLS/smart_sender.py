#!/usr/bin/env python3
"""
Smart Sender - Dynamically assign best available sender for campaigns.

Assigns senders based on:
1. Sector match (HORECA -> horecaworkers.eu)
2. Available capacity (highest remaining first)
3. Sender type priority (A2 > Brevo > Gmail)
4. Warmup status

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/smart_sender.py --campaign HORECA2026
    python3 /opt/ACTIVE/INFRA/SKILLS/smart_sender.py --sector FACTORY --count 3
    python3 /opt/ACTIVE/INFRA/SKILLS/smart_sender.py --dry-run
"""
import os
import sys
import csv
import json
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple, List, Dict

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
from skills_common import to_ascii
from capacity_tracker import (
    get_sender_capacity,
    get_available_senders,
    SENDER_LIMITS,
    SECTOR_MAPPING,
)

# Import campaign config
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS')
from config import AVAILABLE_SENDERS, CAMPAIGNS

# Try to import sector config from config.py, fall back to defaults
try:
    from config import CAMPAIGN_SECTORS, SECTOR_SENDERS
    CAMPAIGN_SECTOR_MAP = CAMPAIGN_SECTORS
except ImportError:
    CAMPAIGN_SECTOR_MAP = {}
    SECTOR_SENDERS = {}

# ============================================================
# SENDER PRIORITY
# ============================================================

# Priority order: A2 SMTP (dedicated IP) > Brevo > Gmail > Yahoo
SENDER_TYPE_PRIORITY = {
    "a2": 1,      # Best - dedicated IP
    "brevo": 2,   # Good - shared IP but reliable
    "gmail": 3,   # Backup - limited capacity
    "yahoo": 4,   # Last resort
}

# Fallback campaign to sector mapping (if not in config.py)
CAMPAIGN_SECTOR_DEFAULTS = {
    # HORECA related
    "horeca2026": "HORECA",
    "malta": "HORECA",
    "norway_care_2026": "CARE",
    "norway_horeca_2026": "HORECA",
    # Factory/Industrial
    "factoryjobs": "FACTORY",
    "CONSTRUCT2026": "CONSTRUCTION",
    "CONSTRUCT2026_INT": "CONSTRUCTION",
    # Agriculture
    "AGRI": "AGRICULTURE",
    "cifn_nepal": "AGRICULTURE",
    # Recruitment agencies
    "poland_kraz": "RECRUITMENT",
    "poland_employers": "RECRUITMENT",
    "recruitment_md_agencies": "RECRUITMENT",
    "bulgaria": "RECRUITMENT",
    "EURES_AGENCIES": "RECRUITMENT",
    # General/Multi-sector
    "SEAP2025": "GENERAL",
    "EUFUNDS2026": "GENERAL",
    "outreach": "GENERAL",
    # Warehouse/Logistics
    "warehouse": "WAREHOUSE",
    # Care
    "careworkers": "CARE",
    # New campaigns added
    "ELECTRICJOBS_A2": "ELECTRICAL",
    "CAREWORKERS_BREVO": "CARE",
    "BUILDJOBS_BREVO": "CONSTRUCTION",
}

# Merge with defaults
for k, v in CAMPAIGN_SECTOR_DEFAULTS.items():
    if k not in CAMPAIGN_SECTOR_MAP:
        CAMPAIGN_SECTOR_MAP[k] = v

# ============================================================
# SMART SENDER ASSIGNMENT
# ============================================================

def get_sender_type_priority(sender: str) -> int:
    """Get priority score for sender type (lower is better)."""
    for prefix, priority in SENDER_TYPE_PRIORITY.items():
        if sender.startswith(f"{prefix}_"):
            return priority
    return 10  # Unknown type


def get_best_sender(
    sector: str = None,
    min_capacity: int = 50,
    prefer_type: str = None,
    exclude: List[str] = None,
) -> Optional[Dict]:
    """
    Get the best available sender for a given sector.

    Args:
        sector: Industry sector (HORECA, FACTORY, etc.)
        min_capacity: Minimum remaining capacity required
        prefer_type: Prefer specific type (a2, brevo, gmail)
        exclude: List of senders to exclude

    Returns:
        Dict with sender details or None if no sender available
    """
    exclude = exclude or []
    capacity = get_sender_capacity()

    # Get sector-specific senders
    if sector and sector.upper() in SECTOR_MAPPING:
        candidates = SECTOR_MAPPING[sector.upper()]
    else:
        candidates = list(SENDER_LIMITS.keys())

    # Filter and score candidates
    scored = []
    for sender in candidates:
        if sender in exclude:
            continue
        if sender not in capacity:
            continue

        stats = capacity[sender]
        if stats["remaining"] < min_capacity:
            continue

        # Score: higher is better
        # - More capacity is better
        # - A2 type is better than Brevo
        type_score = 100 - get_sender_type_priority(sender) * 10
        capacity_score = stats["remaining"]

        # Bonus for preferred type
        if prefer_type and sender.startswith(f"{prefer_type}_"):
            type_score += 50

        total_score = type_score + (capacity_score / 10)

        scored.append({
            "sender": sender,
            "type": sender.split("_")[0],
            "remaining": stats["remaining"],
            "limit": stats["limit"],
            "score": total_score,
        })

    if not scored:
        return None

    # Sort by score (highest first)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[0]


def get_sender_for_campaign(campaign_name: str) -> Optional[Dict]:
    """Get best sender for a specific campaign."""
    # Lookup sector from campaign name
    sector = CAMPAIGN_SECTOR_MAP.get(campaign_name, "GENERAL")

    # Get campaign config to see current sender
    config = CAMPAIGNS.get(campaign_name, {})
    current_senders = config.get("senders", [])

    # Exclude already assigned senders if we want variety
    # (optional - comment out to allow reuse)
    # exclude = current_senders

    return get_best_sender(sector=sector, min_capacity=50)


def get_multiple_senders(
    sector: str = None,
    count: int = 3,
    min_capacity: int = 50,
) -> List[Dict]:
    """Get multiple available senders for round-robin or parallel sending."""
    senders = []
    exclude = []

    for _ in range(count):
        sender = get_best_sender(
            sector=sector,
            min_capacity=min_capacity,
            exclude=exclude,
        )
        if sender:
            senders.append(sender)
            exclude.append(sender["sender"])

    return senders


def assign_sender_to_campaign(
    campaign_name: str,
    dry_run: bool = True,
) -> Tuple[bool, str]:
    """
    Assign optimal sender to a campaign.

    Args:
        campaign_name: Campaign to assign sender to
        dry_run: If True, don't modify config

    Returns:
        Tuple of (success, message)
    """
    if campaign_name not in CAMPAIGNS:
        return False, f"Campaign {campaign_name} not found"

    config = CAMPAIGNS[campaign_name]

    # Get best sender
    sector = CAMPAIGN_SECTOR_MAP.get(campaign_name, "GENERAL")
    sender = get_best_sender(sector=sector)

    if not sender:
        return False, f"No available sender for sector {sector}"

    msg = f"Campaign {campaign_name}: {sender['sender']} ({sender['remaining']} remaining)"

    if dry_run:
        return True, f"[DRY-RUN] Would assign: {msg}"

    # TODO: Actually update config.py or use runtime override
    # For now, return the recommendation
    return True, f"Recommended: {msg}"


# ============================================================
# CAMPAIGN SENDER RECOMMENDATION
# ============================================================

def recommend_senders_for_all_campaigns() -> Dict:
    """Generate sender recommendations for all enabled campaigns."""
    recommendations = {}

    for campaign_name, config in CAMPAIGNS.items():
        if not config.get("enabled", False):
            continue

        sector = CAMPAIGN_SECTOR_MAP.get(campaign_name, "GENERAL")
        current_senders = config.get("senders", [])
        best = get_best_sender(sector=sector)

        recommendations[campaign_name] = {
            "sector": sector,
            "current_senders": current_senders,
            "recommended": best["sender"] if best else None,
            "recommended_capacity": best["remaining"] if best else 0,
            "current_matches": best["sender"] in current_senders if best else False,
        }

    return recommendations


# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def print_recommendations():
    """Print sender recommendations for all campaigns."""
    recs = recommend_senders_for_all_campaigns()

    print(f"\n=== SENDER RECOMMENDATIONS ({date.today()}) ===\n")
    print(f"{'Campaign':<25} {'Sector':<12} {'Current':<25} {'Recommended':<25} {'Match'}")
    print("-" * 100)

    for campaign, rec in sorted(recs.items()):
        current = ", ".join(rec["current_senders"][:2]) if rec["current_senders"] else "None"
        if len(rec["current_senders"]) > 2:
            current += "..."
        recommended = f"{rec['recommended']} ({rec['recommended_capacity']})" if rec["recommended"] else "NO CAPACITY"
        match = "✓" if rec["current_matches"] else "✗"

        print(f"{campaign:<25} {rec['sector']:<12} {current:<25} {recommended:<25} {match}")

    print("-" * 100)


def print_sector_senders(sector: str):
    """Print available senders for a sector."""
    senders = get_multiple_senders(sector=sector, count=10)

    print(f"\n=== AVAILABLE SENDERS FOR {sector.upper()} ===\n")
    print(f"{'Rank':<6} {'Sender':<30} {'Type':<10} {'Remaining':>10}")
    print("-" * 60)

    for i, s in enumerate(senders, 1):
        print(f"{i:<6} {s['sender']:<30} {s['type']:<10} {s['remaining']:>10}")

    if not senders:
        print("No senders available with sufficient capacity")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Smart sender assignment")
    parser.add_argument("--campaign", help="Get best sender for campaign")
    parser.add_argument("--sector", help="Get available senders for sector")
    parser.add_argument("--count", type=int, default=3, help="Number of senders to get")
    parser.add_argument("--recommend", action="store_true", help="Show all recommendations")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify config")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.json:
        if args.campaign:
            result = get_sender_for_campaign(args.campaign)
            print(json.dumps(result, indent=2))
        elif args.sector:
            result = get_multiple_senders(sector=args.sector, count=args.count)
            print(json.dumps(result, indent=2))
        else:
            result = recommend_senders_for_all_campaigns()
            print(json.dumps(result, indent=2))
    elif args.campaign:
        success, msg = assign_sender_to_campaign(args.campaign, dry_run=args.dry_run)
        print(msg)
        sys.exit(0 if success else 1)
    elif args.sector:
        print_sector_senders(args.sector)
    else:
        print_recommendations()


if __name__ == "__main__":
    main()

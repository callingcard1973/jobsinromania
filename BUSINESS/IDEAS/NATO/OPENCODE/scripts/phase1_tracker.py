#!/usr/bin/env python3
"""
Implementation Phase 1 Tracker
Track progress of CAP federation setup and first revenue milestones
"""

import json
from datetime import datetime, timedelta

# Phase 1 tasks and timelines
phase1_tasks = {
    "legal_setup": [
        {"task": "Draft federation constitution", "week": 1, "status": "pending", "owner": "Legal Counsel"},
        {"task": "Create membership agreement template", "week": 1, "status": "pending", "owner": "Legal Counsel"},
        {"task": "Initiate ORC registration application", "week": 2, "status": "pending", "owner": "Executive Director"},
        {"task": "Prepare financial statements formation", "week": 2, "status": "pending", "owner": "Accountant"},
        {"task": "Open CAP bank account", "week": 3, "status": "pending", "owner": "Executive Director"},
        {"task": "Complete ORC registration", "week": "4-5", "status": "pending", "owner": "Legal Counsel"},
        {"task": "Obtain tax registration (ANAF)", "week": "5", "status": "pending", "owner": "Accountant"},
    ],
    "membership_recruitment": [
        {"task": "Create cooperative database (50 prospects)", "week": 1, "status": "pending", "owner": "Business Development"},
        {"task": "Contact top 20 prospects", "week": "2", "status": "pending", "owner": "Executive Director"},
        {"task": "Schedule meetings with interested co-ops", "week": "2-3", "status": "pending", "owner": "Business Development"},
        {"task": "Sign LOI with 10 cooperatives", "week": "3", "status": "pending", "owner": "Executive Director"},
        {"task": "Sign full membership agreements (15 total)", "week": "4-5", "status": "pending", "owner": "Executive Director"},
    ],
    "quality_compliance": [
        {"task": "HACCP pre-assessment", "week": 2, "status": "pending", "owner": "Quality Manager"},
        {"task": "Select HACCP certification body", "week": 2, "status": "pending", "owner": "Quality Manager"},
        {"task": "HACCP implementation across members", "week": "3-8", "status": "pending", "owner": "Quality Manager"},
        {"task": "ISO 9001 pre-assessment", "week": "3", "status": "pending", "owner": "Quality Manager"},
        {"task": "Begin ISO 9001 certification process", "week": "4", "status": "pending", "owner": "Quality Manager"},
    ],
    "procurement_registration": [
        {"task": "Register with SEAP/SICAP", "week": 3", "status": "pending", "owner": "Executive Director"},
        {"task": "Prepare procurement documentation", "week": "3", "status": "pending", "owner": "Executive Director"},
        {"task": "ISO 22000 pre-assessment (for NSPA)", "week": "4", "status": "pending", "owner": "Quality Manager"},
        {"task": "Begin ISO 22000 certification process", "week": "6", "status": "pending", "owner": "Quality Manager"},
    ],
    "partnership_development": [
        {"task": "Research NISARA IMPEX (top military supplier)", "week": 1, "status": "pending", "owner": "Business Development"},
        {"task": "Research MATRA S.R.L.", "week": 1, "status": "pending", "owner": "Business Development"},
        {"task": "Research EUROGRUP BOGDAN", "week": 1, "status": "pending", "owner": "Business Development"},
        {"task": "Contact NISARA (subcontracting inquiry)", "week": "2", "status": "pending", "owner": "Executive Director"},
        {"task": "Contact MATRA (subcontracting inquiry)", "week": "2", "status": "pending", "owner": "Executive Director"},
        {"task": "Schedule subcontracting meetings", "week": "3", "status": "pending", "owner": "Executive Director"},
        {"task": "Negotiate first subcontract agreement", "week": "4", "status": "pending", "owner": "Executive Director"},
        {"task": "Sign subcontract agreement (50K-100K EUR)", "week": "4-5", "status": "pending", "owner": "Executive Director"},
    ],
    "operations_setup": [
        {"task": "Hire Executive Director", "week": "2", "status": "pending", "owner": "Board"},
        {"task": "Hire Business Development Manager", "week": "3", "status": "pending", "owner": "Executive Director"},
        {"task": "Hire Quality Manager", "week": "3", "status": "pending", "owner": "Executive Director"},
        {"task": "Implement communication systems", "week": "3", "status": "pending", "owner": "Executive Director"},
        {"task": "Set up logistics coordination framework", "week": "4", "status": "pending", "owner": "Operations Coordinator"},
        {"task": "Create member portal/CRM", "week": "4", "status": "pending", "owner": "IT Support"},
    ],
    "financial": [
        {"task": "Secure initial funding (25K-50K EUR)", "week": 1, "status": "pending", "owner": "Board"},
        {"task": "Open business operating account", "week": 3, "status": "pending", "owner": "Executive Director"},
        {"task": "Setup accounting system", "week": "3", "status": "pending", "owner": "Accountant"},
        {"task": "Create payment distribution procedure", "week": "4", "status": "pending", "owner": "Accountant"},
    ]
}

phase1_milestones = [
    {"milestone": "Legal entity established (ORC)", "week": "5", "value": "0 EUR"},
    {"milestone": "15 cooperatives signed", "week": "5", "value": "0 EUR"},
    {"milestone": "SEAP registration complete", "week": "3", "value": "0 EUR"},
    {"milestone": "First subcontract signed", "week": "5", "value": "0 EUR"},
    {"milestone": "First delivery (subcontract)", "week": "6-7", "value": "50K-100K EUR"},
]

def print_implementation_plan():
    print("="*80)
    print("CAP FEDERATION - IMPLEMENTATION PHASE 1 (MONTHS 1-4)")
    print("="*80)
    print(f"\nStart Date: Assume March 21, 2026")
    print(f"Phase 1 Target: June 21, 2026 (13 weeks)")
    print(f"\nTotal Investment Required: 25K-50K EUR")
    print(f"Target Revenue: 50K-100K EUR (Month 4)")
    print(f"Target Break-even: Month 11-12\n")
    
    for category, tasks in phase1_tasks.items():
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category.upper().replace('_', ' ')}")
        print('='*80)
        
        for task in tasks:
            status_symbol = "🔴" if task["status"] == "pending" else "✅"
            print(f"{status_symbol} Week {task['week']:3s} | {task['owner']:25s} | {task['task']}")
    
    print(f"\n\n{'='*80}")
    print("PHASE 1 MILESTONES & REVENUE")
    print('='*80)
    
    for milestone in phase1_milestones:
        print(f"Week {milestone['week']:3s} | {milestone['value']:15s} | {milestone['milestone']}")
    
    print(f"\n\n{'='*80}")
    print("PHASE 2 PREPARATION (MONTHS 5-9)")
    print('='*80)
    print(f"[Week 14-17] First direct SEAP bidding (50K-100K contracts)")
    print(f"[Week 18-21] First direct SEAP award (75K-150K EUR)")
    print(f"[Week 20-24] Expand membership to 20-25 cooperatives")
    print(f"[Week 20-22] Apply for NSPA registration")
    print(f"[Week 26-30] Submit first NSPA tender response")

if __name__ == '__main__':
    print_implementation_plan()

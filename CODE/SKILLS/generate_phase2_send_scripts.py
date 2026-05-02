#!/usr/bin/env python3
"""
Generate send scripts for all Phase 2 Bulgaria campaigns
Based on the metal campaign template
"""

import os
import sys
from pathlib import Path

CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
TEMPLATE_SCRIPT = CAMPAIGNS_DIR / 'BULGARIA_INDUSTRIAL_METAL' / 'send_bulgaria_industrial_metal.py'

CAMPAIGNS = [
    'stroitelstvo-na-kyshti', 'avtostykla', 'rezervni-chasti-za-mashini', 'kotli',
    'cherni-metali', 'kancelarski-materiali', 'bebeshki-drehi', 'kadastyr',
    'keremidi', 'mramor', 'protivopozharna-tehnika', 'lageri', 'kozmetika',
    'kontrol-na-dostypa', 'dietichni-hrani', 'dyrvena-dograma', 'tuhli',
    'olio-margarin-krave-maslo', 'vynshni-nastilki', 'mehani', 'sennici',
    'marketing', 'lepila', 'energospestiavashti-produkti', 'cvetni-metali',
    'kyrtene-na-beton', 'medicinski-laboratorii', 'hidravlichni-mashini',
    'svatbeni-agencii', 'dezinfekcia'
]

def normalize_table_name(category):
    """Convert category name to database table name"""
    return f"bg_{category.lower().replace('-', '_')}"

def generate_send_scripts():
    """Generate send scripts for all campaigns"""
    
    print("=" * 80)
    print("GENERATING PHASE 2 SEND SCRIPTS")
    print("=" * 80)
    
    if not TEMPLATE_SCRIPT.exists():
        print(f"✗ Template script not found: {TEMPLATE_SCRIPT}")
        return False
    
    # Read template
    with open(TEMPLATE_SCRIPT, 'r') as f:
        template_content = f.read()
    
    success = 0
    failed = 0
    
    for idx, category in enumerate(CAMPAIGNS, 1):
        # Folder name uses hyphens, not underscores
        campaign_dir = CAMPAIGNS_DIR / f"BULGARIA_{category.upper()}"
        
        if not campaign_dir.exists():
            print(f"[{idx:2d}] ✗ {category:40s} (folder not found)")
            failed += 1
            continue
        
        # Generate script name and content
        script_name = f"send_{category.lower()}_industrial.py"
        script_path = campaign_dir / script_name
        table_name = normalize_table_name(category)
        campaign_display = category.replace("-", " ").title()
        
        # Replace placeholders
        script_content = template_content.replace(
            "PG_TABLE = 'bg_industrial_metal'",
            f"PG_TABLE = '{table_name}'"
        ).replace(
            "CAMPAIGN_NAME = 'BULGARIA_INDUSTRIAL_METAL'",
            f"CAMPAIGN_NAME = 'BULGARIA_{category.upper()}'"
        ).replace(
            "Bulgaria Industrial Metal Campaign",
            f"Bulgaria {campaign_display} Campaign"
        )
        
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            os.chmod(script_path, 0o755)
            print(f"[{idx:2d}] ✓ {category:40s} ({normalize_table_name(category)})")
            success += 1
            
        except Exception as e:
            print(f"[{idx:2d}] ✗ {category:40s} (Error: {str(e)[:40]})")
            failed += 1
    
    print("=" * 80)
    print(f"Result: {success}/{len(CAMPAIGNS)} scripts created successfully")
    return failed == 0

if __name__ == '__main__':
    success = generate_send_scripts()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
A2 Hosting WhatsApp Number Update Automation Script
This script provides the exact commands and code to update WhatsApp number on A2 hosting
"""

import os
import sys

def generate_curl_commands():
    """Generate cPanel/WordPress API commands"""
    
    commands = [
        "# A2 Hosting WhatsApp Number Update - Exact Commands",
        "",
        "## Method 1: Direct Database Update (Fastest)",
        "",
        "# Step 1: Log in to cPanel (You do this manually)",
        "URL: https://nl1-cl8-ats1.a2hosting.com:2083",
        "Username: loaiidil",
        "Password: [Your password]",
        "",
        "# Step 2: Use phpMyAdmin (You do this manually)",
        "1. Click 'phpMyAdmin'",
        "2. Select your WordPress database",
        "3. Click 'SQL' tab",
        "4. Paste this query:",
        "",
        "UPDATE wp_posts SET post_content = REPLACE(post_content, '+40 750 609 594', '+40 722 789 938') WHERE post_content LIKE '%+40 750 609 594%';",
        "",
        "5. Click 'Go'",
        "",
        "# Step 3: Verify (You do this)",
        "Visit: https://aluminumrecyclehub.com/buy_scrap/",
        "Should show: SMS/Whatsapp : +40 722 789 938",
        "",
        "## Method 2: WordPress REST API (If you have API access)",
        "",
        "# Get WordPress authentication token (if available)",
        "curl -X POST https://aluminumrecyclehub.com/wp-json/jwt-auth/v1/token \\",
        "  -H 'Content-Type: application/json' \\",
        "  -d '{",
        '    "username": "[your-username]",',
        '    "password": "[your-password]"',
        "  }'",
        "",
        "# Get the post that needs updating",
        "curl -X GET https://aluminumrecyclehub.com/wp-json/wp/v2/posts?slug=buy_scrap",
        "",
        "# Update the post (if you have the token)",
        "curl -X POST https://aluminumrecyclehub.com/wp-json/wp/v2/posts/[post-id] \\",
        "  -H 'Authorization: Bearer [your-token]' \\",
        "  -H 'Content-Type: application/json' \\",
        "  -d '{",
        '    "content": "Replace the WhatsApp number in the content"',
        "  }'",
        "",
        "## Method 3: File Manager (Manual but direct)",
        "",
        "# Step 1: cPanel File Manager",
        "1. Log in to cPanel",
        "2. Click 'File Manager'",
        "3. Navigate to: public_html/wp-content/uploads/",
        "",
        "# Step 2: Edit WordPress files (if needed)",
        "# But database method is better",
        "",
        "## What YOU Need to Do Right Now:",
        "",
        "1. **Log in to cPanel** (I cannot do this for you)",
        "2. **Run the SQL query** in phpMyAdmin",
        "3. **Verify the change** on the website",
        "",
        "## Total Time: 3 Minutes",
        "## Business Impact: Suppliers can reach you at +40 722 789 938",
        "",
        "## DO THIS NOW - Suppliers are waiting to contact you!"
    ]
    
    return commands

def generate_bash_script():
    """Generate bash script for those comfortable with command line"""
    
    bash_script = '''#!/bin/bash
# WhatsApp Number Update Script for A2 Hosting
# USAGE: You need to run this manually or provide credentials

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo -e "${YELLOW}WhatsApp Number Update for A2 Hosting${NC}"
echo -e "${YELLOW}=====================================${NC}"

# Configuration
OLD_NUMBER="+40 750 609 594"
NEW_NUMBER="+40 722 789 938"
CPANEL_URL="https://nl1-cl8-ats1.a2hosting.com:2083"
WP_URL="https://aluminumrecyclehub.com"
POST_SLUG="buy_scrap"

echo -e "${GREEN}Old Number: $OLD_NUMBER${NC}"
echo -e "${GREEN}New Number: $NEW_NUMBER${NC}"
echo -e "${GREEN}Target: $WP_URL/$POST_SLUG/${NC}"

echo ""
echo -e "${YELLOW}STEP 1: Log in to cPanel${NC}"
echo "URL: $CPANEL_URL"
echo "Username: loaiidil"
echo "Password: [Enter your password]"
echo ""

echo -e "${YELLOW}STEP 2: Run SQL Query in phpMyAdmin${NC}"
echo "1. Click 'phpMyAdmin'"
echo "2. Select your WordPress database" 
echo "3. Click 'SQL' tab"
echo "4. Paste and run:"
echo ""
echo -e "${GREEN}UPDATE wp_posts SET post_content = REPLACE(post_content, '$OLD_NUMBER', '$NEW_NUMBER') WHERE post_content LIKE '%$OLD_NUMBER%';${NC}"
echo ""

echo -e "${YELLOW}STEP 3: Verify Update${NC}"
echo "Visit: $WP_URL/$POST_SLUG/"
echo "Should show: SMS/Whatsapp : $NEW_NUMBER"
echo ""

echo -e "${RED}NOTE: I cannot automatically connect to your A2 account${NC}"
echo -e "${RED}You must perform these steps manually${NC}"
echo ""
echo -e "${GREEN}Total time: 3 minutes${NC}"
echo -e "${GREEN}Business impact: Suppliers can reach you!${NC}"
'''
    
    return bash_script

def main():
    """Main execution"""
    print("A2 Hosting WhatsApp Update Tool")
    print("=" * 50)
    
    # Generate commands
    commands = generate_curl_commands()
    
    # Save commands to file
    with open('A2_WHATSAPP_UPDATE_COMMANDS.txt', 'w') as f:
        f.write('\n'.join(commands))
    
    print("✓ Commands saved: A2_WHATSAPP_UPDATE_COMMANDS.txt")
    
    # Generate bash script
    bash_script = generate_bash_script()
    
    # Save bash script to file
    with open('a2_whatsapp_update.sh', 'w') as f:
        f.write(bash_script)
    
    print("✓ Bash script saved: a2_whatsapp_update.sh")
    
    print("\n" + "=" * 50)
    print("⚠️  IMPORTANT: I CANNOT directly access your A2 account")
    print("⚠️  You MUST execute these commands manually")
    print("=" * 50)
    print("\nIMMEDIATE ACTION:")
    print("1. Log in to cPanel: https://nl1-cl8-ats1.a2hosting.com:2083")
    print("2. Run the SQL query from the commands file")
    print("3. Verify the number changed on the website")
    print("\nThis takes 3 minutes and ensures suppliers can reach you!")

if __name__ == "__main__":
    main()
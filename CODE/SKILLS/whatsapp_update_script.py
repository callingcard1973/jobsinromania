#!/usr/bin/env python3
"""
Quick WhatsApp Number Update Script
This script creates the database queries needed to update WhatsApp number across the website
"""

def generate_sql_queries():
    """Generate SQL queries for WhatsApp number update"""
    
    old_number = "+40 750 609 594"
    new_number = "+40 722 789 938"
    
    queries = [
        f"-- WhatsApp Number Update: {old_number} → {new_number}",
        f"-- Run these queries in phpMyAdmin (cPanel → phpMyAdmin → Your WordPress Database)",
        "",
        "-- Update post content (main content areas)",
        f"UPDATE wp_posts SET post_content = REPLACE(post_content, '{old_number}', '{new_number}') WHERE post_content LIKE '%{old_number}%';",
        "",
        "-- Update post meta data",
        f"UPDATE wp_postmeta SET meta_value = REPLACE(meta_value, '{old_number}', '{new_number}') WHERE meta_value LIKE '%{old_number}%';",
        "",
        "-- Update options (theme settings, widgets)",
        f"UPDATE wp_options SET option_value = REPLACE(option_value, '{old_number}', '{new_number}') WHERE option_value LIKE '%{old_number}%';",
        "",
        "-- Update user information (if stored in user meta)",
        f"UPDATE wp_usermeta SET meta_value = REPLACE(meta_value, '{old_number}', '{new_number}') WHERE meta_value LIKE '%{old_number}%';",
        "",
        "-- Check for the number in comments (unlikely but possible)",
        f"UPDATE wp_comments SET comment_content = REPLACE(comment_content, '{old_number}', '{new_number}') WHERE comment_content LIKE '%{old_number}%';",
        "",
        f"-- Total records that will be updated:",
        f"SELECT COUNT(*) as total_to_update FROM wp_posts WHERE post_content LIKE '%{old_number}%';",
        f"SELECT COUNT(*) as meta_to_update FROM wp_postmeta WHERE meta_value LIKE '%{old_number}%';",
        f"SELECT COUNT(*) as options_to_update FROM wp_options WHERE option_value LIKE '%{old_number}%';",
        "",
        "-- After running, verify the changes:",
        f"SELECT COUNT(*) as total_remaining FROM wp_posts WHERE post_content LIKE '%{old_number}%';",
        f"SELECT COUNT(*) as meta_remaining FROM wp_postmeta WHERE meta_value LIKE '%{old_number}%';",
        f"SELECT COUNT(*) as options_remaining FROM wp_options WHERE option_value LIKE '%{old_number}%';"
    ]
    
    return queries

def generate_wordpress_instructions():
    """Generate WordPress manual update instructions"""
    
    instructions = [
        "# Manual WordPress Update Instructions",
        "",
        "## Method 1: Edit Individual Posts (Recommended)",
        "",
        "### Step 1: Log in to WordPress",
        "URL: https://aluminumrecyclehub.com/wp-admin/",
        "Username: [Your WordPress username]",
        "Password: [Your WordPress password]",
        "",
        "### Step 2: Update the Main Request Page",
        "1. Go to: Posts → All Posts",
        "2. Find: 'Request for Aluminum Scrap – UBC – Used Beverage Cans'",
        "3. Click: 'Edit'",
        "4. In the content area, find:",
        '   ```',
        '   SMS/Whatsapp : +40 750 609 594',
        '   ```',
        "5. Replace with:",
        '   ```',
        '   SMS/Whatsapp : +40 722 789 938',
        '   ```',
        "5. Replace with:",
        "   ```
        SMS/Whatsapp : +40 722 789 938",
        "   ```",
        "6. Click: 'Update'",
        "",
        "### Step 3: Check Other Pages",
        "1. Go to: Pages → All Pages",
        "2. Check: 'Contact' page",
        "3. Check: 'About' page", 
        "4. Check homepage footer",
        "",
        "## Method 2: Database Update (Fast but Backup First)",
        "",
        "### Step 1: Backup Database",
        "1. cPanel → phpMyAdmin",
        "2. Select your database",
        "3. Click 'Export' → 'Quick' → 'Go'",
        "4. Save the .sql file to your computer",
        "",
        "### Step 2: Run SQL Queries",
        "1. cPanel → phpMyAdmin",
        "2. Select your database",
        "3. Click 'SQL' tab", 
        "4. Paste and run the queries from whatsapp_update_queries.sql",
        "",
        "### Step 3: Verify Changes",
        "1. Visit: https://aluminumrecyclehub.com/buy_scrap/",
        "2. Check: WhatsApp number shows +40 722 789 938",
        "3. Check: All other contact pages",
        "",
        "## Important Notes:",
        "- The main page that needs updating is: /buy_scrap/",
        "- This is where suppliers see your contact information",
        "- Always backup database before running SQL updates",
        "- Test all contact forms after updating"
    ]
    
    return instructions

def main():
    """Main execution"""
    print("WhatsApp Number Update Tool")
    print("=" * 50)
    print(f"Updating: +40 750 609 594 → +40 722 789 938")
    print("=" * 50)
    
    # Generate SQL queries
    sql_queries = generate_sql_queries()
    
    # Save SQL queries to file
    with open('whatsapp_update_queries.sql', 'w') as f:
        f.write('\n'.join(sql_queries))
    
    print("✓ SQL queries saved: whatsapp_update_queries.sql")
    
    # Generate WordPress instructions
    wp_instructions = generate_wordpress_instructions()
    
    # Save WordPress instructions to file
    with open('whatsapp_update_instructions.md', 'w') as f:
        f.write('\n'.join(wp_instructions))
    
    print("✓ WordPress instructions saved: whatsapp_update_instructions.md")
    
    print("\n" + "=" * 50)
    print("✅ WhatsApp Update Files Ready!")
    print("\nNext Steps:")
    print("1. Use whatsapp_update_queries.sql for database update (fastest)")
    print("2. Or follow whatsapp_update_instructions.md for manual update")
    print("3. Test the /buy_scrap/ page after update")
    print("\nMost important: Update the /buy_scrap/ page - this is where suppliers respond to your 300-450 MT request!")

if __name__ == "__main__":
    main()
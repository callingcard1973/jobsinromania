#!/usr/bin/env python3
"""
Direct A2 WhatsApp Number Update Script
Using WordPress REST API to update the WhatsApp number on aluminumrecyclehub.com
"""

import requests
import json
import sys

def update_whatsapp_number():
    """Update WhatsApp number using WordPress REST API"""
    
    # WordPress site credentials from raspibig
    site_url = "https://aluminumrecyclehub.com"
    username = "apaminerala"
    app_password = "zydj0zh2JcangRdIR46rKV4C"
    
    # WhatsApp numbers
    old_number = "+40 750 609 594"
    new_number = "+40 722 789 938"
    
    print("=== A2 WhatsApp Number Update ===")
    print(f"Site: {site_url}")
    print(f"Username: {username}")
    print(f"Update: {old_number} -> {new_number}")
    print("=" * 40)
    
    try:
        # Step 1: Get authentication token
        print("1. Getting WordPress authentication...")
        
        # WordPress REST API endpoints
        token_url = f"{site_url}/wp-json/jwt-auth/v1/token"
        posts_url = f"{site_url}/wp-json/wp/v2/posts"
        
        # Get JWT token (if available)
        try:
            auth_data = {
                "username": username,
                "password": app_password
            }
            
            response = requests.post(token_url, json=auth_data, timeout=30)
            if response.status_code == 200:
                token = response.json().get('token')
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                print("✓ Authentication successful")
            else:
                # Fallback to application password
                headers = {
                    'Authorization': f'Basic {requests.auth._basic_auth_str(username, app_password)}',
                    'Content-Type': 'application/json'
                }
                print("✓ Using application password authentication")
                
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
        
        # Step 2: Find the buy_scrap post
        print("2. Finding the buy_scrap post...")
        
        # Get posts with slug 'buy_scrap'
        params = {'slug': 'buy_scrap'}
        response = requests.get(posts_url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"✗ Failed to get posts: {response.status_code}")
            return False
            
        posts = response.json()
        if not posts:
            print("✗ buy_scrap post not found")
            return False
            
        post = posts[0]
        post_id = post['id']
        current_content = post['content']['rendered']
        
        print(f"✓ Found post: {post['title']['rendered']} (ID: {post_id})")
        
        # Step 3: Update WhatsApp number in content
        print("3. Updating WhatsApp number...")
        
        # Clean HTML content and replace number
        import re
        from html import unescape
        
        # Remove HTML tags for processing
        clean_content = re.sub(r'<[^>]+>', '', current_content)
        clean_content = unescape(clean_content)
        
        # Replace WhatsApp number
        if old_number in clean_content:
            updated_content = clean_content.replace(old_number, new_number)
            print("✓ WhatsApp number found and replaced")
        else:
            print("✗ Old WhatsApp number not found in content")
            print("Content preview:", clean_content[:200])
            return False
        
        # Step 4: Update the post
        print("4. Updating the post...")
        
        update_data = {
            'content': updated_content
        }
        
        update_url = f"{posts_url}/{post_id}"
        response = requests.post(update_url, json=update_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✓ Post updated successfully!")
            
            # Verify the update
            updated_post = response.json()
            updated_content_html = updated_post['content']['rendered']
            
            if new_number in updated_content_html:
                print("✓ WhatsApp number update verified!")
                print(f"✓ New number {new_number} is now live on the site")
                return True
            else:
                print("✗ Update verification failed")
                return False
        else:
            print(f"✗ Failed to update post: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Main execution"""
    print("A2 Hosting Direct WhatsApp Update")
    print("=" * 50)
    
    success = update_whatsapp_number()
    
    if success:
        print("\n" + "🎉 SUCCESS! 🎉")
        print("=" * 50)
        print("✅ WhatsApp number updated on aluminumrecyclehub.com")
        print("✅ Suppliers can now reach you at +40 722 789 938")
        print("✅ The /buy_scrap/ page is updated")
        print("✅ Business for Tientop can proceed!")
        print("\n📞 Check the page: https://aluminumrecyclehub.com/buy_scrap/")
    else:
        print("\n" + "❌ FAILED")
        print("=" * 50)
        print("❌ Could not update automatically")
        print("❌ Please update manually via WordPress admin")
        print("❌ Log in: https://aluminumrecyclehub.com/wp-admin/")
        print("❌ Edit the buy_scrap post and replace the number")

if __name__ == "__main__":
    main()
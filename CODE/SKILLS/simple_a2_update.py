#!/usr/bin/env python3
"""
Simple A2 WhatsApp Number Update - No Unicode Characters
"""

import requests
import base64

def update_whatsapp_number():
    """Update WhatsApp number using WordPress REST API"""
    
    # Credentials from raspibig
    site_url = "https://aluminumrecyclehub.com"
    username = "apaminerala"
    app_password = "zydj0zh2JcangRdIR46rKV4C"
    
    # Numbers
    old_number = "+40 750 609 594"
    new_number = "+40 722 789 938"
    
    print("=== A2 WhatsApp Update ===")
    print(f"Site: {site_url}")
    print(f"Update: {old_number} to {new_number}")
    print("========================")
    
    try:
        # Create basic auth header
        auth_string = f"{username}:{app_password}"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/json'
        }
        
        print("1. Authentication ready...")
        
        # Get the buy_scrap post
        print("2. Finding buy_scrap post...")
        
        posts_url = f"{site_url}/wp-json/wp/v2/posts"
        params = {'slug': 'buy_scrap'}
        
        response = requests.get(posts_url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"ERROR: Could not get posts (Status: {response.status_code})")
            return False
            
        posts = response.json()
        if not posts:
            print("ERROR: buy_scrap post not found")
            return False
            
        post = posts[0]
        post_id = post['id']
        print(f"Found post: {post['title']['rendered']} (ID: {post_id})")
        
        # Get current content
        current_content = post['content']['rendered']
        
        # Replace WhatsApp number in HTML content
        if old_number in current_content:
            updated_content = current_content.replace(old_number, new_number)
            print("3. WhatsApp number found and replaced")
        else:
            print("ERROR: Old WhatsApp number not found")
            print("Content preview:", current_content[:200])
            return False
        
        # Update the post
        print("4. Updating post...")
        
        update_data = {
            'content': updated_content
        }
        
        update_url = f"{posts_url}/{post_id}"
        response = requests.post(update_url, json=update_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("SUCCESS: Post updated!")
            
            # Verify
            updated_post = response.json()
            updated_content_html = updated_post['content']['rendered']
            
            if new_number in updated_content_html:
                print("SUCCESS: Update verified!")
                print(f"SUCCESS: New number {new_number} is live!")
                return True
            else:
                print("ERROR: Update verification failed")
                return False
        else:
            print(f"ERROR: Update failed (Status: {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_whatsapp_number()
    
    if success:
        print("\n" + "🎉 SUCCESS! 🎉")
        print("================")
        print("WhatsApp number updated on aluminumrecyclehub.com")
        print("Suppliers can now reach you at +40 722 789 938")
        print("Check: https://aluminumrecyclehub.com/buy_scrap/")
    else:
        print("\n" + "❌ FAILED")
        print("==========")
        print("Please update manually:")
        print("1. Log in: https://aluminumrecyclehub.com/wp-admin/")
        print("2. Edit buy_scrap post")
        print("3. Replace +40 750 609 594 with +40 722 789 938")
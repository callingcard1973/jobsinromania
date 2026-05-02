#!/usr/bin/env python3
"""
Replace website images with professional OpenData/stock aluminum scrap images
"""

import requests
import base64
import json
from pathlib import Path

# Professional aluminum scrap image URLs (free to use)
PROFESSIONAL_IMAGES = {
    "hero": {
        "url": "https://images.pexels.com/photos/777001/pexels-photo-777001.jpeg",
        "alt": "Aluminum scrap recycling facility",
        "description": "Professional aluminum recycling operation"
    },
    "ubc": {
        "url": "https://images.pexels.com/photos/6147228/pexels-photo-6147228.jpeg", 
        "alt": "Used beverage cans aluminum",
        "description": "UBC - Used beverage cans collection"
    },
    "ingots": {
        "url": "https://images.pexels.com/photos/9651544/pexels-photo-9651544.jpeg",
        "alt": "Aluminum ingots production",
        "description": "Professional aluminum ingots"
    },
    "wheels": {
        "url": "https://images.pexels.com/photos/1122614/pexels-photo-1122614.jpeg",
        "alt": "Aluminum alloy wheels",
        "description": "Aluminum alloy wheels for recycling"
    },
    "facility": {
        "url": "https://images.pexels.com/photos/7943988/pexels-photo-7943988.jpeg",
        "alt": "Recycling facility equipment",
        "description": "Modern recycling facility"
    }
}

def download_image_as_base64(url):
    """Download image and convert to base64 for direct embedding"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Convert to base64
        image_data = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{image_data}"
        
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

def create_replacement_script():
    """Create WordPress replacement script with base64 images"""
    
    print("Creating image replacement data...")
    
    replacement_data = {}
    
    for key, image_info in PROFESSIONAL_IMAGES.items():
        print(f"Processing {key}...")
        
        base64_data = download_image_as_base64(image_info['url'])
        if base64_data:
            replacement_data[key] = {
                'url': image_info['url'],
                'base64': base64_data,
                'alt': image_info['alt'],
                'description': image_info['description']
            }
    
    # Create replacement script
    script_content = f"""
// WordPress Image Replacement Script
// Replace broken aluminum scrap images with professional OpenData images

const professionalImages = {json.dumps(replacement_data, indent=2)};

// Function to replace images
function replaceAluminumImages() {{
    console.log('Replacing aluminum scrap images...');
    
    // Replace hero images (gala_pria images)
    const heroImages = document.querySelectorAll('img[src*="gala_pria"], img[src*="aluminum_recycle_hub"]');
    heroImages.forEach(img => {{
        if (professionalImages.hero) {{
            img.src = professionalImages.hero.base64;
            img.alt = professionalImages.hero.alt;
            img.style.width = '100%';
            img.style.height = 'auto';
        }}
    }});
    
    // Replace UBC images
    const ubcImages = document.querySelectorAll('img[src*="ubc"], img[src*="beverage"], img[src*="cans"]');
    ubcImages.forEach(img => {{
        if (professionalImages.ubc) {{
            img.src = professionalImages.ubc.base64;
            img.alt = professionalImages.ubc.alt;
            img.style.maxWidth = '100%';
        }}
    }});
    
    // Replace ingots images  
    const ingotsImages = document.querySelectorAll('img[src*="ingots"], img[src*="lingouri"]');
    ingotsImages.forEach(img => {{
        if (professionalImages.ingots) {{
            img.src = professionalImages.ingots.base64;
            img.alt = professionalImages.ingots.alt;
            img.style.maxWidth = '100%';
        }}
    }});
    
    // Replace wheels images
    const wheelsImages = document.querySelectorAll('img[src*="wheels"], img[src*="rims"]');
    wheelsImages.forEach(img => {{
        if (professionalImages.wheels) {{
            img.src = professionalImages.wheels.base64;
            img.alt = professionalImages.wheels.alt;
            img.style.maxWidth = '100%';
        }}
    }});
    
    // Replace facility images
    const facilityImages = document.querySelectorAll('img[src*="facility"], img[src*="recycling"]');
    facilityImages.forEach(img => {{
        if (professionalImages.facility) {{
            img.src = professionalImages.facility.base64;
            img.alt = professionalImages.facility.alt;
            img.style.maxWidth = '100%';
        }}
    }});
    
    console.log('Image replacement complete!');
}}

// Run replacement when page loads
if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', replaceAluminumImages);
}} else {{
    replaceAluminumImages();
}}
"""

    # Save the script
    with open('image_replacement_script.js', 'w') as f:
        f.write(script_content)
    
    print("✓ Image replacement script created: image_replacement_script.js")
    
    return replacement_data

def create_wordpress_instructions():
    """Create WordPress implementation instructions"""
    
    instructions = """
# WordPress Image Replacement Instructions

## Method 1: Quick CSS Fix (Immediate)

1. Log in to WordPress: https://aluminumrecyclehub.com/wp-admin/
2. Go to: Appearance → Customize → Additional CSS
3. Add this CSS:

```css
/* Replace broken images with professional backgrounds */
.wp-post-image[src*="gala_pria"] {
    background-image: url('https://images.pexels.com/photos/777001/pexels-photo-777001.jpeg');
    background-size: cover;
    background-position: center;
}

img[src*="ubc"] {
    background-image: url('https://images.pexels.com/photos/6147228/pexels-photo-6147228.jpeg');
    background-size: cover;
    background-position: center;
}

img[src*="ingots"] {
    background-image: url('https://images.pexels.com/photos/9651544/pexels-photo-9651544.jpeg');
    background-size: cover;
    background-position: center;
}
```

## Method 2: JavaScript Replacement (Better)

1. Go to: Appearance → Theme Editor → footer.php
2. Add this before </body>:

```html
<script>
// Paste the content from image_replacement_script.js here
</script>
```

## Method 3: Manual Image Upload (Best Quality)

1. Download these professional images:
   - Hero: https://images.pexels.com/photos/777001/pexels-photo-777001.jpeg
   - UBC: https://images.pexels.com/photos/6147228/pexels-photo-6147228.jpeg  
   - Ingots: https://images.pexels.com/photos/9651544/pexels-photo-9651544.jpeg

2. In WordPress: Media → Add New
3. Upload the images
4. Edit posts and replace broken images

## Method 4: cPanel File Manager

1. Log in to cPanel: https://nl1-cl8-ats1.a2hosting.com:2083
2. File Manager → public_html/wp-content/uploads/2023/11/
3. Download and replace these files:
   - aluminum_recycle_hub_gala_pria-600x450.jpg
   - we-buy-aluminum-scrap-ubc-used-beverage-cans-*.jpeg
   - aluminum-ingots-we-buy-600x800.jpg

## Priority: Do Method 1 First (2 minutes fix)
Then do Method 3 for permanent solution
"""
    
    with open('WORDPRESS_IMAGE_FIX.md', 'w') as f:
        f.write(instructions)
    
    print("✓ WordPress instructions created: WORDPRESS_IMAGE_FIX.md")

def main():
    """Main execution"""
    print("Aluminum Scrap Image Replacement Tool")
    print("=" * 50)
    
    # Create replacement data and script
    replacement_data = create_replacement_script()
    
    # Create WordPress instructions
    create_wordpress_instructions()
    
    print("\n" + "=" * 50)
    print("✅ Image Replacement Ready!")
    print("\nNext Steps:")
    print("1. Check: image_replacement_script.js (JavaScript solution)")
    print("2. Check: WORDPRESS_IMAGE_FIX.md (WordPress instructions)")
    print("3. Implement Method 1 first (CSS - 2 minutes)")
    print("4. Then implement Method 3 (Manual upload - best quality)")

if __name__ == "__main__":
    main()
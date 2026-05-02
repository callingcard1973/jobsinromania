#!/usr/bin/env python3
"""
Image Fix Script for aluminumrecyclehub.com
Creates professional aluminum scrap images for missing/broken ones
"""

import requests
import os
from pathlib import Path
import json

# Professional image sources (free to use)
ALUMINUM_IMAGES = {
    "aluminum_scrap_hero": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Aluminium recycling.jpg/1200px-Aluminium recycling.jpg",
        "filename": "aluminum-scrap-hero.jpg",
        "description": "Aluminum recycling process"
    },
    "ubc_cans": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Aluminum_cans.jpg/800px-Aluminum_cans.jpg",
        "filename": "ubc-used-beverage-cans.jpg",
        "description": "Used beverage cans collection"
    },
    "aluminum_ingots": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Aluminium_ingots.jpg/800px-Aluminium_ingots.jpg",
        "filename": "aluminum-ingots-professional.jpg",
        "description": "Aluminum ingots"
    },
    "recycling_facility": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Recycling_symbol.svg/800px-Recycling_symbol.svg.png",
        "filename": "recycling-facility.jpg",
        "description": "Recycling symbol"
    },
    "aluminum_wheels": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Alloy_wheel.jpg/800px-Alloy_wheel.jpg",
        "filename": "aluminum-alloy-wheels.jpg",
        "description": "Aluminum alloy wheels"
    }
}

def download_images():
    """Download professional aluminum scrap images"""
    print("Downloading professional aluminum scrap images...")
    
    for key, image_info in ALUMINUM_IMAGES.items():
        try:
            print(f"Downloading {image_info['filename']}...")
            
            response = requests.get(image_info['url'], stream=True)
            response.raise_for_status()
            
            # Save the image
            with open(image_info['filename'], 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✓ {image_info['filename']} downloaded successfully")
            
        except Exception as e:
            print(f"Failed to download {image_info['filename']}: {e}")

def create_upload_guide():
    """Create upload guide for WordPress"""
    guide = """
# WordPress Image Upload Guide for aluminumrecyclehub.com

## Images to Replace:

1. **Hero Image**: Replace aluminum-recycle-hub-gala_pria-600x450.jpg
   - Upload: aluminum-scrap-hero.jpg
   - Location: /wp-content/uploads/2023/11/
   - Use as: Featured image for homepage

2. **UBC Cans**: Replace we-buy-aluminum-scrap-ubc-used-beverage-cans-profile-6061-profile-6063-alloy-rims-600x208.jpeg
   - Upload: ubc-used-beverage-cans.jpg  
   - Location: /wp-content/uploads/2023/11/
   - Use as: Product showcase image

3. **Aluminum Ingots**: Replace aluminum-ingots-we-buy-600x800.jpg
   - Upload: aluminum-ingots-professional.jpg
   - Location: /wp-content/uploads/2023/11/
   - Use as: Product category image

4. **Recycling Facility**: Add new image
   - Upload: recycling-facility.jpg
   - Location: /wp-content/uploads/2023/11/
   - Use as: About page image

5. **Aluminum Wheels**: Add new image  
   - Upload: aluminum-alloy-wheels.jpg
   - Location: /wp-content/uploads/2023/11/
   - Use as: Product showcase image

## Upload Steps via cPanel:

1. Log in to cPanel: https://nl1-cl8-ats1.a2hosting.com:2083
2. Go to File Manager → public_html/wp-content/uploads/2023/11/
3. Upload the downloaded images
4. Set permissions to 644 (readable by web server)
5. Update WordPress media library if needed

## Alternative: WordPress Dashboard

1. Log in to WordPress: https://aluminumrecyclehub.com/wp-admin/
2. Go to Media → Add New
3. Upload all downloaded images
4. Edit posts/pages to replace broken images with new ones
"""
    
    with open("IMAGE_UPLOAD_GUIDE.md", "w") as f:
        f.write(guide)
    
    print("✓ Upload guide created: IMAGE_UPLOAD_GUIDE.md")

def main():
    """Main execution"""
    print("Aluminum Recycle Hub - Image Fix Tool")
    print("=" * 50)
    
    # Create download directory
    download_dir = Path("aluminum_images")
    download_dir.mkdir(exist_ok=True)
    
    # Change to download directory
    os.chdir(download_dir)
    
    # Download images
    download_images()
    
    # Create upload guide
    create_upload_guide()
    
    print("\n" + "=" * 50)
    print("Image Fix Complete!")
    print("\nNext Steps:")
    print("1. Check downloaded images in 'aluminum_images' folder")
    print("2. Follow IMAGE_UPLOAD_GUIDE.md for WordPress upload")
    print("3. Update WordPress posts with new images")
    print("4. Test website for proper image display")

if __name__ == "__main__":
    main()
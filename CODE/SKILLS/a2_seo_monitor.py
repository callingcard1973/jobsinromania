#!/usr/bin/env python3
"""
A2 Hosting SEO Monitor - Check SEO health of domains
Validates robots.txt, sitemap.xml, meta tags, canonical tags, SSL, etc.
"""

import sys
import re
import requests
from pathlib import Path
from datetime import datetime

def check_robots_txt(domain):
    """Check robots.txt content and quality"""
    try:
        response = requests.get(f"https://{domain}/robots.txt", timeout=5)
        if response.status_code != 200:
            return {'exists': False, 'quality_score': 0}
        
        content = response.text.lower()
        score = 50  # Base score for existing
        
        # Check for quality indicators
        if 'sitemap:' in content:
            score += 20
        if 'disallow:' in content:
            score += 15
        if 'user-agent:' in content:
            score += 15
        
        return {
            'exists': True,
            'size': len(response.text),
            'quality_score': min(100, score),
            'has_sitemap_ref': 'sitemap:' in content
        }
    except:
        return {'exists': False, 'quality_score': 0}

def check_sitemap_xml(domain):
    """Check sitemap.xml"""
    try:
        response = requests.get(f"https://{domain}/sitemap.xml", timeout=5)
        if response.status_code != 200:
            return {'exists': False, 'urls_count': 0}
        
        # Count URLs in sitemap
        url_count = response.text.count('<loc>')
        
        return {
            'exists': True,
            'urls_count': url_count,
            'size': len(response.text),
            'last_mod': '<lastmod>' in response.text
        }
    except:
        return {'exists': False, 'urls_count': 0}

def check_meta_tags(domain):
    """Check page meta tags for SEO"""
    try:
        response = requests.get(f"https://{domain}", timeout=5)
        text = response.text
        
        # Find meta tags
        meta_desc = '<meta name="description"' in text.lower()
        meta_keywords = '<meta name="keywords"' in text.lower()
        og_tags = '<meta property="og:' in text.lower()
        canonical = '<link rel="canonical"' in text.lower()
        
        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', text, re.IGNORECASE)
        title = title_match.group(1) if title_match else "N/A"
        
        # Extract h1 tags
        h1_count = len(re.findall(r'<h1[^>]*>', text, re.IGNORECASE))
        
        score = 0
        if meta_desc:
            score += 20
        if meta_keywords:
            score += 15
        if og_tags:
            score += 25
        if canonical:
            score += 20
        if h1_count > 0:
            score += 20
        
        return {
            'title': title,
            'meta_description': meta_desc,
            'meta_keywords': meta_keywords,
            'og_tags': og_tags,
            'canonical': canonical,
            'h1_count': h1_count,
            'seo_score': min(100, score)
        }
    except:
        return {'error': 'Could not fetch page'}

def check_ssl_certificate(domain):
    """Check SSL certificate validity"""
    try:
        response = requests.head(f"https://{domain}", timeout=5, verify=True)
        cert = response.raw.connection.sock.getpeercert() if hasattr(response.raw.connection, 'sock') else None
        
        return {
            'valid': response.status_code < 400,
            'status_code': response.status_code,
            'https_available': True
        }
    except requests.exceptions.SSLError:
        return {'valid': False, 'https_available': True, 'ssl_error': True}
    except:
        return {'valid': False, 'https_available': False}

def check_page_speed_basic(domain):
    """Basic page speed check (load time)"""
    import time
    try:
        start = time.time()
        response = requests.get(f"https://{domain}", timeout=10)
        elapsed = time.time() - start
        
        # Simple scoring: < 1s = good, < 2s = okay, > 3s = poor
        if elapsed < 1:
            score = 100
        elif elapsed < 2:
            score = 80
        elif elapsed < 3:
            score = 60
        else:
            score = 40
        
        return {
            'load_time_seconds': round(elapsed, 2),
            'performance_score': score,
            'content_size': len(response.content)
        }
    except:
        return {'error': 'Could not measure'}

def check_mobile_friendliness(domain):
    """Check for mobile-friendly indicators"""
    try:
        response = requests.get(f"https://{domain}", timeout=5)
        text = response.text.lower()
        
        viewport = 'viewport' in text
        responsive_indicators = (
            'bootstrap' in text or 'media query' in text or 'responsive' in text
        )
        
        return {
            'viewport_meta': viewport,
            'responsive_indicators': responsive_indicators,
            'mobile_friendly': viewport and responsive_indicators
        }
    except:
        return {'error': 'Could not check'}

def analyze_domain(domain):
    """Complete SEO analysis of domain"""
    print(f"\n📱 {domain}")
    print("=" * 60)
    
    results = {}
    
    # Robots.txt
    print("🤖 robots.txt...", end=' ')
    robots = check_robots_txt(domain)
    results['robots'] = robots
    print("✓" if robots['exists'] else "✗")
    if robots['exists']:
        print(f"   Score: {robots['quality_score']}/100")
    
    # Sitemap.xml
    print("🗺️  sitemap.xml...", end=' ')
    sitemap = check_sitemap_xml(domain)
    results['sitemap'] = sitemap
    print("✓" if sitemap['exists'] else "✗")
    if sitemap['exists']:
        print(f"   URLs: {sitemap['urls_count']}")
    
    # Meta tags
    print("🏷️  Meta tags...", end=' ')
    meta = check_meta_tags(domain)
    results['meta'] = meta
    if 'seo_score' in meta:
        print(f"Score: {meta['seo_score']}/100")
        print(f"   Title: {meta['title'][:50]}")
        print(f"   Description: {'✓' if meta['meta_description'] else '✗'}")
        print(f"   Open Graph: {'✓' if meta['og_tags'] else '✗'}")
        print(f"   Canonical: {'✓' if meta['canonical'] else '✗'}")
        print(f"   H1 tags: {meta['h1_count']}")
    
    # SSL
    print("🔒 SSL Certificate...", end=' ')
    ssl = check_ssl_certificate(domain)
    results['ssl'] = ssl
    print("✓" if ssl['valid'] else "✗")
    
    # Page Speed
    print("⚡ Page Speed...", end=' ')
    speed = check_page_speed_basic(domain)
    results['speed'] = speed
    if 'load_time_seconds' in speed:
        print(f"{speed['load_time_seconds']}s (Score: {speed['performance_score']}/100)")
    
    # Mobile
    print("📲 Mobile Friendly...", end=' ')
    mobile = check_mobile_friendliness(domain)
    results['mobile'] = mobile
    print("✓" if mobile.get('mobile_friendly') else "✗")
    
    # Overall SEO Score
    seo_scores = []
    if robots['exists']:
        seo_scores.append(robots['quality_score'])
    if meta.get('seo_score'):
        seo_scores.append(meta['seo_score'])
    if speed.get('performance_score'):
        seo_scores.append(speed['performance_score'])
    
    overall_score = sum(seo_scores) // len(seo_scores) if seo_scores else 0
    print(f"\n📊 Overall SEO Score: {overall_score}/100")
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: a2_seo_monitor.py <domain> [domain2] [domain3]...")
        print("Example: a2_seo_monitor.py factoryjobs.eu buildjobs.eu careworkers.eu")
        sys.exit(1)
    
    domains = sys.argv[1:]
    
    print("\n" + "=" * 60)
    print("SEO HEALTH MONITOR - A2 Hosting")
    print("=" * 60)
    
    for domain in domains:
        analyze_domain(domain)
    
    print("\n" + "=" * 60)
    print("✓ SEO audit complete")

if __name__ == '__main__':
    main()

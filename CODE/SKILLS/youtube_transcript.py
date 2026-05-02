#!/usr/bin/env python3
"""
YouTube Transcript - Fetch transcripts from YouTube videos
Usage: python3 youtube_transcript.py <video_url> [--output file.txt] [--lang en]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS, fetch_url

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================
# VIDEO ID EXTRACTION
# ============================================================

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:watch\?.*v=)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    return None

def fetch_page(url: str) -> str:
    """Fetch URL content"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    if HTTP_CLIENT == 'httpx':
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            return client.get(url, headers=headers).text
    elif HTTP_CLIENT == 'cloudscraper':
        scraper = cloudscraper.create_scraper()
        return scraper.get(url, headers=headers, timeout=30).text
    else:
        return requests.get(url, headers=headers, timeout=30).text

def get_video_info(video_id: str) -> Dict:
    """Get video title and metadata"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    html = fetch_page(url)
    info = {'video_id': video_id, 'url': url, 'title': '', 'channel': '', 'duration': ''}

    title_match = re.search(r'"title":"([^"]+)"', html)
    if title_match:
        info['title'] = title_match.group(1)
    channel_match = re.search(r'"ownerChannelName":"([^"]+)"', html)
    if channel_match:
        info['channel'] = channel_match.group(1)
    duration_match = re.search(r'"lengthSeconds":"(\d+)"', html)
    if duration_match:
        seconds = int(duration_match.group(1))
        info['duration'] = f"{seconds // 60}:{seconds % 60:02d}"
    return info

def fetch_transcript(video_id: str, lang: str = 'en') -> Optional[List[Dict]]:
    """Fetch transcript using YouTube's internal API"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    html = fetch_page(url)

    match = re.search(r'"captionTracks":\s*\[(.*?)\]', html)
    if not match:
        return None

    caption_data = match.group(1)
    url_match = re.search(rf'"baseUrl":"([^"]+)"[^}}]*"languageCode":"{lang}"', caption_data)
    if not url_match:
        url_match = re.search(r'"baseUrl":"([^"]+)"', caption_data)
    if not url_match:
        return None

    caption_url = url_match.group(1).replace('\\u0026', '&')
    caption_xml = fetch_page(caption_url)

    captions = []
    for match in re.finditer(r'<text start="([^"]+)" dur="([^"]+)"[^>]*>([^<]*)</text>', caption_xml):
        text = match.group(3).replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        captions.append({'start': float(match.group(1)), 'duration': float(match.group(2)), 'text': text.strip()})
    return captions

def format_timestamp(seconds: float) -> str:
    hours, minutes = int(seconds // 3600), int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours > 0 else f"{minutes}:{secs:02d}"

def main():
    args = sys.argv[1:]
    if not args or '-h' in args or '--help' in args:
        print(f"""
{'='*60}
YOUTUBE TRANSCRIPT
{'='*60}

Usage: youtube_transcript.py <video_url> [options]

Options:
  --output FILE     Save to file
  --format FORMAT   txt or json (default: txt)
  --lang LANG       Language code (default: en)
  --no-timestamps   Omit timestamps
  --summary         First 10 sentences only

Examples:
  youtube_transcript.py https://www.youtube.com/watch?v=VIDEO_ID
  youtube_transcript.py VIDEO_ID --format json --output transcript.json
""")
        return

    video_url = output_file = None
    output_format, lang = 'txt', 'en'
    timestamps = '--no-timestamps' not in args
    summary = '--summary' in args

    for i, arg in enumerate(args):
        if arg == '--output' and i + 1 < len(args): output_file = args[i + 1]
        elif arg == '--format' and i + 1 < len(args): output_format = args[i + 1]
        elif arg == '--lang' and i + 1 < len(args): lang = args[i + 1]
        elif not arg.startswith('-') and not video_url: video_url = arg

    video_id = extract_video_id(video_url) if video_url else None
    if not video_id:
        print("Error: Invalid video URL")
        return

    print(f"\n{'='*60}\nYOUTUBE TRANSCRIPT\n{'='*60}\n")
    info = get_video_info(video_id)
    print(f"Title: {info['title'][:50]}...")

    captions = fetch_transcript(video_id, lang)
    if not captions:
        print("Error: No transcript available")
        return

    print(f"Segments: {len(captions)}, Words: {len(' '.join(c['text'] for c in captions).split())}")

    if output_format == 'json':
        output = json.dumps({'video': info, 'transcript': captions, 'full_text': ' '.join(c['text'] for c in captions)}, indent=2)
    else:
        lines = [f"Title: {info['title']}", f"Channel: {info['channel']}", f"URL: {info['url']}", "", "TRANSCRIPT:", ""]
        if summary:
            text = ' '.join(c['text'] for c in captions)
            lines.append(' '.join(re.split(r'(?<=[.!?])\s+', text)[:10]))
        elif timestamps:
            lines.extend(f"[{format_timestamp(c['start'])}] {c['text']}" for c in captions)
        else:
            lines.append(' '.join(c['text'] for c in captions))
        output = '\n'.join(lines)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f: f.write(output)
        print(f"Saved to: {output_file}")
    else:
        print(f"\n{output[:2000]}{'...' if len(output) > 2000 else ''}")
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()

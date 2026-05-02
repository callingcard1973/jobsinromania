#!/usr/bin/env python3
"""
Multi-Language Email Template Generator

Translates email templates into multiple languages using local LLM.
No external API tokens required - uses localhost:1234 (LM Studio).

Usage:
    python3 multilang_template_gen.py --template template.txt --lang pl       # Translate to Polish
    python3 multilang_template_gen.py --template template.txt --lang de,cz,pl # Multiple languages
    python3 multilang_template_gen.py --template template.txt --all           # All supported
    python3 multilang_template_gen.py --campaign HORECA2026 --lang pl         # All templates in campaign
    python3 multilang_template_gen.py --text "Hello, we are..." --lang de     # Translate text
    python3 multilang_template_gen.py --list-languages                        # Show supported
    python3 multilang_template_gen.py --status                                 # Show stats

Supported languages: EN, RO, PL, CZ, DE, HU, BG, ES, FR, IT, NL, SV, NO, DA, FI

Output: Creates {template_name}_{lang}.txt in same directory or --output dir
"""

import os
import sys
import json
import re
import time
import hashlib
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

# Paths
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
TEMPLATES_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS/TEMPLATES")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.multilang_state.json")
CACHE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/.translation_cache")
LLM_URL = "http://localhost:1234/v1/chat/completions"

# Supported languages
LANGUAGES = {
    "en": {"name": "English", "native": "English", "code": "EN"},
    "ro": {"name": "Romanian", "native": "Romana", "code": "RO"},
    "pl": {"name": "Polish", "native": "Polski", "code": "PL"},
    "cz": {"name": "Czech", "native": "Cestina", "code": "CZ"},
    "de": {"name": "German", "native": "Deutsch", "code": "DE"},
    "hu": {"name": "Hungarian", "native": "Magyar", "code": "HU"},
    "bg": {"name": "Bulgarian", "native": "Balgarski", "code": "BG"},
    "es": {"name": "Spanish", "native": "Espanol", "code": "ES"},
    "fr": {"name": "French", "native": "Francais", "code": "FR"},
    "it": {"name": "Italian", "native": "Italiano", "code": "IT"},
    "nl": {"name": "Dutch", "native": "Nederlands", "code": "NL"},
    "sv": {"name": "Swedish", "native": "Svenska", "code": "SV"},
    "no": {"name": "Norwegian", "native": "Norsk", "code": "NO"},
    "da": {"name": "Danish", "native": "Dansk", "code": "DA"},
    "fi": {"name": "Finnish", "native": "Suomi", "code": "FI"},
    "sk": {"name": "Slovak", "native": "Slovencina", "code": "SK"},
    "hr": {"name": "Croatian", "native": "Hrvatski", "code": "HR"},
    "sl": {"name": "Slovenian", "native": "Slovenscina", "code": "SI"},
    "pt": {"name": "Portuguese", "native": "Portugues", "code": "PT"},
}

# Common placeholders to preserve
PLACEHOLDERS = [
    "{company}", "{name}", "{city}", "{email}", "{phone}",
    "{position}", "{salary}", "{date}", "{link}", "{unsubscribe}",
    "{greeting}", "{signature}", "{sender_name}", "{sender_phone}",
    "{job_title}", "{occupation}", "{contact_person}"
]


def log(msg):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    """Load generator state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "translations_count": 0,
        "languages_used": {},
        "last_run": None,
        "cache_hits": 0
    }


def save_state(state):
    """Save generator state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_cache_key(text, target_lang):
    """Generate cache key for translation."""
    content = f"{target_lang}:{text}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def get_cached_translation(text, target_lang):
    """Check if translation is cached."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(text, target_lang)
    cache_file = CACHE_DIR / f"{cache_key}.txt"

    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return f.read()
    return None


def cache_translation(text, target_lang, translation):
    """Cache translation result."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(text, target_lang)
    cache_file = CACHE_DIR / f"{cache_key}.txt"

    with open(cache_file, 'w') as f:
        f.write(translation)


def protect_placeholders(text):
    """Replace placeholders with tokens to protect during translation."""
    protected = text
    mapping = {}

    for i, ph in enumerate(PLACEHOLDERS):
        if ph in protected:
            token = f"__PH{i}__"
            mapping[token] = ph
            protected = protected.replace(ph, token)

    # Also protect URLs and emails
    url_pattern = r'(https?://[^\s]+)'
    urls = re.findall(url_pattern, protected)
    for j, url in enumerate(urls):
        token = f"__URL{j}__"
        mapping[token] = url
        protected = protected.replace(url, token, 1)

    return protected, mapping


def restore_placeholders(text, mapping):
    """Restore protected placeholders after translation."""
    restored = text
    for token, original in mapping.items():
        restored = restored.replace(token, original)
    return restored


def detect_language(text):
    """Detect source language using LLM."""
    prompt = f"""What language is this text written in? Reply with just the ISO 639-1 code (2 letters lowercase).

Text: {text[:500]}

Language code:"""

    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "llama-3.2-3b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            lang = result['choices'][0]['message']['content'].strip().lower()[:2]
            if lang in LANGUAGES:
                return lang
    except Exception:
        pass

    return "en"  # Default to English


def translate_text(text, target_lang, source_lang=None):
    """Translate text using local LLM."""
    if not text.strip():
        return text

    # Check cache first
    cached = get_cached_translation(text, target_lang)
    if cached:
        return cached

    # Detect source language if not provided
    if not source_lang:
        source_lang = detect_language(text)

    if source_lang == target_lang:
        return text

    # Protect placeholders
    protected_text, placeholder_mapping = protect_placeholders(text)

    target_name = LANGUAGES.get(target_lang, {}).get('name', target_lang)
    source_name = LANGUAGES.get(source_lang, {}).get('name', source_lang)

    prompt = f"""Translate this email template from {source_name} to {target_name}.

IMPORTANT RULES:
1. Keep the exact same formatting (line breaks, spacing)
2. Keep tokens like __PH0__, __URL0__ exactly as they are (do not translate them)
3. Keep the "Subject:" line format
4. Make the translation sound natural and professional
5. Use formal business language appropriate for B2B email

Original ({source_name}):
{protected_text}

Translation ({target_name}):"""

    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "llama-3.2-3b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.3
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            translation = result['choices'][0]['message']['content'].strip()

            # Restore placeholders
            translation = restore_placeholders(translation, placeholder_mapping)

            # Convert to ASCII
            translation = to_ascii(translation)

            # Cache result
            cache_translation(text, target_lang, translation)

            return translation

    except Exception as e:
        log(f"Translation error: {e}")

    return text  # Return original if translation fails


def translate_template_file(template_path, target_lang, output_dir=None):
    """Translate a template file."""
    template_path = Path(template_path)

    if not template_path.exists():
        log(f"Template not found: {template_path}")
        return None

    # Read template
    with open(template_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    log(f"Translating {template_path.name} to {target_lang}...")

    # Translate
    translated = translate_text(content, target_lang)

    # Determine output path
    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = template_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    stem = template_path.stem
    # Remove existing language suffix if present
    for lang in LANGUAGES:
        if stem.endswith(f"_{lang}"):
            stem = stem[:-3]
            break

    output_file = output_dir / f"{stem}_{target_lang}.txt"

    # Write translated template
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translated)

    log(f"  Created: {output_file}")
    return output_file


def translate_campaign_templates(campaign_name, target_langs, output_dir=None):
    """Translate all templates in a campaign."""
    campaign_dir = CAMPAIGNS_DIR / campaign_name / "templates"

    if not campaign_dir.exists():
        log(f"Campaign templates not found: {campaign_dir}")
        return []

    templates = list(campaign_dir.glob("*.txt"))
    if not templates:
        log(f"No templates found in {campaign_dir}")
        return []

    log(f"Found {len(templates)} templates in {campaign_name}")

    results = []
    for template in templates:
        # Skip already translated templates
        stem = template.stem
        if any(stem.endswith(f"_{lang}") for lang in LANGUAGES):
            continue

        for lang in target_langs:
            output = translate_template_file(template, lang, output_dir)
            if output:
                results.append(output)
            time.sleep(1)  # Rate limit

    return results


def generate_all_languages(template_path, output_dir=None):
    """Generate template in all supported languages."""
    results = []
    for lang in LANGUAGES:
        if lang == "en":  # Skip if source is likely English
            continue
        output = translate_template_file(template_path, lang, output_dir)
        if output:
            results.append(output)
        time.sleep(1)

    return results


def show_status():
    """Show generator status."""
    state = load_state()

    print("\n=== Multi-Language Template Generator ===\n")
    print(f"Translations made: {state.get('translations_count', 0)}")
    print(f"Cache hits: {state.get('cache_hits', 0)}")
    print(f"Last run: {state.get('last_run', 'Never')}")

    print("\nLanguages used:")
    for lang, count in sorted(state.get('languages_used', {}).items(), key=lambda x: -x[1]):
        lang_name = LANGUAGES.get(lang, {}).get('name', lang)
        print(f"  {lang} ({lang_name}): {count} translations")

    print("\nCache status:")
    if CACHE_DIR.exists():
        cache_count = len(list(CACHE_DIR.glob("*.txt")))
        print(f"  Cached translations: {cache_count}")
    else:
        print("  No cache")

    print("\nCampaign templates:")
    for campaign in CAMPAIGNS_DIR.iterdir():
        if campaign.is_dir():
            templates_dir = campaign / "templates"
            if templates_dir.exists():
                templates = list(templates_dir.glob("*.txt"))
                if templates:
                    print(f"  {campaign.name}: {len(templates)} templates")


def list_languages():
    """List supported languages."""
    print("\n=== Supported Languages ===\n")
    for code, info in sorted(LANGUAGES.items()):
        print(f"  {code}: {info['name']} ({info['native']})")
    print(f"\nTotal: {len(LANGUAGES)} languages")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Language Template Generator")
    parser.add_argument("--template", help="Path to template file to translate")
    parser.add_argument("--campaign", help="Campaign name to translate all templates")
    parser.add_argument("--text", help="Translate text directly")
    parser.add_argument("--lang", help="Target language(s), comma-separated (e.g., pl,de,cz)")
    parser.add_argument("--all", action="store_true", help="Translate to all languages")
    parser.add_argument("--output", help="Output directory for translated templates")
    parser.add_argument("--list-languages", action="store_true", help="List supported languages")
    parser.add_argument("--status", action="store_true", help="Show generator status")
    parser.add_argument("--detect", help="Detect language of text")
    parser.add_argument("--clear-cache", action="store_true", help="Clear translation cache")

    args = parser.parse_args()

    if args.list_languages:
        list_languages()
        return

    if args.status:
        show_status()
        return

    if args.clear_cache:
        if CACHE_DIR.exists():
            import shutil
            shutil.rmtree(CACHE_DIR)
            print("Cache cleared.")
        return

    if args.detect:
        lang = detect_language(args.detect)
        lang_name = LANGUAGES.get(lang, {}).get('name', 'Unknown')
        print(f"Detected language: {lang} ({lang_name})")
        return

    # Parse target languages
    if args.all:
        target_langs = [l for l in LANGUAGES if l != 'en']
    elif args.lang:
        target_langs = [l.strip().lower() for l in args.lang.split(',')]
        # Validate
        for lang in target_langs:
            if lang not in LANGUAGES:
                print(f"Unknown language: {lang}")
                print(f"Use --list-languages to see supported languages")
                return
    else:
        target_langs = []

    if not target_langs and not args.text:
        parser.print_help()
        return

    state = load_state()

    # Translate text directly
    if args.text:
        if not target_langs:
            target_langs = ['pl']  # Default

        for lang in target_langs:
            translated = translate_text(args.text, lang)
            print(f"\n=== {LANGUAGES[lang]['name']} ===")
            print(translated)

        state['translations_count'] = state.get('translations_count', 0) + len(target_langs)
        for lang in target_langs:
            state['languages_used'][lang] = state.get('languages_used', {}).get(lang, 0) + 1

    # Translate template file
    elif args.template:
        for lang in target_langs:
            translate_template_file(args.template, lang, args.output)

        state['translations_count'] = state.get('translations_count', 0) + len(target_langs)
        for lang in target_langs:
            state['languages_used'][lang] = state.get('languages_used', {}).get(lang, 0) + 1

    # Translate campaign templates
    elif args.campaign:
        results = translate_campaign_templates(args.campaign, target_langs, args.output)
        log(f"Created {len(results)} translated templates")

        state['translations_count'] = state.get('translations_count', 0) + len(results)
        for lang in target_langs:
            state['languages_used'][lang] = state.get('languages_used', {}).get(lang, 0) + len(results) // len(target_langs)

    state['last_run'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()

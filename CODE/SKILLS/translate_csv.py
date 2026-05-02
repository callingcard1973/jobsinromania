#!/usr/bin/env python3
"""
Translate CSV columns using Google Translate API via deep-translator.

Usage:
    python translate_csv.py --input data.csv --output data_translated.csv \
        --column "description" --source ro --target en --new-column "description_en"
"""

import argparse
import csv
import unicodedata
import time
import sys

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Error: deep-translator not installed. Run:")
    print("  /opt/ACTIVE/INFRA/venv/bin/pip install deep-translator")
    sys.exit(1)


def to_ascii(text):
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return ''
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


def translate_batch_safe(translator, texts, batch_size=50):
    """Translate texts in batches with error handling."""
    results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            trans = translator.translate_batch(batch)
            results.extend(trans)
        except Exception as e:
            print(f"Batch error at {i}, falling back to individual: {e}")
            for text in batch:
                try:
                    results.append(translator.translate(text))
                except:
                    results.append(text)  # Use original on failure

        print(f"Translated {len(results)}/{len(texts)}", end='\r')
        time.sleep(0.1)

    print()
    return results


def main():
    parser = argparse.ArgumentParser(description='Translate CSV column')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    parser.add_argument('--output', '-o', required=True, help='Output CSV file')
    parser.add_argument('--column', '-c', required=True, help='Column to translate')
    parser.add_argument('--source', '-s', default='auto', help='Source language (default: auto)')
    parser.add_argument('--target', '-t', default='en', help='Target language (default: en)')
    parser.add_argument('--new-column', '-n', help='New column name for translation (default: {column}_translated)')
    parser.add_argument('--ascii', '-a', action='store_true', help='Convert output to ASCII')
    parser.add_argument('--batch-size', '-b', type=int, default=50, help='Batch size (default: 50)')

    args = parser.parse_args()

    new_col = args.new_column or f"{args.column}_translated"

    # Read input
    with open(args.input, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if args.column not in fieldnames:
        print(f"Error: Column '{args.column}' not found in CSV")
        print(f"Available columns: {', '.join(fieldnames)}")
        sys.exit(1)

    print(f"Translating {len(rows)} rows from {args.source} to {args.target}...")

    # Get texts to translate
    texts = [row[args.column] for row in rows]

    # Translate
    translator = GoogleTranslator(source=args.source, target=args.target)
    translations = translate_batch_safe(translator, texts, args.batch_size)

    # Add translations to rows
    for i, row in enumerate(rows):
        trans = translations[i] if i < len(translations) else row[args.column]
        row[new_col] = to_ascii(trans) if args.ascii else trans

    # Write output
    output_fieldnames = list(fieldnames)
    if new_col not in output_fieldnames:
        # Insert new column after source column
        idx = output_fieldnames.index(args.column) + 1
        output_fieldnames.insert(idx, new_col)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done! Output: {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convert all text files in CODE and DATA to ASCII-only by removing diacritics."""
import os
import unicodedata

def to_ascii(s):
    if not isinstance(s, str):
        return s
    normalized = unicodedata.normalize('NFKD', s)
    return normalized.encode('ascii', 'ignore').decode('ascii')

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
dirs = ['CODE', 'DATA']

for d in dirs:
    dirpath = os.path.join(root, d)
    for dirpath, _, filenames in os.walk(dirpath):
        for fn in filenames:
            if fn.lower().endswith(('.md', '.py', '.txt', '.csv', '.json', '.log')):
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    newtext = to_ascii(text)
                    if newtext != text:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(newtext)
                        print(f"Converted {path}")
                except Exception as e:
                    print(f"Failed {path}: {e}")

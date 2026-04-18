import os

results = []

for root, dirs, files in os.walk(r'D:\MEMORY'):
    dirs[:] = [d for d in dirs if d not in ['.venv', 'node_modules', '__pycache__', '.git', 'venv', 'lib', 'Scripts', 'Include']]
    for fname in files:
        if fname.endswith('.csv'):
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    header = f.readline()
                    if any(kw in header.lower() for kw in ['caen', 'utilaj', 'machinery', 'firma', 'cui', 'onrc']):
                        rel = os.path.relpath(fpath, r'D:\MEMORY')
                        size = os.path.getsize(fpath)
                        results.append((rel, size, header.strip()[:200]))
            except:
                pass

with open(r'D:\MEMORY\DELECROIX\db_files.txt', 'w', encoding='utf-8') as out:
    out.write(f'Found {len(results)} CSV files with company/business data:\n\n')
    for rel, size, header in sorted(results, key=lambda x: -x[1]):
        out.write(f'{rel} ({size:,} bytes)\n  Header: {header}\n\n')

print(f'Found {len(results)} files, wrote to db_files.txt')

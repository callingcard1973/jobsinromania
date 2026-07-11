"""Shared helpers pentru GRAIN desk: path, CSV/JSONL/SQLite, norm_name."""
import csv, json, os, re, sqlite3, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)

def setup():
    if PARENT not in sys.path:
        sys.path.insert(0, PARENT)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import config as C
    return C

def data_path(*parts):
    C = setup()
    return os.path.join(C.DATA, *parts)

def open_db(name="grain.db"):
    path = data_path(name)
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path)

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out

def log(msg):
    print("  %s" % msg)

def norm_name(n):
    n = (n or "").upper().strip()
    n = re.sub(r"\b(S\.?R\.?L\.?|S\.?A\.?|SRL|SA|S\.C\.|SC)\b\.?", "", n)
    return re.sub(r"[^A-Z0-9 ]", "", n).strip()

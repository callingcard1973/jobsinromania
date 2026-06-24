---
name: render-check
description: Use when validating or before deploying the InterJob TEMPLATE files — checks that base.html / listing.html / job_detail.html / candidates.html parse as Jinja2 and render against every domain in domains.py with no missing variables, and that domains.py is structurally consistent (13 domains, full key set). Trigger on "lint templates", "check the templates render", "validate domains.py", or after editing any TEMPLATE file.
---

# render-check

Fast offline validation that the Jinja2 templates render for all 13 domains and that `domains.py` is consistent. No DB, no network, no deploy.

Folder (quote — spaces): `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\TEMPLATE`

## Steps

1. Confirm files exist: `domains.py`, `base.html`, `listing.html`, `job_detail.html`, `candidates.html`.
2. Run the check script below from the TEMPLATE folder. It:
   - imports `DOMAINS`, asserts 13 entries each with the required keys + correct types;
   - loads each `.html` with Jinja2 `StrictUndefined`;
   - renders each per domain using domain config + a stub render context (`domain`, `posthog_key`, sample `jobs`/`candidates` lists);
   - reports any `TemplateSyntaxError` or `UndefinedError` (= missing variable).
3. Report a numbered pass/fail summary. Stop — do not deploy.

## Check script (run with the laptop Python that has jinja2)

```bash
cd "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\TEMPLATE"
python - <<'PY'
import importlib.util, sys
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.exceptions import TemplateSyntaxError, UndefinedError

REQ = {"emoji","brand","primary","accent","category_label","category_description",
       "lang","lang_codes","topics","tone","cpanel_path","site_type"}

spec = importlib.util.spec_from_file_location("d","domains.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
D = m.DOMAINS
errs = []
assert len(D) == 13, f"expected 13 domains, got {len(D)}"
for name,cfg in D.items():
    miss = REQ - set(cfg)
    if miss: errs.append(f"{name}: missing keys {miss}")
    if not isinstance(cfg.get("lang_codes"),list): errs.append(f"{name}: lang_codes not list")
    if not isinstance(cfg.get("topics"),list): errs.append(f"{name}: topics not list")
    for c in ("primary","accent"):
        if not str(cfg.get(c,"")).startswith("#"): errs.append(f"{name}: {c} not #hex")

env = Environment(loader=FileSystemLoader("."), undefined=StrictUndefined)
tmpls = ["base.html","listing.html","job_detail.html","candidates.html"]
stub = {"posthog_key":"phc_stub","jobs":[],"candidates":[],"job":{},"count":0}
for t in tmpls:
    try: tpl = env.get_template(t)
    except TemplateSyntaxError as e: errs.append(f"{t}: syntax {e}"); continue
    for name,cfg in D.items():
        ctx = {**cfg,"domain":name,**stub}
        try: tpl.render(**ctx)
        except UndefinedError as e: errs.append(f"{t} @ {name}: undefined {e}")
        except TemplateSyntaxError as e: errs.append(f"{t} @ {name}: syntax {e}")

if errs:
    print("FAIL"); [print(" -",e) for e in errs]; sys.exit(1)
print(f"PASS: {len(D)} domains x {len(tmpls)} templates rendered clean")
PY
```

## Notes

- Undeclared-variable failures are expected if a generator passes extra context; add the variable to `stub` only if the generator truly supplies it, otherwise it is a real template bug.
- For raspibig drift, diff against `/opt/ACTIVE/INTERJOB/` via `ssh tudor@192.168.100.21` (key) or `plink -pw 'bucare'`.
